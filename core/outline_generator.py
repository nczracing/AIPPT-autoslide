# -*- coding: utf-8 -*-
"""
大纲生成器
调用AI生成PPT大纲
"""
import logging

from settings_module import get_settings, Presentation, Slide
from core.prompt_builder import PromptBuilder
from core.ai_client import AIClient

logger = logging.getLogger("autoslide")


class OutlineGenerator:
    """大纲生成器"""

    def __init__(self):
        self.settings = get_settings()
        self.prompt_builder = PromptBuilder()
        self.ai_client = AIClient()

    def generate(
        self,
        topic: str,
        page_count: int = 10,
        language: str = "zh",
        style: str = "Business",
        references: str = "",
        context: str = "",
    ) -> Presentation:
        """生成演示文稿大纲

        references: 用户提供的参考文献文本（每行一条）。会注入 Prompt 让正文基于
        这些文献撰写，并在末尾统一追加一页「参考文献」。
        context: 用户提供的参考资料/背景材料（自由文本），仅用于让 AI 更好理解
        内容侧重点，不追加额外页面。
        """
        # 构建Prompt
        prompt = self.prompt_builder.build_outline_prompt(
            topic=topic,
            page_count=page_count,
            language=language,
            style=style,
            references=references,
            context=context,
        )

        # 调用AI（富文本内容更长，放宽 max_tokens，避免正文被截断）
        result = self.ai_client.generate_json(prompt, max_tokens=8192)

        # 解析结果
        slides_data = result.get("slides", [])
        if not slides_data:
            raise ValueError("AI未返回有效的大纲内容")

        # 构建Presentation对象
        theme = {
            "Business": "business",
            "Academic": "academic",
            "Creative": "creative",
            "Tech": "tech",
            "Vibrant": "vibrant",
        }.get(style, "business")
        presentation = Presentation(
            title=topic,
            theme=theme,
            language=language,
        )

        for slide_data in slides_data:
            slide = Slide(
                page=slide_data.get("page", 0),
                title=slide_data.get("title", ""),
                points=slide_data.get("points", []),
                detail=slide_data.get("detail", ""),
                notes=slide_data.get("notes", ""),
                layout=slide_data.get("layout", "title_content"),
                image_prompt=slide_data.get("image_prompt", ""),
            )
            # 插图布局：优先采用 AI 按内容语义的选择，非法值回退确定性轮换
            if slide.image_prompt and slide.layout != "title_slide":
                slide.image_layout = self._normalize_image_layout(
                    slide_data.get("image_layout"), slide.page
                )
            else:
                slide.image_layout = "right"
            presentation.add_slide(slide)

        # 追加「参考文献」页（用户提供了参考文献时）
        ref_items = self._parse_references(references)
        if ref_items:
            presentation.add_slide(
                Slide(
                    page=len(presentation.slides) + 1,
                    title="参考文献" if language == "zh" else "References",
                    points=ref_items,
                    detail="",
                    notes="",
                    layout="references",
                    image_prompt="",
                )
            )

        return presentation

    VALID_IMAGE_LAYOUTS = ("right", "left", "top", "bottom", "fullscreen")

    @classmethod
    def _normalize_image_layout(cls, value, page: int = 0) -> str:
        """校验 AI 返回的插图布局；非法/缺失时按页码确定性轮换回退。

        轮换序列 (right, left, top, bottom) 保证版式多样性且同内容可复现。
        """
        if isinstance(value, str) and value.strip().lower() in cls.VALID_IMAGE_LAYOUTS:
            return value.strip().lower()
        if value:
            logger.warning(
                "AI 返回非法 image_layout '%s'（第%s页），回退轮换选择", value, page
            )
        import random
        rng = random.Random(page)
        return rng.choice(("right", "left", "top", "bottom"))

    @staticmethod
    def _parse_references(references: str):
        """解析参考文献文本为条目列表（按行拆分，去空行）。"""
        refs = (references or "").strip()
        if not refs:
            return []
        items = []
        for line in refs.splitlines():
            line = line.strip()
            if line:
                items.append(line)
        return items
