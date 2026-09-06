# CODE REVIEW REQUEST — Round 12

You are an independent code reviewer. You must NOT modify any code. Output a CODE REVIEW REPORT in the fixed format below.

## Project Background
AutoSlide is a PyQt6 desktop app that generates PowerPoint presentations via an LLM. The module under review is the PPTX builder.

## What Changed (this round)
File: `core/pptx_builder.py`

Two bugs were found by reading back the generated .pptx and discovering that slide bullet points were silently missing for the default `title_content` layout.

Fix 1 — layout index mapping was wrong:
```python
# BEFORE
LAYOUTS = {
    "title_slide": 0,
    "title_content": 1,
    "two_content": 2,   # WRONG: index 2 is "Section Header" in the python-pptx default template
}
# AFTER
LAYOUTS = {
    "title_slide": 0,
    "title_content": 1,
    "two_content": 3,   # index 3 is "Two Content"
}
```

Fix 2 — content placeholder type detection only matched BODY (2), but the default template's "Title and Content" (index 1) and "Two Content" (index 3) use OBJECT (7) placeholders, so points were never written:
```python
# BEFORE
if placeholder.type == 2:  # BODY_PLH
    content_box = shape
    break
# AFTER
if placeholder.type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
    content_box = shape
    break
```
Plus added import: `from pptx.enum.shapes import PP_PLACEHOLDER`

## Full file under review
```python
# -*- coding: utf-8 -*-
"""
PPTX构建器
将内容转换为实际的PPT文件
"""
from pathlib import Path
from pptx import Presentation as PptxPresentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.dml.color import RGBColor
from settings_module import Presentation as AppPresentation, Slide


class PPTXBuilder:
    """PPTX文件构建器"""

    # 布局映射（索引对应 python-pptx 默认模板 slide_layouts）
    # 0=Title Slide, 1=Title and Content, 2=Section Header, 3=Two Content
    LAYOUTS = {
        "title_slide": 0,  # 标题布局
        "title_content": 1,  # 标题+内容
        "two_content": 3,  # 双栏
    }

    # 主题色配置
    THEMES = {
        "business": {
            "title_color": (0, 51, 102),  # 深蓝
            "accent_color": (51, 102, 153),  # 浅蓝
            "bg_color": (255, 255, 255),  # 白色
        },
        "academic": {
            "title_color": (102, 51, 0),  # 棕色
            "accent_color": (153, 102, 51),  # 浅棕
            "bg_color": (255, 253, 245),  # 米白
        },
        "creative": {
            "title_color": (102, 0, 102),  # 紫色
            "accent_color": (153, 51, 153),  # 浅紫
            "bg_color": (255, 245, 255),  # 浅粉
        },
    }

    def __init__(self):
        self.themes = self.THEMES

    def build(self, presentation: AppPresentation, output_path: str) -> str:
        """构建PPTX文件"""
        # 创建新的PPTX
        prs = PptxPresentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        # 获取主题
        theme_name = presentation.theme or "business"
        theme = self.themes.get(theme_name, self.themes["business"])

        # 遍历所有幻灯片
        for i, slide in enumerate(presentation.slides):
            # 选择布局
            layout_index = self.LAYOUTS.get(slide.layout, 1)
            try:
                slide_layout = prs.slide_layouts[layout_index]
            except IndexError:
                slide_layout = prs.slide_layouts[1]  # 默认标题+内容

            # 添加幻灯片
            slide_obj = prs.slides.add_slide(slide_layout)

            # 设置标题
            title_box = slide_obj.shapes.title
            if title_box:
                title_frame = title_box.text_frame
                title_frame.clear()
                p = title_frame.paragraphs[0]
                p.text = slide.title
                p.font.size = Pt(36)
                p.font.bold = True
                p.font.color.rgb = self._rgb_to_color(theme["title_color"])
                p.alignment = PP_ALIGN.LEFT

            # 设置内容
            content_box = None
            for shape in slide_obj.shapes:
                if not shape.is_placeholder:
                    continue
                placeholder = shape.placeholder_format
                # 内容区可能是 BODY（Section Header 等）或 OBJECT（Title and Content / Two Content）
                if placeholder.type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
                    content_box = shape
                    break

            if content_box and slide.points:
                tf = content_box.text_frame
                tf.clear()
                for j, point in enumerate(slide.points):
                    if j == 0:
                        p = tf.paragraphs[0]
                    else:
                        p = tf.add_paragraph()
                    p.text = f"• {point}"
                    p.font.size = Pt(18)
                    p.font.color.rgb = self._rgb_to_color(theme["accent_color"])
                    p.space_after = Pt(12)

            # 添加备注（不在幻灯片上显示，仅供演讲者）
            if slide.notes:
                notes_slide = slide_obj.notes_slide
                notes_slide.notes_text_frame.text = slide.notes

        # 保存文件
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))

        return str(output_path)

    def _rgb_to_color(self, rgb_tuple):
        """RGB元组转颜色对象"""
        return RGBColor(*rgb_tuple)

    def preview_html(self, presentation: AppPresentation) -> str:
        """生成HTML预览"""
        html_parts = [
            '<!DOCTYPE html>',
            '<html><head>',
            '<meta charset="UTF-8">',
            '<title>预览 - ' + presentation.title + '</title>',
            '<style>',
            'body { font-family: "Microsoft YaHei", sans-serif; padding: 20px; background: #f5f5f5; }',
            '.slide { background: white; border-radius: 8px; padding: 30px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }',
            '.slide h2 { color: #003366; margin-bottom: 20px; }',
            '.slide ul { line-height: 1.8; }',
            '.slide li { margin: 8px 0; }',
            '.notes { color: #666; font-size: 14px; font-style: italic; margin-top: 20px; padding-top: 10px; border-top: 1px solid #eee; }',
            '</style>',
            '</head><body>',
            f'<h1>{presentation.title}</h1>',
        ]

        for slide in presentation.slides:
            html_parts.append('<div class="slide">')
            html_parts.append(f'<h2>{slide.page}. {slide.title}</h2>')
            html_parts.append('<ul>')
            for point in slide.points:
                html_parts.append(f'<li>{point}</li>')
            html_parts.append('</ul>')
            if slide.notes:
                html_parts.append(f'<div class="notes">备注：{slide.notes}</div>')
            html_parts.append('</div>')

        html_parts.extend(['</body></html>'])
        return ''.join(html_parts)
```

## Verification already done
- `py_compile` passes.
- Read-back of generated .pptx: 3 slides, all titles AND all 9 bullet points now present (previously the 6 points on `title_content` slides were missing).
- Two-content layout maps to the correct "Two Content" layout.

## Your task
Review the correctness of these changes. Specifically check:
1. Is the `two_content` → index 3 mapping correct for the python-pptx default template? (0=Title Slide, 1=Title and Content, 2=Section Header, 3=Two Content)
2. Does `PP_PLACEHOLDER.OBJECT` correctly identify the content area for "Title and Content" and "Two Content" layouts?
3. Any regression risk: does matching BODY or OBJECT risk writing points into the WRONG placeholder (e.g. a date/footer/subtitle placeholder) on any of the 11 default layouts?
4. For `title_slide` (index 0), `shapes.title` will return CENTER_TITLE; is that handled? Any issue with a title_slide having points but no OBJECT/BODY placeholder?
5. Any other bug introduced.

## Required output format (strict)
```
=== CODE REVIEW REPORT ===
Overall Result: PASS / CONDITIONAL PASS / NEEDS_FIX
Risk Summary:
  P0: ...
  P1: ...
  P2: ...
  P3: ...
Findings:
  [F01] Severity: ... | Location: ... | Description: ... | Impact: ... | Recommendation: ...
  ...
Conclusion: ...
```
Be concise. Distinguish real risks from optimization suggestions and personal style preferences. Do NOT output a full replacement implementation.
