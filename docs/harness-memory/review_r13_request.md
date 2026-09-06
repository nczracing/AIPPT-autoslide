# Claude 独立审查请求 — 第 13 轮（富文本内容 + 插图功能）

## 原始需求
用户希望"完善 PPT 内容生成方式，要求内容有质量与丰富度，不要只有大纲，需要详细文字说明与插图"。
- 之前只有"标题 + 几个要点"的大纲式内容（短、干瘪）
- 需要为每页加上详细段落正文（事实/数据/例子）
- 需要为每页配插图

## 实现摘要
1. **数据模型扩展** (`settings_module/models.py`)：`Slide` 新增 `detail`(详细正文)、`image_prompt`(插图提示词)、`image_path`(插图路径) 三个字段。
2. **Prompt 重写** (`core/prompt_builder.py`)：`OUTLINE_PROMPT_TEMPLATE` 要求 AI 每页产出 detail 详细段落（80-180 字具体事实/例子），同时为内容页产出 image_prompt。
3. **token 上调**：调用 `generate_json` 时 `max_tokens=8192`，避免富文本被截断。
4. **新模块** `core/image_generator.py`：每页插图生成
   - AI 图像 API 优先（OpenAI images API，gpt-image-1 或 dall-e-3，支持 b64_json 与 url 两种返回）
   - Pillow 主题示意图兜底（渐变 + 装饰圆 + CJK 字体渲染中文标题）
   - 任一步骤失败均优雅跳过（返回 None，绝不抛异常中断生成）
5. **PPTX 构建器重写** (`core/pptx_builder.py`)：图文混排布局
   - 16:9 横屏
   - 标题占顶部，正文为左侧文本框，插图为右侧 add_picture
   - 渲染顺序：详细正文段落 + 要点列表
   - 封面使用 detail 作为副标题
   - 双栏布局拆要点到左右两个 OBJECT 占位符
6. **HTML 预览**：`detail` 与 `image_path` 都嵌入预览（图片 base64 内嵌）。
7. **预览面板** (`ui/preview_widget.py`)：增加 detail 段落与 base64 内嵌插图。
8. **生成线程** (`ui/generator_widget.py`)：内容生成后逐页生成插图，逐页发 `progress` 信号，单页失败不阻断。
9. **设置** (`settings_module/settings.py`, `ui/settings_dialog.py`)：新增 `ppt.enable_images`（默认 True）与 `ppt.image_model`（默认 gpt-image-1），设置对话框加勾选框。
10. **测试** (`_test_export.py`)：扩展为 5 项验证（生成兜底图、PPTX 导出、HTML 预览、QTextBrowser 渲染、PPTX 读回含 detail+图片）。

## 修改文件清单
- settings_module/models.py
- core/prompt_builder.py
- core/ai_client.py
- core/image_generator.py (新增)
- core/outline_generator.py
- core/pptx_builder.py
- ui/preview_widget.py
- ui/generator_widget.py
- ui/settings_dialog.py
- settings_module/settings.py
- autoslide.spec (新增 openai.resources、PIL.ImageDraw、PIL.ImageFont 隐藏导入)
- _test_export.py (测试扩展)

## 验证结果
- 全部文件 py_compile 通过
- _test_export.py 全部通过：3 页标题 + 9 个要点 + detail 正文 + 1 张插图（含 base64 内嵌）
- 兜底插图渲染中文无乱码（msyh.ttc）
- exe 重新打包成功（59.4 MB），启动正常进入事件循环，日志正常生成

## 审查重点
1. **数据模型扩展**：新字段是否向后兼容？`to_json` 是否完整？
2. **Prompt 工程**：能否确保 AI 输出符合 detail 长度约束（80-180 字）？image_prompt 是否会污染封面/致谢？
3. **插图容错链路**：AI 失败→Pillow 失败→None 的三级降级是否真正做到"绝不抛异常中断生成"？
4. **PPTX 图文混排**：双栏布局 fallback（仅有 1 个内容区时）是否正确退化？插图插入失败是否会被吞掉而无声？
5. **线程安全**：ImageGenerator 在 QThread 内实例化是否安全？每页单独 try 是否隔离？
6. **资源管理**：临时图片目录 %TEMP%/AutoSlide/images/ 是否会无限增长？
7. **CJK 字体**：仅 Windows 路径，若其他平台字体找不到是否正常跳过？
8. **PyInstaller 隐藏导入**：是否覆盖 openai.resources.images、PIL.ImageDraw、PIL.ImageFont？

## 输出格式
按规则输出：
- Overall Result: PASS / PASS_WITH_NOTES / FAIL
- Risk Summary（P0/P1/P2/P3 列表）
- Findings（每个 finding 含 7 字段：Severity / Location / Issue / Impact / Recommendation / Risk Acceptance / Verdict）
- Verdict（本次审查结论 + 是否接受风险）