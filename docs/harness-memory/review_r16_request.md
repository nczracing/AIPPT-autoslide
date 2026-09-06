# 第 16 轮审查请求：参考材料/背景材料输入框（非必填）

## 原始需求（用户）
> 还要在用户生成ppt的界面增加一个输入框（不是必填），用于进一步了解用户所要生成的ppt的内容，供用户提供参考资料

## 实现摘要
1. **UI 输入**（ui/generator_widget.py）：在「参考文献 References」输入框下方新增多行 `QTextEdit context_input`（可选、高 88px），placeholder 说明「自由文本、非必填、不追加额外页面」；`GenerateThread` 增加 `context` 参数并在 `run()` 中传给 `OutlineGenerator.generate(..., context=...)`；`start_generate` 读取 `context_input.toPlainText().strip()` 传入线程。
2. **Prompt 注入**（core/prompt_builder.py）：`OUTLINE_PROMPT_TEMPLATE` 新增 `{context_block}` 占位符；`build_outline_prompt` 新增 `context` 参数；新增 `_build_context_block` 生成「背景材料约束段」（要求 AI 从材料提取关键事实/数据/观点/术语/结构建议融入正文 points/detail，忠实原文但不整段照抄、非正式引文）。
3. **大纲生成透传**（core/outline_generator.py）：`generate` 新增 `context` 参数并注入 prompt；**不追加额外页面**（与 references 区别）。
4. **内容生成透传**（core/content_generator.py）：`generate` 新增 `context` 参数透传。

## 修改文件
- core/prompt_builder.py
- core/outline_generator.py
- core/content_generator.py
- ui/generator_widget.py

## 关键 Diff（核心逻辑）
```python
# prompt_builder.py —— context 与 references 共用「占位符 + replace」安全方案
def build_outline_prompt(self, topic, page_count=10, language="zh", style="Business", references="", context=""):
    ref_block = self._build_references_block(references)
    context_block = self._build_context_block(context)
    prompt = self.OUTLINE_PROMPT_TEMPLATE.format(
        topic=topic, page_count=page_count, language=language, style=style,
        references_block="__REFERENCES_PLACEHOLDER__",
        context_block="__CONTEXT_PLACEHOLDER__",
    )
    prompt = prompt.replace("__REFERENCES_PLACEHOLDER__", ref_block)
    return prompt.replace("__CONTEXT_PLACEHOLDER__", context_block)

@staticmethod
def _build_context_block(context: str) -> str:
    ctx = (context or "").strip()
    if not ctx:
        return ""
    return (
        "Background reference material provided by the user (helps understand "
        "the intended content of this presentation):\n" + ctx +
        "\n\nUse the material above to enrich the presentation: ... "
        "Stay faithful to the material — do not contradict it — but do not copy it "
        "verbatim as a single block. The material is guidance for content, NOT a "
        "list of formal citations."
    )
```

```python
# generator_widget.py —— 新增 context 输入框 + 线程透传
def __init__(self, topic, page_count, language, style, references="", context=""):
    ...
    self.context = context

# init_ui 中（references_input 之后）：
layout.addWidget(QLabel('参考材料 / Reference Materials (optional)'))
self.context_input = QTextEdit()
self.context_input.setPlaceholderText('Paste background materials here ... 非必填 ...')
self.context_input.setFixedHeight(88)
layout.addWidget(self.context_input)

# start_generate 中：
context = self.context_input.toPlainText().strip()
self.thread = GenerateThread(topic, pages, language, style, references, context)
```

## 验证结果
- py_compile：4 个修改文件全部通过
- PromptBuilder 专项 4 用例全绿：
  1. 空 context/references 不注入约束、无残留占位符
  2. 仅 context（含中文 + `{}` 字符）正确注入且保留原文
  3. references + context 同时注入，两者约束段并存
  4. context 含 `{a:b} {{c}} 100%` 不触发 `.format()` KeyError
- GeneratorWidget 离屏渲染通过：`context_input` / `references_input` 均就绪，空输入 `.strip()==""`
- exe 重新打包 59.4 MB，冒烟测试进程存活、日志无报错

## 审查范围
请独立审查以上实现是否有 P0/P1/P2/P3 风险，特别关注：
1. `{context_block}` 与 `{references_block}` 两个占位符并存时，`.format()` + `replace` 方案是否仍安全（用户 context 文本含 `{` `}` `%` `\n` URL 等；两个 replace 顺序是否有干扰）
2. context 与 references 语义是否清晰区分（前者不追加页、后者追加页），是否可能互相混淆或 Prompt 冲突
3. context 超长（用户粘贴大段材料）时 Prompt 是否失控（无截断/长度限制），是否影响 token 上限（generate_json max_tokens=8192）
4. `GenerateThread` 新增 `context` 位置参数后，所有调用点（含可能的测试/旧代码）是否兼容；`context` 默认值 `""` 是否保证向后兼容
5. 空 context 时是否真的零副作用（无空约束段、无空占位符残留、无额外页面）
6. 其他兼容性/健壮性问题

请独立判断，禁止修改代码，仅输出 CODE REVIEW REPORT 格式报告。
