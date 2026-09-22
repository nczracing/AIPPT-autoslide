# -*- coding: utf-8 -*-
"""一次性 probe：验证 R29 修复（issue #3/#4/#5/#6 + emoji 清理）"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

# --- Issue #6: fence 行被跳过 ---
from core.doc_parser import _clean_markdown
md = """# 标题
正文段落
```python
def hello():
    print("hi")
```
- 列表项
"""
cleaned = _clean_markdown(md)
assert "```" not in cleaned, "fence 行未被跳过: " + cleaned
assert "def hello():" in cleaned, "代码内容丢失"
assert "标题" in cleaned
print("ISSUE #6 OK: fence 行被跳过，代码内容保留")

# --- Issue #5: 扫描件 PDF 提示 ---
import inspect
src = inspect.getsource(__import__("core.doc_parser", fromlist=["_parse_pdf"])._parse_pdf)
assert "OCR" in src, "PDF 扫描件提示未包含 OCR 引导"
print("ISSUE #5 OK: 扫描件 PDF 提示已加 OCR 引导文案")

# --- Issue #4: 截断保留来源标注 ---
from core.prompt_builder import PromptBuilder
ctx = "=== 来源: a.pdf ===\n" + ("甲" * 5000) + "\n=== 来源: b.md ===\n" + ("乙" * 5000)
block = PromptBuilder._build_context_block(ctx)
# 两个来源标注都应出现在 block 中（截断后第一个标注被保留）
assert "=== 来源: a.pdf ===" in block, "第一个来源标注被切没"
print("ISSUE #4 OK: 截断保留了来源标注")

# 无来源标注的 context：直接截断
ctx2 = "x" * 10000
block2 = PromptBuilder._build_context_block(ctx2)
assert "已省略后 6000 字符" in block2, "无来源标注时截断未正确计算省略字符数"
print("ISSUE #4b OK: 无来源标注 context 截断正常")

# --- Issue #3: 双栏垂直居中逻辑 ---
# 通过静态检查确认 _adjust_textbox_for_image 多栏分支有居中逻辑
from core.pptx_builder import PPTXBuilder
src3 = inspect.getsource(PPTXBuilder._adjust_textbox_for_image)
assert "est_h" in src3 and "est_h > 0.5" in src3, "多栏垂直居中逻辑缺失"
print("ISSUE #3 OK: 多栏（双栏）分支已加垂直居中逻辑")

# --- Emoji 清理：确认 UI 源码无 emoji ---
import re
emoji_pat = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # 各种 emoji
    "\u2600-\u27BF"          # 杂项符号
    "\u2B00-\u2BFF"          # 星形符号
    "\u2190-\u21FF"          # 箭头
    "\u2049\u203C\u203D"     # 特殊标点
    "\uFE0F"
    "]"
)
ui_files = [
    "ui/generator_widget.py",
    "ui/preview_widget.py",
    "ui/main_window.py",
    "ui/settings_dialog.py",
]
base = os.path.dirname(__file__)
found = []
for rel in ui_files:
    p = os.path.join(base, rel)
    with open(p, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            m = emoji_pat.search(line)
            if m:
                found.append(f"{rel}:{i}: {line.rstrip()}")
if found:
    print("EMOJI 残留（" + str(len(found)) + " 处）：")
    for f_ in found:
        print("  " + f_)
    sys.exit(1)
print("EMOJI OK: UI 4 个文件无 emoji 残留")

print("\n所有 R29 probe 通过")
