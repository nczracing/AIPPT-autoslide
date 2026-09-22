# -*- coding: utf-8 -*-
"""
AutoSlide 反馈邮件监听守护脚本
- 持续调用 `agently-cli message +watch`
- 每封新邮件追加到 all_mail.log（带时间戳）
- 命中 AutoSlide 反馈特征的邮件，额外写出 feedback_NNN.json 结构化报告
- 控制台打印 [FEEDBACK DETECTED] 标记行，便于快速发现

过滤特征（任一满足即视为反馈邮件）:
  - 主题/正文包含关键词: autoslide, AutoSlide, PPT, 幻灯片, 反馈, 改进, 优化, bug, 缺陷, 报错, 崩溃, 闪退
  - 发件人是本人账号 nczracing@agent.qq.com （自我反馈流）
"""
import subprocess
import json
import os
import sys
import time
import re

CLI = r'C:\Users\NCZ Racing\.workbuddy\binaries\node\versions\22.22.2-3\agently-cli.cmd'
WATCH_DIR = os.path.dirname(os.path.abspath(__file__))
ALL_LOG = os.path.join(WATCH_DIR, 'all_mail.log')
FEEDBACK_DIR = os.path.join(WATCH_DIR, 'feedback')
STATE_FILE = os.path.join(WATCH_DIR, 'last_seq.txt')

KEYWORDS = ['autoslide', '幻灯片', '反馈', '改进', '优化', 'bug', '缺陷',
            '报错', '崩溃', '闪退', 'ppt', 'pptx']
SELF_ADDR = 'nczracing@agent.qq.com'

os.makedirs(FEEDBACK_DIR, exist_ok=True)


def load_last_seq():
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return int(f.read().strip())
    except Exception:
        return 0


def save_last_seq(n):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            f.write(str(n))
    except Exception:
        pass


def extract_text(msg):
    """尽力提取邮件纯文本正文。"""
    body = msg.get('body') or msg.get('text') or ''
    if not body and msg.get('parts'):
        for p in msg['parts']:
            if p.get('mime_type', '').startswith('text/plain'):
                body = p.get('content', '')
                break
        if not body and msg['parts']:
            body = msg['parts'][0].get('content', '')
    # 去除 HTML 标签
    body = re.sub(r'<[^>]+>', ' ', str(body))
    body = re.sub(r'\s+', ' ', body).strip()
    return body


def is_feedback(msg):
    subject = (msg.get('subject') or '').lower()
    sender = ''
    frm = msg.get('from') or {}
    if isinstance(frm, dict):
        sender = (frm.get('email') or '').lower()
    elif isinstance(frm, str):
        sender = frm.lower()
    text = extract_text(msg).lower()
    hay = subject + ' ' + text
    if any(k in hay for k in KEYWORDS):
        return True
    if SELF_ADDR in sender:
        return True
    return False


def log_all(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    subject = msg.get('subject', '')
    frm = msg.get('from', {})
    frm_email = frm.get('email', '') if isinstance(frm, dict) else str(frm)
    line = f'[{ts}] FROM={frm_email} SUBJECT={subject} ID={msg.get("message_id")}\n'
    with open(ALL_LOG, 'a', encoding='utf-8') as f:
        f.write(line)
        # 保存完整 JSON 便于回溯
        f.write('  RAW=' + json.dumps(msg, ensure_ascii=False)[:4000] + '\n')


def save_feedback(msg, idx):
    path = os.path.join(FEEDBACK_DIR, f'feedback_{idx:03d}.json')
    frm = msg.get('from', {})
    frm_email = frm.get('email', '') if isinstance(frm, dict) else str(frm)
    out = {
        'seq': idx,
        'received_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'message_id': msg.get('message_id'),
        'from': frm_email,
        'from_name': frm.get('name', '') if isinstance(frm, dict) else '',
        'subject': msg.get('subject'),
        'body_text': extract_text(msg),
        'raw_keys': list(msg.keys()),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return path


def main():
    print(f'[watch] started pid={os.getpid()} dir={WATCH_DIR}', flush=True)
    seq = load_last_seq()
    # 启动子进程
    proc = subprocess.Popen(
        [CLI, 'message', '+watch'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
    )
    print('[watch] subprocess launched, waiting for new mail...', flush=True)
    fb_idx = seq
    for line in iter(proc.stdout.readline, ''):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except Exception:
            # 非 JSON（可能是状态行/错误），原样记录
            with open(ALL_LOG, 'a', encoding='utf-8') as f:
                f.write(f'[non-json] {line}\n')
            continue
        # +watch 全量模式输出信封: {"message": {...}}
        # 事件模式输出原始 watch event。统一解包为消息对象。
        if isinstance(data, dict) and 'message' in data:
            msg = data['message']
        else:
            msg = data
        seq += 1
        log_all(msg)
        if is_feedback(msg):
            fb_idx += 1
            path = save_feedback(msg, fb_idx)
            save_last_seq(seq)
            print(f'[FEEDBACK DETECTED] seq={seq} idx={fb_idx} -> {path}', flush=True)
            print(f'  FROM={msg.get("from",{}).get("email","") if isinstance(msg.get("from"),dict) else msg.get("from")} '
                  f'SUBJECT={msg.get("subject","")}', flush=True)
        else:
            save_last_seq(seq)
            print(f'[mail] seq={seq} (non-feedback) FROM={(msg.get("from",{}).get("email","") if isinstance(msg.get("from"),dict) else msg.get("from"))}', flush=True)
    # 子进程结束（正常不应发生，除非被 kill 或出错）
    rc = proc.wait()
    print(f'[watch] subprocess exited rc={rc}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('[watch] interrupted', flush=True)
        sys.exit(0)
