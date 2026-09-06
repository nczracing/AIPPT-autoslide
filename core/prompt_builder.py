# -*- coding: utf-8 -*-
"""
Prompt构建器
负责生成调用AI的提示词
"""


class PromptBuilder:
    """Prompt构建器"""

    # 用户输入的长度上限，防止超长材料撑爆 Prompt / 稀释有效信息
    MAX_CONTEXT_CHARS = 4000
    MAX_REFERENCES_CHARS = 2000

    OUTLINE_PROMPT_TEMPLATE = """You are a professional presentation content creator. Create rich, substantive PPT content for the following topic.

Topic: {topic}
Pages: {page_count}
Language: {language}
Style: {style}

{references_block}

{context_block}

IMPORTANT — Output language: if Language is "zh", write ALL text fields (title, points, detail, notes) in Simplified Chinese; if "en", write in English. The "image_prompt" field must ALWAYS be in English.

Content quality requirements (this is the core value — do NOT output a bare outline):
1. Generate exactly {page_count} slides following a clear narrative arc: Cover -> Agenda -> Content sections (with a logical progression) -> Summary -> Thanks.
2. Every slide must contain these fields:
   - "title": a concise, specific slide title (no generic labels).
   - "points": 3-4 key points, each a short punchy phrase — this is the visual summary of the slide.
   - "detail": a substantive explanatory paragraph (about 80-180 字 — Chinese characters count as one each, English words also count as one) that actually explains the points with concrete facts, data, examples, mechanisms, or reasoning. Avoid empty filler and clichés; make each paragraph informative and specific to the topic.
   - "notes": speaker notes (30-80 characters) with delivery guidance for the presenter.
   - "layout": use "title_slide" for the cover, "title_content" for normal content slides, "two_content" only for comparison/contrast slides.
   - "image_layout": the illustration placement for this slide, chosen from "right" / "left" / "top" / "bottom" / "fullscreen". Decide by content semantics AND visual rhythm across the deck:
     * "right" or "left": default for most content slides — a supporting illustration beside the text; alternate them for variety.
     * "top" or "bottom": wide banner visuals — best for timelines, data trends, roadmaps, landscape scenes, process flows.
     * "fullscreen": immersive background — use sparingly (at most 1-2 slides per deck), ideal for section dividers or emotional/atmospheric slides; the text overlays a dark scrim on the image.
     * Do not repeat the same value more than twice in a row; keep the deck visually rhythmic.
   - "image_prompt": a vivid, detailed English prompt for a high-quality illustration, structured as: subject + scene + style + lighting + composition + quality tags (e.g. "A confident young software engineer standing at a crossroads with three glowing signposts labeled code, team and product, warm studio lighting, flat vector illustration with subtle gradients and soft shadows, clean balanced composition, high detail"). Be concrete and specific — name objects, colors, mood and perspective; prefer informative, well-composed, information-rich visuals over minimal icons. Provide it for content slides where a visual genuinely adds value; leave it as an empty string "" for the cover, agenda, summary, thanks slides, and any text-heavy slide where an illustration would be redundant.
3. Be accurate and specific — cite real concepts, numbers, or examples appropriate to the topic. Tailor depth to the audience implied by the topic.
4. Keep the JSON valid: use double quotes, separate keys/values and array items with commas, no trailing commas, no comments.

Output ONLY valid JSON in the following shape:
{{
  "slides": [
    {{
      "page": 1,
      "title": "Slide Title",
      "points": ["Key point 1", "Key point 2", "Key point 3"],
      "detail": "A substantive paragraph explaining the points with concrete facts or examples.",
      "notes": "Delivery guidance for the speaker.",
      "layout": "title_content",
      "image_layout": "right",
      "image_prompt": "English description of an illustration for this slide"
    }}
  ]
}}"""

    CONTENT_PROMPT_TEMPLATE = """Please expand the following PPT outline into complete presentation content:

Outline:
{outline}

Requirements:
1. Keep each slide concise and powerful, suitable for presentation
2. Control points to 3-5 per slide, each point no more than 20 characters
3. Add appropriate speaker notes (30-50 characters each)
4. Maintain professional tone and coherence

Output complete content in JSON format."""

    SUMMARY_PROMPT_TEMPLATE = """Please generate a brief summary for the following content (max {max_length} characters):

{content}"""

    def build_outline_prompt(
        self,
        topic: str,
        page_count: int = 10,
        language: str = "zh",
        style: str = "Business",
        references: str = "",
        context: str = "",
    ) -> str:
        """构建大纲生成Prompt

        references: 用户提供的参考文献文本（每行一条），用于让内容严格基于这些文献
        并在正文中自然引用；同时提示无需额外生成参考文献页（由代码统一追加）。
        context: 用户提供的参考资料/背景材料（自由文本），用于让 AI 进一步理解
        用户想要的 PPT 内容（侧重点、素材、要点等）。
        """
        ref_block = self._build_references_block(references)
        context_block = self._build_context_block(context)

        # 用唯一占位符承载用户原文，避免 .format() 解析用户文本中的 { } 等字符
        prompt = self.OUTLINE_PROMPT_TEMPLATE.format(
            topic=topic,
            page_count=page_count,
            language=language,
            style=style,
            references_block="__REFERENCES_PLACEHOLDER__",
            context_block="__CONTEXT_PLACEHOLDER__",
        )
        prompt = prompt.replace("__REFERENCES_PLACEHOLDER__", ref_block)
        return prompt.replace("__CONTEXT_PLACEHOLDER__", context_block)

    @staticmethod
    def _build_references_block(references: str) -> str:
        """构造参考文献约束段落；无参考文献时返回空串。"""
        refs = (references or "").strip()
        if not refs:
            return ""
        if len(refs) > PromptBuilder.MAX_REFERENCES_CHARS:
            refs = refs[: PromptBuilder.MAX_REFERENCES_CHARS] + "\n...(参考文献过长，已截断)..."
        return (
            "Reference materials — the presentation content MUST be grounded in and "
            "cite these references:\n"
            + refs
            + "\n\nWhen writing each slide's 'detail' and 'points', naturally incorporate "
            "and attribute the ideas, findings, data, or viewpoints from the above "
            "references (e.g. 'according to ...', '... demonstrated that ...', 'X et al. found ...'). "
            "Do NOT fabricate facts that contradict the references, and keep the tone academic. "
            "You do NOT need to output a separate references slide — one will be appended automatically."
        )

    @staticmethod
    def _build_context_block(context: str) -> str:
        """构造参考资料/背景材料约束段落；无内容时返回空串。"""
        ctx = (context or "").strip()
        if not ctx:
            return ""
        if len(ctx) > PromptBuilder.MAX_CONTEXT_CHARS:
            ctx = ctx[: PromptBuilder.MAX_CONTEXT_CHARS] + "\n...(参考材料过长，已截断)..."
        return (
            "Background reference material provided by the user (helps understand "
            "the intended content of this presentation):\n"
            + ctx
            + "\n\nUse the material above to enrich the presentation: extract key "
            "facts, data, viewpoints, terminology, and structure suggestions from it, "
            "and incorporate them into the slides' 'points' and 'detail' where relevant. "
            "Stay faithful to the material — do not contradict it — but do not copy it "
            "verbatim as a single block. The material is guidance for content, NOT a "
            "list of formal citations."
        )

    def build_content_prompt(self, outline: dict) -> str:
        """构建内容扩写Prompt"""
        import json
        return self.CONTENT_PROMPT_TEMPLATE.format(
            outline=json.dumps(outline, ensure_ascii=False, indent=2),
        )

    def build_summary_prompt(self, content: str, max_length: int = 200) -> str:
        """构建摘要Prompt"""
        return self.SUMMARY_PROMPT_TEMPLATE.format(
            max_length=max_length,
            content=content,
        )
