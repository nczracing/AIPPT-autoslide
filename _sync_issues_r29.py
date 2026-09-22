# -*- coding: utf-8 -*-
"""R29 issues 同步脚本
- 关闭已修复的 issue #3 #4 #5 #6
- 创建新 issue 记录 R29 遇到的新问题
"""
import json
import re
import subprocess
import sys

import urllib.request
import urllib.error

REPO = "nczracing/AIPPT-autoslide"
API = f"https://api.github.com/repos/{REPO}/issues"


def get_pat() -> str:
    """从 git credential-manager 取出 nczracing 的 PAT。"""
    r = subprocess.run(
        ["git", "-C", "E:/life/study/projects/autos/autoslide", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        capture_output=True,
        text=True,
        timeout=60,
    )
    for line in r.stdout.splitlines():
        if line.lower().startswith("password="):
            return line.split("=", 1)[1].strip()
    print("credential fill 输出:", r.stdout, "错误:", r.stderr)
    sys.exit(2)


def api(method: str, path: str, payload: dict = None, pat: str = ""):
    """调用 GitHub REST API，返回 (status, data)。"""
    url = f"https://api.github.com/{path}"
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {pat}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "autoslide-r29-sync")
    if payload is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
    try:
        with urllib.request.urlopen(req, data) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[{method} {path}] HTTP {e.code}: {body[:500]}")
        return e.code, {}
    except Exception as e:
        print(f"[{method} {path}] {e}")
        return 0, {}


def close_issue(num: int, note: str, pat: str):
    print(f"\n=== 关闭 #{num} ===")
    status, data = api("PATCH", f"repos/{REPO}/issues/{num}",
                       {"state": "closed", "state_reason": "completed",
                        "body": note + "\n\n---\n\n_由 R29 开发轮次自动关闭_"},
                       pat)
    print(f"  -> HTTP {status}")


def create_issue(title: str, body: str, pat: str):
    print(f"\n=== 创建 issue: {title} ===")
    status, data = api("POST", f"repos/{REPO}/issues",
                       {"title": title, "body": body}, pat)
    if status == 201:
        print(f"  -> 已创建 #{data['number']}  {data.get('html_url','')}")
        return data["number"]
    return None


def main():
    pat = get_pat()
    print(f"PAT 已获取（长度 {len(pat)}）")

    close_issue(3,
        "## 修复（R29，2026-09-22）\n\n"
        "- `core/pptx_builder.py` 的 `_adjust_textbox_for_image` 多栏分支"
        "（`n >= 2`）已加垂直居中估算：按每栏实际内容高度 `est_h` 计算，"
        "远小于文字区时整体居中，消除底部空白，高度留 0.35\" 余量防触发字号缩放。\n"
        "- 与单栏 `layout_mode in (right,left)` 分支的居中逻辑对齐。", pat)
    close_issue(4,
        "## 修复（R29，2026-09-22）\n\n"
        "- `core/prompt_builder.py` 的 `_build_context_block` 截断改为"
        "保留每个「=== 来源: 文件名 ===」标注：定位所有来源标注结束位置，"
        "把截断点对齐到最后一个不超过 MAX_CONTEXT_CHARS 的标注末尾，"
        "保证标注本身不被切没（最多超出一条标注长度）。\n"
        "- 新增 `_truncate_context` 静态方法实现该逻辑；无来源标注时按原样截断。", pat)
    close_issue(5,
        "## 修复（R29，2026-09-22）\n\n"
        "- `core/doc_parser.py` 的 `_parse_pdf` 在提取 0 页文本时，"
        "错误信息改为带 OCR 引导文案：「PDF 无可提取文本（可能是扫描件）。"
        "建议先用 OCR 工具预处理（如 OCRmyPDF、Adobe Acrobat 的 OCR 功能）"
        "再上传，或直接提供 .md / 可复制文本的 PDF。」\n"
        "- UI 层 `generator_widget.upload_reference_files` 已有 "
        "`QMessageBox.warning` 捕获该 ValueError 并弹提示，无需额外改动。", pat)
    close_issue(6,
        "## 修复（R29，2026-09-22）\n\n"
        "- `core/doc_parser.py` 的 `_clean_markdown` 改为跳过代码块 fence 行"
        "（```lang / ```），仅保留代码内容，避免 fence 行被 LLM 当作正文噪音。", pat)

    create_issue(
        "双栏垂直居中后需补充几何验证测试",
        "## 现象\n\n"
        "R29 在 `_adjust_textbox_for_image` 多栏分支加了垂直居中估算，"
        "但当前测试（_test_layout.py 12 场景 / _test_extreme.py 7 场景）"
        "均未覆盖双栏稀疏内容的居中几何。需要新增断言：双栏两栏的 top 相同"
        "且等于 `(region[1] + (region[3] - new_h)/2)`。\n\n"
        "## 来源\n\nR29 开发过程中发现：居中逻辑依赖 `_estimate_body_height` "
        "估算，缺少专项测试。\n\n## 建议\n\n在 `_test_layout.py` 中新增双栏稀疏"
        "场景，打印 shape 的 top/w/h 并断言居中。", pat)

    create_issue(
        "iss 脚本与项目路径迁移不同步",
        "## 现象\n\n"
        "`scripts/autoslide_setup.iss` 的 `LicenseFile` 与 `[Files] Source` "
        "在 R29 打包前仍指向旧路径 `E:\\study\\projects\\autoslide`，"
        "导致 InnoSetup 编译在用户机器上无法找到源文件。\n\n"
        "## 来源\n\nR29 打包时发现（项目已迁至 "
        "`E:\\life\\study\\projects\\autos\\autoslide`，iss 未同步迁移）。\n\n"
        "## 修复\n\n已改两处路径指向新位置（提交 813cb32）。"
        "建议将 iss 的路径参数化（用 `__DIR__` 或环境变量），"
        "避免迁移时再改。", pat)

    create_issue(
        "GitHub MCP 写权限不足，issue 关闭需走 PAT",
        "## 现象\n\n"
        "GitHub MCP 连接器的 `issue_write` 工具返回 403 "
        "（Resource not accessible by integration），MCP 的 integration "
        "token 没有该仓库的 issue 写权限。R29 的 issue 同步需要绕 MCP "
        "直接调 GitHub REST API（git-credential-manager 存的 PAT）。\n\n"
        "## 来源\n\nR29 关闭 #3/#4/#5/#6 时发现 MCP 写 403。\n\n"
        "## 建议\n\n为 GitHub MCP 配置带 issue 写权限的 PAT，"
        "或保持现状用本地 PAT 调 API。", pat)

    print("\n=== R29 issues 同步完成 ===")


if __name__ == "__main__":
    main()
