# 第 14 轮审查请求：Agnes AI 图像集成

## 原始需求（用户）
> 完善ppt内容生成方式，要求内容有质量与丰富度，不要只有大纲，需要详细文字说明与插图。
> 推荐用户使用agnes AI，并把agnes模型生图流程完成，不要过于简单的图片。

（本轮聚焦后两句：Agnes AI 集成 + 图片质量。第 13 轮已实现富文本+插图框架）

## 调查发现的关键根因
1. `$APPDATA/AutoSlide/settings.json`：`ai.base_url="https://apihub.agnes-ai.com/v1"`、`ai.model="agnes-2.5-flash"`（用户已在用 Agnes 文本），但 **`ppt.image_model="dall-e-3"`**（旧配置残留）
2. 最新日志 `autoslide_20260903_130443.log`：`POST .../v1/images/generations` 反复 503
3. **根因**：用 OpenAI 模型名打 Agnes 端点 → 503
4. 次要：venv 是 `httpx2 2.12.0`（openai 3.7.0 依赖），代码 `import httpx` 失败

## 实现摘要
- settings 默认改为推荐 Agnes：`image_provider=agnes`、`image_model=agnes-image-2.1-flash`、`image_base_url=apihub.agnes-ai.com/v1`、`image_api_key=""`（留空复用 ai.api_key 或环境变量 AGNES_API_KEY）、`image_size=1024x768`
- settings_dialog 新增图像服务区（服务下拉框+模型/BaseURL/Key/尺寸+绿色推荐标签），切换自动填预设，`_loading` 防回填
- image_generator._connect：Key 优先级 image_api_key > ai.api_key > env AGNES_API_KEY；用 image_base_url；timeout=120.0 float
- image_generator._generate_ai：provider=agnes 时 extra_body={"response_format":"url"} 明确 URL 返回
- ai_client + image_generator 去掉 `import httpx`，改 `timeout=浮点数` 兼容 httpx/httpx2
- prompt_builder image_prompt 强化：结构化（主体+场景+风格+光照+构图+质量词）
- 兜底图增强：渐变+网格+装饰圆+圆角白卡+主题条+分隔线+水印
- spec hiddenimports 加 `'httpx2'`

## 修改文件
- settings_module/settings.py
- ui/settings_dialog.py
- core/image_generator.py
- core/ai_client.py
- core/prompt_builder.py
- autoslide.spec

## 关键 Diff（核心逻辑）
```python
# image_generator.py _generate_ai 新增 extra_body
if provider == "agnes":
    kwargs["extra_body"] = {"response_format": "url"}

# _connect Key 优先级 + base_url + 兼容 timeout
api_key = (ppt_cfg.get("image_api_key", "")
           or config.get("api_key", "")
           or os.environ.get("AGNES_API_KEY", ""))
base_url = ppt_cfg.get("image_base_url", "") or "https://apihub.agnes-ai.com/v1"
self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=120.0)
```

## 验证结果
- py_compile 全部通过
- Agnes API 真实调用成功：samples/agnes_demo.png (997 KB, 1024×768) — 开发者+Code/Team 霓虹指示牌完整场景
- 兜底图：samples/fallback_demo.png (35 KB)，含网格+卡片+主题条+水印
- _test_export.py 全量 5 项全绿
- exe 重新打包 59.4 MB，启动正常，日志正常

## 审查范围
请审查以上实现是否有 P0/P1/P2/P3 风险，特别是：
- extra_body response_format=url 参数兼容性
- Key 优先级链是否合理（环境变量兜底是否安全）
- 默认配置改为 Agnes 是否会影响 OpenAI 用户
- 兜底图渲染逻辑是否健壮
- 其他可能的安全/并发/兼容问题

请独立判断，禁止修改代码，仅输出 CODE REVIEW REPORT 格式报告。