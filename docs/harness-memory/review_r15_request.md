# 第 15 轮审查请求：参考文献输入与引用

## 原始需求（用户）
> 增加一个输入窗口，使用户可以输入参考文献，生成的ppt需要参考这些文献

## 实现摘要
1. **UI 输入**（ui/generator_widget.py）：主界面新增多行 `QTextEdit` 参考文献输入框（可选，每行一条）；`GenerateThread` 增加 `references` 参数并在 `run()` 中传递给 `OutlineGenerator.generate(..., references=...)`；`start_generate` 读取 `references_input.toPlainText().strip()` 传入线程。
2. **Prompt 注入**（core/prompt_builder.py）：`OUTLINE_PROMPT_TEMPLATE` 新增 `{references_block}` 占位符；`build_outline_prompt` 新增 `references` 参数；`_build_references_block` 生成「文献约束段」（要求正文 detail/points 自然引用文献观点/数据/结论、不编造、无需额外生成参考文献页）。
3. **自动追加参考文献页**（core/outline_generator.py）：`generate` 新增 `references` 参数并注入 prompt；生成后 `_parse_references`（按行拆分、去空行）追加 `layout="references"` 的「参考文献」页，标题中文「参考文献」/ 英文「References」。
4. **PPTX/预览渲染**（core/pptx_builder.py + ui/preview_widget.py）：`build()` 识别 `layout=="references"` → 新增 `_fill_references`（13pt 常规字 + `[i]` 编号，区别于要点页的 bold+accent 18pt）；`preview_html` 加 `.refs` 样式（无圆点、编号、正文色）；`preview_widget.update_preview` 同步编号渲染。
5. **内容生成透传**（core/content_generator.py）：`generate` 新增 `references` 参数透传给 outline_generator。

## 修改文件
- core/prompt_builder.py
- core/outline_generator.py
- core/content_generator.py
- core/pptx_builder.py
- ui/generator_widget.py
- ui/preview_widget.py

## 关键 Diff（核心逻辑）
```python
# prompt_builder.py —— 用唯一占位符承载参考文献原文，避免 .format() 解析用户文本中的 {} / % 等字符
def build_outline_prompt(self, topic, page_count=10, language="zh", style="Business", references=""):
    ref_block = self._build_references_block(references)
    prompt = self.OUTLINE_PROMPT_TEMPLATE.format(
        topic=topic, page_count=page_count, language=language, style=style,
        references_block="__REFERENCES_PLACEHOLDER__",
    )
    return prompt.replace("__REFERENCES_PLACEHOLDER__", ref_block)

# outline_generator.py —— 生成后追加参考文献页
ref_items = self._parse_references(references)
if ref_items:
    presentation.add_slide(Slide(
        page=len(presentation.slides) + 1,
        title="参考文献" if language == "zh" else "References",
        points=ref_items, detail="", notes="", layout="references", image_prompt="",
    ))

# pptx_builder.py —— 参考文献页小字号编号渲染
def _fill_references(self, slide_obj, slide, theme):
    tf = self._content_textbox(slide_obj, has_image=False)
    tf.clear()
    for i, item in enumerate(slide.points or [], 1):
        p = tf.paragraphs[0] if i == 1 else tf.add_paragraph()
        p.text = f"[{i}] {item}"
        p.font.size = Pt(13); p.font.bold = False
        p.font.color.rgb = self._rgb_to_color(theme["text_color"])
        p.space_after = Pt(8); p.line_spacing = 1.15
```

## 验证结果
- py_compile 全部通过
- `_test_export.py` 全量 5 项全绿（未破坏原有富文本+插图链路）
- prompt 注入专项：参考文献含 `{}` / `%` 特殊字符不报错、原文完整进入 prompt；空 references 不注入约束
- `_parse_references` 解析正确（去空行）
- PPTX 读回：参考文献页文本为 `[1] [2] [3]` 编号、无要点圆点；标题「参考文献」
- preview_html 含 `class="refs"` 且编号渲染
- mock AI 端到端：带参考文献追加页 / 英文标题 References / 无参考文献不追加 —— 全绿
- exe 重新打包 59.4 MB，冒烟测试启动正常、无闪退、日志正常

## 审查范围
请独立审查以上实现是否有 P0/P1/P2/P3 风险，特别关注：
1. `.format()` + `replace` 占位符方案是否真的安全（用户参考文献文本含 `{`、`}`、`%`、`\n`、URL 等）
2. 参考文献页复用 `points` 字段承载条目、用 `layout="references"` 标记是否会导致其他环节（如 `_derive_slide_visual`、装饰母题、密度计算、`LAYOUTS.get` fallback）出现意外
3. 参考文献条目超长时 PPTX 排版是否溢出（`_fill_references` 未做自动缩小/分栏）
4. 参考文献页是否会被插图生成逻辑误处理（`image_prompt=""` 是否正确跳过）
5. `GenerateThread` 线程安全、`references` 传递链路完整性
6. 其他兼容性/健壮性问题

请独立判断，禁止修改代码，仅输出 CODE REVIEW REPORT 格式报告。
