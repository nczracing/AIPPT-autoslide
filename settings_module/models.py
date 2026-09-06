# -*- coding: utf-8 -*-
"""
数据模型定义
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Slide:
    """单页幻灯片

    字段说明：
    - points: 关键要点（视觉摘要，3-4 条短语）
    - detail: 详细文字说明（正文段落，阐述要点的具体事实/例子/数据/推理）
    - notes: 演讲者备注（提词，非放映内容）
    - image_prompt: 插图提示词（英文，供图像生成使用；封面/目录/致谢留空）
    - image_path: 本地插图路径（生成阶段填充，供预览与导出使用）
    - image_layout: 插图布局模式，可选值：
        "right"（默认）：图片在右侧
        "left"：图片在左侧
        "top"：图片在上方，文字在下方
        "fullscreen"：图片铺满全屏作为背景（不叠加正文）
    """
    page: int
    title: str
    points: List[str] = field(default_factory=list)
    detail: str = ""
    notes: str = ""
    layout: str = "title_content"
    image_prompt: str = ""
    image_path: str = ""
    image_layout: str = "right"


@dataclass
class Presentation:
    """完整演示文稿"""
    title: str
    slides: List[Slide] = field(default_factory=list)
    theme: str = "business"
    language: str = "zh"

    def add_slide(self, slide: Slide):
        """添加幻灯片"""
        slide.page = len(self.slides) + 1
        self.slides.append(slide)

    def to_json(self) -> dict:
        """转换为JSON"""
        return {
            "title": self.title,
            "slides": [
                {
                    "page": s.page,
                    "title": s.title,
                    "points": s.points,
                    "detail": s.detail,
                    "notes": s.notes,
                    "layout": s.layout,
                    "image_prompt": s.image_prompt,
                    "image_path": s.image_path,
                }
                for s in self.slides
            ],
            "theme": self.theme,
            "language": self.language,
        }
