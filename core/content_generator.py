# -*- coding: utf-8 -*-
"""
内容生成器
生成完整的PPT内容
"""
from settings_module import get_settings, Presentation
from core.outline_generator import OutlineGenerator


class ContentGenerator:
    """内容生成器"""

    def __init__(self):
        self.settings = get_settings()
        self.outline_generator = OutlineGenerator()

    def generate(
        self,
        topic: str,
        page_count: int = 10,
        language: str = "zh",
        style: str = "Business",
        references: str = "",
        context: str = "",
    ) -> Presentation:
        """从主题直接生成内容"""
        return self.outline_generator.generate(
            topic, page_count, language, style, references=references, context=context
        )
