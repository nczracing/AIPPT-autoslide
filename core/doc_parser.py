# -*- coding: utf-8 -*-
"""
参考文档解析器
将用户上传的 PDF / Markdown 文件解析为纯文本，供 Prompt 上下文注入。

设计要点：
- PDF 用 PyPDF2 逐页提取，保留页边界与总页数，便于 AI 理解结构
- Markdown 清理标记语法（标题#/链接/图片/代码块），保留可读层级
- 统一入口 parse_reference_file 返回 (纯文本, 文件名)，失败抛 ValueError
- 输出截断保护：单文件超过 MAX_FILE_CHARS 时截断并标注
"""
import logging
import re
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("autoslide")

# 单文件最大注入字符数（与 prompt_builder.MAX_CONTEXT_CHARS 配合，
# 这里取更宽松的上限，最终由 prompt_builder 二次截断）
MAX_FILE_CHARS = 12000


def parse_reference_file(file_path: str) -> str:
    """解析参考文件为纯文本。

    根据扩展名路由到 PDF / Markdown 解析器。
    返回清洗后的文本；文件不存在或解析失败时抛出 ValueError。
    """
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"文件不存在: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _parse_pdf(path)
    elif suffix in (".md", ".markdown"):
        text = _parse_markdown(path)
    else:
        raise ValueError(f"不支持的文件类型: {suffix}（仅支持 .pdf / .md）")

    text = text.strip()
    if not text:
        raise ValueError(f"文件无有效文本内容: {path.name}")

    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + f"\n...(内容过长，已截取前 {MAX_FILE_CHARS} 字符)..."

    return text


def _parse_pdf(path: Path) -> str:
    """用 PyPDF2 逐页提取 PDF 文本，带页边界标注。"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ValueError("PDF 解析需要 PyPDF2，请确认依赖已安装")

    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise ValueError(f"PDF 打开失败（可能已损坏）: {e}")

    # 加密文件检查
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ValueError("PDF 已加密，无法读取")

    pages = []
    for i, page in enumerate(reader.pages, 1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        page_text = page_text.strip()
        if page_text:
            # 页数标注帮助 AI 理解原文结构
            pages.append(f"[第{i}页]\n{page_text}")

    if not pages:
        raise ValueError(
            "PDF 无可提取文本（可能是扫描件）。"
            "建议先用 OCR 工具预处理（如 OCRmyPDF、Adobe Acrobat 的 OCR 功能）"
            "再上传，或直接提供 .md / 可复制文本的 PDF。"
        )

    return "\n\n".join(pages)


def _parse_markdown(path: Path) -> str:
    """读取 Markdown 并清理标记语法，保留可读结构与层级。"""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    text = _clean_markdown(raw)
    if not text.strip():
        raise ValueError("Markdown 无有效内容")
    return text


def _clean_markdown(text: str) -> str:
    """清理 Markdown 标记语法，转为可读纯文本。

    处理：
    - 标题 # → 保留文字（去 #）
    - 加粗/斜体 **__* → 去标记留文字
    - 链接 [text](url) → 保留 text
    - 图片 ![alt](url) → 删除
    - 代码块 ``` → 保留内容（去围栏）
    - 无序/有序列表标记 → 保留为 • / 数字
    - HTML 标签 → 删除
    """
    lines = text.splitlines()
    cleaned = []
    in_code_block = False
    for line in lines:
        # 代码块围栏：跳过 fence 行（```lang / ```），保留代码内容（F-06）
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            cleaned.append(line)
            continue

        out = line
        # 图片行（先清除行内图片语法，避免后续链接规则把 ![alt](url) 误匹配成 "!alt"）
        out = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", out)
        # 标题：# / ## / ### → 去 # 留文字
        out = re.sub(r"^#{1,6}\s*", "", out)
        # 加粗/斜体标记去除
        out = re.sub(r"(\*\*|__)(.*?)\1", r"\2", out)
        out = re.sub(r"(\*|_)(.*?)\1", r"\2", out)
        # 链接 [text](url) → text
        out = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", out)
        # 行内代码 `code` → code
        out = re.sub(r"`([^`]+)`", r"\1", out)
        # 块引用 > → 去标记留文字
        out = re.sub(r"^\s*>\s?", "", out)
        # 无序列表 - / * / + → •
        out = re.sub(r"^\s*[-*+]\s+", "• ", out)
        # 水平线 --- / *** → 删除
        if re.match(r"^\s*([-*_]){3,}\s*$", out):
            continue
        # HTML 标签删除
        out = re.sub(r"<[^>]+>", "", out)
        # 图片清除后若整行只剩空白则跳过
        if not out.strip():
            continue
        cleaned.append(out)

    # 合并多余空行
    result_lines = []
    prev_blank = False
    for ln in cleaned:
        if ln.strip() == "":
            if not prev_blank:
                result_lines.append("")
            prev_blank = True
        else:
            result_lines.append(ln)
            prev_blank = False

    return "\n".join(result_lines).strip()
