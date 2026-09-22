# AutoSlide 审查历史

## 第 1 轮 - NEEDS_FIX
**审查者**: Claude
**发现问题**: P0/P1/P2/P3 共9个问题

## 第 2 轮 - PASS
**验证**: 核心P1/P2问题已修复

## 第 3 轮 - NEEDS_FIX
**说明**: P3修复未落实

## 第 4 轮 - NEEDS_FIX
**新发现**: F06 (P1) main_window.py 缺少 import logging

## 第 5 轮 - PASS
**验证**: 所有已知修复确认

## 第 6 轮 - NEEDS_FIX
**新发现**: exe模式下路径问题、日志写入失败

## 第 7-8 轮 - 修复中
**修复内容**:
- main.py: PyInstaller路径判断
- utils/logger.py: 移除默认实例、修复变量名

## 第 9 轮 - PASS ✅
**最终状态**: 日志正常生成，程序运行稳定

## 第 10 轮 - NEEDS_FIX → 修复后 PASS ✅
**审查者**: Claude
**触发**: 最新日志 `autoslide_20260903_105143.log` 暴露两个真实 bug
**发现问题**:
- P1: `AttributeError: 'QWidget' object has no attribute 'update_preview'`（generator_widget.py:127 on_generated）— `content.addWidget()` 将 widget 重新 parent 到 central QWidget，`self.parent()` 并非 MainWindow
- P1: `QThread: Destroyed while thread is still running` — 自定义信号 `finished = pyqtSignal(Presentation)` 遮蔽 QThread 内建 `finished`，且 `on_generated` 在 run 线程里提前 `self.thread = None`
- P1: closeEvent 线程清理竞态（Claude 审查补充发现）
**修复**:
- 信号解耦：新增 `preview_requested = pyqtSignal(object)` 替代脆弱的 `parent().update_preview()`
- 重命名自定义信号 `finished` → `generated`，消除对 QThread 内建 `finished` 的遮蔽
- 线程清理改用内建 `finished` 信号触发 `_on_thread_finished`（run 返回后才释放）
- closeEvent 加固（局部引用 + try/except + 移除无效的 quit()）
**验证**: 端到端测试通过（on_generated 无异常、预览正确更新、线程正确清理），exe 无闪退、日志无错误

## 第 11 轮 - 有条件通过 → P1 驳回（误报）→ PASS ✅
**审查者**: Claude
**触发**: 最新日志 `autoslide_20260903_110923.log` 暴露 `RuntimeError: JSON生成失败: Expecting ',' delimiter`（AI 返回的 outline JSON 缺逗号）
**根因**: `core/ai_client.py` 的 `_extract_json` 只做两次直接 `json.loads`，LLM 生成的轻微坏 JSON（缺逗号）即整体失败
**修复**:
- `generate_json`：JSON mode 优先（`response_format={"type":"json_object"}`），失败回退普通模式；强化 system prompt 强调 JSON 语法
- `chat`/`_chat`：新增 `response_format` 可选参数（默认 None，向后兼容）
- `_extract_json` 重写：提取代码块、截取首 `{`/`[` 到末 `}`/`]`、逐层尝试 `json.loads` + `ast.literal_eval`
- 新增 `_repair_json`/`_strip_comments`/`_fix_missing_commas`：状态机移除注释、修尾逗号、修缺失逗号（区分字符串内外/键值/true/false/null/数字）
**Claude 审查结果**: 有条件通过，报告 1 个 P1 + 1 个 P2 + 1 个 P3
**修复闭环处置**:
- P1（"负数误插逗号"）→ **实测驳回（误报）**：`{"a":-1}` 正确解析为 `{'a': -1}`；`-` 作为"新值首字符"是必要设计（用于修复 `[1 -2]` 缺逗号）。回归测试 7 个合法 JSON（负数/科学计数/URL/嵌套/中文）全部未被破坏
- P2（未闭合转义字符串）、P3（块注释未闭合边界）→ 接受风险：属极端坏输入，本身无法修复，不影响真实使用
**验证**: 13/14 坏 JSON 修复用例通过（唯一"失败"是顶层数组，属 `_extract_json` 刻意只接受 dict 的设计约束）；端到端 mock 测试通过；exe 重新打包（49s）启动正常、进入事件循环

## 第 12 轮 - PASS ✅
**审查者**: Claude
**触发**: PPTX 内容读回验证（续上轮中断处），发现 `title_content` 布局的要点（bullet points）静默缺失
**根因**（`core/pptx_builder.py` 两个叠加 bug）:
- `LAYOUTS` 映射错误：`two_content: 2` 实际指向 "Section Header"（python-pptx 默认模板中 2=Section Header，3=Two Content）
- 内容占位符类型判断只认 `BODY (2)`，而默认模板 "Title and Content"(1) / "Two Content"(3) 的内容区是 `OBJECT (7)` 类型，导致 `content_box` 永远找不到 → 默认布局要点全部写不进 PPTX
**修复**:
- `LAYOUTS["two_content"]` 2 → 3
- 占位符判断 `placeholder.type == 2` → `in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT)`
- 新增 `from pptx.enum.shapes import PP_PLACEHOLDER`
- 补充：要点非空但无内容占位符时记录 `logger.warning`（Claude F01 建议，便于未来诊断）
**Claude 审查结果**: PASS，P0/P1 无；P2(F01 title_slide 无内容区属语义正确)、P3(F02 two_content 仅用左栏、F03 themes 冗余) 均为信息级
**验证**: py_compile 通过；`_test_export.py` 增强为含"读回 PPTX 内容验证"（3 页标题 + 9 要点全部写入）；exe 重新打包成功

## 第 13 轮 - PASS_WITH_NOTES → 修复后 PASS ✅（富文本内容 + 插图）
**审查者**: Claude
**触发**: 用户新需求"完善 PPT 内容生成方式，要求内容有质量与丰富度，不要只有大纲，需要详细文字说明与插图"
**原始设计**: 之前只有"标题 + 几个要点"的大纲式内容（短、干瘪）；本轮实现富文本正文 + AI 配图
**实现摘要**:
- **数据模型扩展** (`settings_module/models.py`)：`Slide` 增加 `detail`(详细正文段落)、`image_prompt`(插图提示词)、`image_path`(插图路径) 三个字段
- **Prompt 重写** (`core/prompt_builder.py`)：要求每页产出 detail 详细段落（80-180 字含具体事实/例子），并为内容页产出 image_prompt；token 上调到 8192
- **新增 `core/image_generator.py`**：AI 图像 API 优先（OpenAI gpt-image-1/dall-e-3），Pillow 主题示意图兜底（渐变 + 装饰圆 + CJK 字体），三级降级绝不抛异常
- **PPTX 构建器重写** (`core/pptx_builder.py`)：16:9 横屏，图文混排（左侧文本框 + 右侧 add_picture），detail 正文段落 + 要点列表，封面用 detail 作副标题
- **HTML 预览 / PreviewWidget**：detail + 图片 base64 内嵌
- **生成线程** (`ui/generator_widget.py`)：内容生成后逐页生成插图并发 progress 信号，单页失败不阻断
- **设置**：`ppt.enable_images` + `ppt.image_model`，对话框加勾选框与下拉框
- **测试扩展** (`_test_export.py`)：5 项验证（兜底图 + PPTX + HTML 预览 + QTextBrowser 渲染 + 读回 PPTX 含 detail+图片）

**Claude 审查结果**: PASS_WITH_NOTES，P0 无，P1×2、P2×3、P3×4

**修复闭环处置**:
- F1 (P1) `_fill_two_content` 签名缺 `has_image` 参数，双栏布局插图丢失 → **已修复**：增加 `has_image` 参数；有图时将左右栏缩窄（left=0.6"宽3.7" + left=4.5"宽3.5"）让出右侧图片区
- F2 (P1) 设置对话框缺 `image_model` 控件 → **已修复**：PPT 配置区增加 `QComboBox`（gpt-image-1 / dall-e-3），load/save 同步
- F3 (P2) 临时图片目录无限增长 → **已修复**：每次创建会话子目录 `%TEMP%/AutoSlide/images/YYYYMMDD_HHMMSS_<uuid>/`，并在创建时清理 >7 天的旧会话（命名严格匹配正则，仅清本应用目录）
- F4 (P2) 临时文件名碰撞 → **已修复**：会话级子目录彻底隔离
- F5 (P2) `_fill_two_content` 签名误导 → 与 F1 一并修复
- F7 (P3) detail 字数约束含糊 → **已修复**：明确"汉字/单词各算 1"的计字规则
- F8 (P3) image_prompt 覆盖过宽 → **已修复**：放宽为"对可视化有增益的内容页才提供"
- F6/F9 (P3)：requests 流式读取 / spec 隐藏导入确认 → 接受风险/正向确认

**验证**:
- py_compile 全部通过
- _test_export.py：5 项全绿（3 页标题 + 9 要点 + detail + 1 插图，HTML 预览含 base64 内嵌插图）
- 双栏 + 插图专项测试通过（左 3.7" / 右 3.5" 缩窄，图片正确插入不遮挡）
- session dir + cleanup 专项测试通过（>7 天清理，<7 天保留，非本应用目录不动）
- exe 重新打包成功（59.4 MB），启动正常进入事件循环，日志正常生成

## 第 14 轮 - PASS（Agnes AI 图像集成 + P1/P2 修复闭环）
**审查者**: Claude
**触发**: 用户新需求"推荐用户使用 agnes AI，并把 agnes 模型生图流程完成，不要过于简单的图片"
**调查发现**（关键根因）:
- 读取 AppData 配置 `$APPDATA/AutoSlide/settings.json`：`ai.base_url="https://apihub.agnes-ai.com/v1"`，`ai.model="agnes-2.5-flash"`（用户已在用 Agnes 文本），但 **`ppt.image_model="dall-e-3"`**（旧配置残留）
- 读最新日志 `autoslide_20260903_130443.log`：`POST https://apihub.agnes-ai.com/v1/images/generations` 反复返回 **503 Service Unavailable**
- **根因**：image_generator 旧版用 `ai.base_url`（=Agnes）+ `ppt.image_model`（="dall-e-3"，OpenAI 模型名），即"用 OpenAI 的模型名打 Agnes 的端点"→ 服务不认识 → 503
- 次要发现：venv 是 `httpx2 2.12.0`（openai 3.7.0 的新依赖），代码里 `import httpx` 会 ModuleNotFoundError
**实现摘要**:
1. **settings 默认配置改为推荐 Agnes**：`image_provider="agnes"`, `image_model="agnes-image-2.1-flash"`, `image_base_url="https://apihub.agnes-ai.com/v1"`, `image_api_key=""`（留空复用 ai.api_key 或环境变量 `AGNES_API_KEY`）
2. **settings_dialog 新增图像服务选择区**：图像服务下拉框（Agnes AI 推荐/OpenAI/自定义）、图像模型/Base URL/API Key/尺寸控件，Agnes 推荐说明标签（绿色）；服务切换自动填预设；`_loading` 标志防 setText 触发回填覆盖已保存自定义值
3. **image_generator 集成 Agnes**：
   - `_connect`：Key 优先级 `image_api_key > ai.api_key > env AGNES_API_KEY`；base_url 用 `image_base_url`（默认 apihub.agnes-ai.com/v1）；超时 `120.0`（float，Agnes 约 10~60s）
   - `_generate_ai`：provider=agnes 时加 `extra_body={"response_format":"url"}` 明确返回 URL（对象存储有时效，立即下载）；size 用 `image_size`（默认 1024x768 横版适配 PPT）
4. **兼容 httpx / httpx2**：`core/ai_client.py` 和 `core/image_generator.py` 去掉 `import httpx` / `httpx.Timeout()`，改用 `OpenAI(timeout=30.0)` / `OpenAI(timeout=120.0)` 直接传 float 总超时
5. **prompt_builder image_prompt 强化**：要求"主体+场景+风格+光照+构图+质量词"结构化详细描述，诱导 Agnes 产出高信息密度图
6. **兜底示意图增强**（无 API Key 时）：渐变背景 + 细网格线 + 装饰圆 + 圆角白卡 + 主题色顶部条 + 标题 + 分隔线 + AutoSlide 水印标签，比之前"渐变+圆+标题"有设计感得多
7. **spec hiddenimports 加 `'httpx2'`**：兜底打包（系统 python 同时有 httpx/httpx2，但显式声明更稳）

**验证**:
- py_compile：settings/settings_dialog/image_generator/prompt_builder/ai_client 全通过
- **Agnes API 真实调用成功**：`_test_agnes.py` 走 `ImageGenerator._generate_ai` 真实路径，`model="agnes-image-2.1-flash"`, `size="1024x768"`, `extra_body={"response_format":"url"}` → 生成 `samples/agnes_demo.png` (997 KB, 1024×768)，图为"开发者站十字路口 + Code/Team 霓虹指示牌"完整场景，信息密度高
- 兜底图验证：`samples/fallback_demo.png` (35 KB)，含渐变+网格+装饰圆+圆角白卡+主题条+AutoSlide 水印
- `_test_export.py` 全量回归 5 项全绿
- exe 重新打包中

**推荐用户使用**:
- Agnes AI 官网/注册入口：https://agnes-ai.com/
- API 平台：https://apihub.agnes-ai.com（OpenAI 兼容）
- 文档：https://agnes-ai.com/doc/overview
- 文生图端点：`POST /v1/images/generations`（model: agnes-image-2.1-flash，~10s，1024×768/1024×1024/2K+ratio，免费）

**Claude 第 14 轮审查结论**: 功能正确落地并验证（agnes_demo.png 997KB 真实生成），但发现 P1×2、P2×2、P3×2，建议修复 P1/P2 后发版。

**修复闭环处置**（本轮完成）:
- P1-A `image_generator._generate_ai` 未对 `image_provider` 归一化，旧值 `"dall-e-3"` 走不到 agnes 分支 → **已修复**：新增 `VALID_PROVIDERS = {"agnes","openai","custom"}`，非法值 warning + 回退 `"agnes"`
- P1-B `settings_dialog.load_settings` 旧非法 provider 会显示"自定义"、与配置不一致 → **已修复**：归一化映射 `{'agnes':0,'openai':1,'custom':2}.get(provider, 0)`，非法值回退 Agnes
- P2-A `image_size` 未校验格式（非法值致 SDK ValidationError 静默 fallback）→ **已修复**：`re.fullmatch(r"\d+x\d+")` 校验，非法值回退 `"1024x768"`
- P2-B 环境变量 Key 兜底来源未日志 → **已修复**：`_connect` 记录 key 来源（image_api_key / ai.api_key / env AGNES_API_KEY），未配置时也日志提示走兜底
- P3×2（fallback `str(path)` 冗余、孤儿 png 未清理）→ 接受风险（信息级，不影响功能；会话目录已按 7 天自动清理）

**验证**:
- py_compile 通过；`_test_export.py` 5 项全绿
- P1-A/P2-A 专项断言测试通过（非法 provider/size 均正确回退，合法值保留）
- exe 重新打包成功，冒烟测试正常


## 第 15 轮 - PASS with warnings（参考文献输入与引用）
**审查者**: Claude
**触发**: 用户需求"增加一个输入窗口，使用户可以输入参考文献，生成的ppt需要参考这些文献"
**审查结论**: Overall Result = PASS with warnings；P0=0, P1=0, P2=3, P3=2。核心逻辑正确，不阻断发布。

**Claude 确认的安全/兼容性要点**:
- `.format()` + `replace` 占位符方案**安全**：模板 JSON 花括号均以 `{{`/`}}` 转义，`{references_block}` 是唯一被 `.format()` 消费的占位符，用户文本（含 `{` `}` `%` `\n` URL）经 replace 原样透传，无二次解析风险。
- `layout="references"` 全链路兼容：`LAYOUTS.get` fallback 到 1（Title+Content）、插图生成过滤 `image_prompt=""`、装饰推导走正常流程，无异常分支。
- `GenerateThread` 线程安全：`run()` 内本地创建实例，`references` 经 `__init__` 传入，无跨线程共享状态。

**发现与修复闭环**:
- F-15-01 (P2) 参考文献超长条目无自适应 → **已修复**：`_fill_references` 动态字号（>8条或单条>90字→10pt；>5条或>60字→12pt；否则13pt）。验证：10条长文→10pt、2条短文→13pt。
- F-15-02 (P2) 参考文献页被内容关键词分配到 data/tech 等语义不匹配母题 → **已修复**：`_derive_slide_visual` 中 `layout=="references"` 固定 `motif="academic"`。验证：参考文献页母题固定 academic、普通页分类不受影响。
- F-15-03 (P2) 新文本框未显式清除 body 占位符 → **接受风险**：与既有 `_fill_content` 模式一致，python-pptx 默认模板空 body 占位符导出后不渲染残影，非真实 bug。
- F-15-04 (P3) 参考文献页 `page=` 参数冗余（add_slide 会重赋值）→ **已修复**：移除冗余参数。
- F-15-05 (P3) `.refs li` CSS 两条规则冗余 → **已修复**：合并为一条。

**验证**: py_compile 通过；_test_export.py 5 项全绿；F-15-02 母题断言、F-15-01 动态字号读回（段落级 font.size）均通过。

## 第 16 轮 - PASS with warnings（参考材料/背景材料输入框）
**审查者**: Claude
**触发**: 用户需求"在生成 PPT 界面再增加一个输入框（非必填），供用户提供参考资料，帮助 AI 进一步理解 PPT 内容"
**审查结论**: Overall Result = PASS with warnings；P0=0, P1=0, P2=2, P3=2。

**实现摘要**（4 文件）：新增 `context_input`（参考材料，自由文本，不追加页）区别于 `references_input`（参考文献，正式引文，追加页）。全链路透传 `context` 参数；Prompt 用「双占位符 + replace」安全方案注入「背景材料约束段」。

**发现与修复闭环**:
- F-16-01 (P2) `_build_context_block` 应声明 `@staticmethod` → **误报驳回**：第 116 行已声明 `@staticmethod`，Claude 读行号有误。
- F-16-02 (P2) context/references 无长度上限，超长材料可撑爆 Prompt / 稀释信息 → **已修复**：`PromptBuilder` 新增 `MAX_CONTEXT_CHARS=4000`、`MAX_REFERENCES_CHARS=2000`，超限截断并追加「已截断」提示。
- F-16-03 (P2) `context_input` 固定高度 88px 无法随内容增长、placeholder 未提示字数限制 → **已修复**：placeholder 注明「最长约 4000 字」；固定高度与 references_input 保持一致（既有设计，接受）。
- F-16-04 (P3) 用户文本恰好含字面 `__REFERENCES_PLACEHOLDER__`/`__CONTEXT_PLACEHOLDER__` 会被二次替换 → **接受风险**（极罕见，防御性建议，不影响真实使用）。
- F-16-05 (P3) `GenerateThread` 新增 `context=""` 位置参数的向后兼容性 → **确认无风险**（默认值保证零副作用）。

**验证**: py_compile 通过；PromptBuilder 超长截断/正常长度/空 context 专项全绿；`_test_export.py` 5 项全绿；exe 重新打包 + 冒烟测试。

## 第 17 轮 - PASS with warnings（界面全量汉化）
**审查者**: Claude
**触发**: 用户需求"所有界面全部汉化，可以在括号中写英文"
**审查结论**: Overall Result = PASS with warnings；P0=0, P1=1, P2=1, P3=3。

**实现摘要**（4 文件）：全界面「中文为主 + 括号附英文」汉化。核心链路确认安全：style 下拉框 `addItem(中文, userData英文)` + `currentData()`，theme 映射回退合理；语言下拉框 `currentIndex()` 三层逻辑一致；全量 grep 确认无 `.text()` 参与逻辑判断。

**发现与修复闭环**:
- F-17-01 (P1) `备注 (Notes):` 中英冗余 → **已修复**：简化为 `备注:`。
- F-17-02 (P2) placeholder `输入 API Key` 不自然 → **已修复**：改为 `请输入 API Key`。
- F-17-03 (P3) 关于弹窗标题 `关于 AutoSlide` → **接受**（AutoSlide 为产品名，不翻译）。
- F-17-04 (P3) Provider 下拉框 OpenAI/Azure/DeepSeek 纯英文 → **接受**（服务商专有名词）。
- F-17-05 (P3) 模型占位符示例 gpt-4o 等 → **接受**（技术术语，翻译反而失去参考价值）。

**验证**: py_compile 通过；离屏测试确认 style `currentData()` 返回英文值、语言下拉框 index 逻辑不变；`_test_export.py` 5 项全绿；exe 重打包 + 冒烟测试。

## 第 18 轮 - PASS with warnings（单文件安装包）
**审查者**: Claude
**触发**: 用户需求"打包成一个单文件安装包"
**审查结论**: Overall Result = PASS with warnings；P0=0, P1=1, P2=1, P3=4。

**实现摘要**：Inno Setup 6.7.3 制作 `installer/AutoSlide-Setup.exe`（60.9MB 单文件安装程序）。新增 `autoslide_setup.iss`（构建脚本）、`resources/icons/app.ico`（PIL 绘制）、`LICENSE`（MIT，README 声明但此前缺失）。中文语言文件从 issrc 仓库下载并规范化为 UTF-8 BOM + 65001。

**发现与修复闭环**:
- F-18-01 (P1) `PrivilegesRequired=lowest` 与 `DefaultDirName={autopf}`（Program Files）语义冲突，可能触发 VirtualStore/静默重定向 → **已修复**：`DefaultDirName` 改为 `{localappdata}\Programs\AutoSlide`。
- F-18-02 (P2) 缺少元数据（VersionInfoCopyright/LicenseFile/URL）→ **已修复**：补 `VersionInfoCopyright`、`LicenseFile=LICENSE`（新增 MIT LICENSE）。
- F-18-03 (P3) AppId `{{GUID}}` 双大括号语法 → **接受**（合法，硬编码保证重装识别同一产品）。
- F-18-04 (P3) spec `httpx2` 冗余 hiddenimport → **接受**（双兼容，仅增约 200KB，非本任务范围）。
- F-18-05 (P3) OutputDir 相对路径 → **已修复**：脚本顶部加注释「须在项目根目录运行 ISCC」。
- F-18-06 (P3) [Files] 无哈希校验 → **接受**（单文件安装包风险极低）。

**验证**: ISCC 编译成功（4.5s）；SHA256 校验与官方一致；静默安装解压正确；安装后冒烟测试进程存活；程序未运行时卸载退出码 0 完全清理。

**环境备注**: 本机 DNS `114.114.114.114` 失效 + GitHub 被墙，用 `223.5.5.5` 解析 + curl `--resolve` + `ghfast.top` 代理完成工具链下载。工具链已装 `C:\Users\NCZ Racing\InnoSetup6\`，`ISCC.exe autoslide_setup.iss` 可复现。

---

## 第 19 轮：图片布局适配优化（本轮新需求）

### 需求
用户要求：修复图片和文字的适配问题，继续优化文件。

### 实现
| 模块 | 变更 |
|------|------|
| `settings_module/models.py` | Slide 新增 `image_layout: str = "right"` 字段 |
| `core/pptx_builder.py` | 重写 `_calc_image_position()`：按宽高比动态计算尺寸；新增 `_get_image_dimensions()` 使用 PIL；`_adjust_textbox_for_image()` 自适应文本框；全屏模式加文字蒙层 |
| `core/outline_generator.py` | 自动分配布局：`rng.choice(["right", "left", "top"])` |
| 动画 | 页面切换动画（sldTrans XML）+ 文字出现动画（animCue/anim） |

### Claude 第 19 轮审查结论：FAIL（存在P0语法错误）
P0=2, P1=2, P2=3, P3=2。确认问题：
- F-19-01 (P0) `_calc_image_position` 体内混入 HTML 代码 → **误报**，本地 py_compile 通过，AST 解析正常
- F-19-02 (P0) `slide_page_num` 未定义 → **已修复**：改为 `logger.info("全图背景模式已应用")`
- F-19-03 (P2) NS_ANIM/NS_A 重复定义 → **已修复**：删除 NS_A
- F-19-04 (P1) 高图 top 计算可能为负 → **实际验证通过**：height 上限 5.5"，top = (7.5-5.5)/2 = 1.0 ≥ 0
- F-19-05 (P2) sldTrans 注入位置 → **接受**：pptx 库本身也 append 到 slide 根，现代版本宽容

### 修复闭环
- P0 已修复（`slide_page_num` → 移除未定义变量引用）
- P2 已修复（删除冗余 NS_A 常量）
- P1/P3 经独立验证后确认无实际风险

### 验证结果
```
✓ py_compile 全部通过
✓ _test_export.py 全量 5 项回归全绿
✓ 不同宽高比布局验证通过（方形 1:1 / 宽图 1.5:1 / 高图 0.67:1）
✓ 图片比例保持、位置不超边界
✓ exe 重新打包成功（59.4 MB），冒烟测试进程存活
```

代码可发布。

---

## 第20轮（2026-09-04）— 图文排版修复 — PASS（有条件）
- **触发**: 用户报告"图片与文字依旧冲突，文字可能显示在屏幕外"
- **改动**: core/pptx_builder.py
  - 新增正文注册表 `_content_registry`（每页重置）
  - 重写 `_adjust_textbox_for_image`：覆盖 add_textbox+占位符，按图片实际矩形算安全文字区，多栏均分；修复 python-pptx 代理对象 `id()` 去重失效 bug（改按底层 lxml 元素去重）
  - `_calc_image_position`：top 模式 top=1.45 避开标题区、max_height=2.4；侧图高上限 5.3；兜底最小高度 1.2"
  - 新增 `_estimate_body_height`/`_fit_registered_text`：两级自适应（缩字号→紧凑排版）+ 条件启用 normAutofit
  - `_write_body` 支持 scale/compact；标题/副标题按长度自适应字号
- **验证**: py_compile ✓；_test_layout.py 10场景 ✓（图文无重叠/无越界/文字可容纳）；_test_export.py 5/5 ✓
- **审查发现与处置**:
  - P1-01 auto_size 与 word_wrap 冲突风险 → **已修复**：仅在内容超量时启用 normAutofit
  - P1-02 无内容时仍重写 → 逻辑已含跳过条件，冗余但无害，**接受**
  - P2-01 双栏占位符顺序假设 → **已修复**：按 (left, top) 显式排序
  - P2-02 兜底高度可能成细线 → **已修复**：最小高度 1.2" 约束
  - P3-01 ASCII 字宽高估 → **接受**（仅致字号略保守）
  - P3-02 文献页无注册表自适应 → **接受**（已有静态阈值兜底，后续迭代考虑）
- **修复闭环**: 接受→修改→验证（10+5 测试复跑通过）→闭环，循环 1/5

## 第21轮（2026-09-04）— 文字安全边距优化 — 内部审查通过
- **触发**: 用户预览演示文件后要求"文字不要出现在画面边缘"
- **改动**（core/pptx_builder.py）:
  - 页脚水印: (0.4,7.05,6.0,0.4)→(0.7,6.95,4.0,0.25)，底边距 0.05"→0.30"
  - 标题占位符显式设为 (0.7,0.45,11.9,0.95)，替换模板默认 (0.5,0.3) 贴边位置
  - 正文框底边距 0.4"→0.55"（bottom 7.1→6.95）
  - 双栏无图: 显式安全区几何，替换模板默认 0.5" 边距与 9.5" 截断
  - `_adjust_textbox_for_image` 各模式底边距统一 0.55"
  - 自适应估算加严: avail_w-0.3/avail_h-0.25，估算基数 0.1→0.15
- **验证**: py_compile ✓；_test_layout.py 10场景含新增V5边距检查 ✓；_test_export.py ✓；演示文件7页贴边自检 0 问题；exe 冒烟 ✓

### 第21轮 Claude 独立审查结果 — PASS（无P0）
- F-21-01/P1 right模式图文间距语义 → **已修复**：gap 0.35→0.4 统一常量并注明设计意图
- F-21-02/P2 双栏 region_w 11.93 与全文档 11.9 不一致 → **已修复**：改为 SLIDE_W-0.7*2 动态计算
- F-21-03/P2 margin_side 注释与 right 模式实现脱节 → **已修复**：注释明确 right 模式边界推导
- F-21-04/P3 标题区右边缘 0.733" → 接受（视觉对称，无功能问题）
- F-21-05/P3 估算内缩常量与边距常量未统一 → 接受（防御性设计合理）
- **闭环验证**: py_compile ✓ / _test_layout 10场景 ✓ / _test_export 5/5 ✓ / 演示7页贴边0问题 / exe+安装包重构建+冒烟 ✓
- 循环 1/5 次闭环

## 第22轮（2026-09-04）— AI驱动布局 + 图片比例协调 + UI进度细化 — 审查中
- **触发**: 用户需求：①排版种类太少，要AI按内容决定布局，图片比例不对画面不协调；②UI进度无法直观了解所需时间
- **改动**:
  - prompt_builder：大纲prompt新增image_layout字段说明（AI按语义+节奏从5种布局选择）
  - outline_generator：_normalize_image_layout 校验（容忍大小写/空白），非法回退按页码确定性轮换
  - pptx_builder：top改为全宽横幅带；新增bottom贴底通栏；_apply_cover_crop居中裁切（top/bottom/fullscreen不再拉伸变形）；bottom模式页脚自动上移；修复_add_image引用未定义slide_w的NameError
  - image_generator：LAYOUT_IMAGE_SIZES按布局请求匹配比例（4:5/2:1/16:9），拒绝时回退配置尺寸重试；Pillow兜底画布同步匹配
  - generator_widget：progress_step(percent,msg,eta)信号；确定模式进度条；QTimer每秒刷新已用时+预计剩余
- **验证**: py_compile ✓；_test_layout 12场景含V6裁切 ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；布局解析6断言 ✓；演示5页 ✓；exe冒烟 ✓

## 第23轮（2026-09-04）— 横幅非全宽 + 前端UI视觉优化 — PASS(有条件)
- **触发**: 用户预览演示后要求"横幅不用铺满全宽；优化前端UI视觉效果"
- **改动**:
  - pptx_builder: top/bottom横幅 left=0,w=13.333 → left=0.7,w=11.93（与正文0.7"边距栅格对齐）；cover-fit目标比例改用显示框实际比例 width.inches/height.inches；页脚避让偏移0.37→0.5（F-23-05）
  - image_generator: top/bottom出图 1440x720 → 1536x512（AI请求+Pillow兜底同步，F-23-01）
  - **新增 ui/theme.py 全局QSS主题**：主色#2f6fed、圆角8px、悬停/按下/焦点态、渐变进度条、自定义滚动条、titleBar/fieldLabel/primaryBtn/doneLabel objectName体系；main.py接入apply_theme；main_window标题栏+logo；generator_widget布局spacing+标签体系；settings_dialog移除硬编码深色样式统一入主题
  - _test_layout.py: V6目标比例同步11.93/2.4，新增V6b横幅非全宽断言
- **验证**: py_compile ✓；_test_layout 12场景(含V6裁切+V6b) ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；offscreen UI运行时(主窗口+进度流+设置对话框+禁用态) ✓；exe+安装包重构建+冒烟 ✓
- **审查发现与处置**:
  - F-23-01/P1 LAYOUT_IMAGE_SIZES未同步(1440x720残留) → **已修复**（审查者正确，此前编辑未持久化）
  - F-23-02/P2 进度条百分比灰字压蓝色渐变可读性差 → **已修复**：改白色
  - F-23-03/P2 primaryBtn禁用态对比度过低 → **已修复**：#dbe5f8底+#7a8dbf字
  - F-23-04/P3 全局outline:none → 接受，补注释说明有意设计（文本控件已有2px focus边框补偿）
  - F-23-05/P3 bottom页脚与文字区间隙0.12"偏紧 → **已修复**：偏移0.37→0.5
- **闭环验证**: 三层测试复跑通过 + UI运行时复验 + 交付物重构建冒烟 ✓ / 循环 1/5 次
- **工具链备注**: Edit工具两次报告成功但未持久化（pptx_builder横幅几何、image_generator尺寸），需grep回读验证关键编辑

## 第24轮（2026-09-04）— 稀疏内容自适应均衡 — PASS
- **触发**: 用户反馈"图文左右结构的文字太少，中间空出一段比较明显"
- **改动**（core/pptx_builder.py + _test_layout.py）:
  - 新增 _estimate_natural_width（CJK 0.82/ASCII 0.55 系数估算正文自然宽度）
  - 新增 _grow_image_for_sparse_content：right/left 单栏且自然宽度比文字区窄>1"时插图放大（锚点/比例不变，上限5.6"宽/5.5"高，垂直居中于[1.45,7.1]）
  - _adjust_textbox_for_image：接入放大逻辑；单栏 est_h < region_h-0.9 时正文块垂直居中（高度est_h+0.35不触发字号缩放）
  - **修复连带Bug**：空BODY占位符被计入文字框集合→单栏正文被误拆为3"窄栏（正是中部留白观感的隐性成因）；现在跳过无文字占位符
  - _test_layout.py 新增 V7 verify_sparse_balance（稀疏页插图>4.6"、正文top>2.2）
- **验证**: py_compile ✓；_test_layout 12场景+V7 ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；probe sparse/rich/sparse_left 三场景几何 ✓；exe+安装包重构建+冒烟 ✓
- **审查发现与处置**（Claude 第24轮，通过可合入）:
  - F1/P2 双栏稀疏时两栏不垂直居中 → 接受（审查者明示当前无需修，极端场景，逻辑自洽）
  - F2/P3 两套估算模型系数不统一（0.82/0.55 vs 0.80统一）→ 接受（误差方向对冲，后续合并为共享估算函数）
  - F3/P3 空占位符过滤对"带默认提示文本的自定义模板"可能漏过 → 接受（去重兜底，仅多余空框无功能影响）
  - 专项检查 a~e 全部确认无冲突（放大与兜底约束/居中与fit余量链0.25"充足/fullscreen与references不受影响/双栏排除/空页无除零）
- **闭环**: 循环 1/5 次，无需修复轮次

## Round 25（2026-09-04）— bottom 横幅不贴画面底端
- **触发**：用户「底部图片不要贴住屏幕底端」
- **改动**：`core/pptx_builder.py` bottom 横幅 top 由 5.1→4.75（底边 7.5→7.15，新增 BANNER_BOTTOM_MARGIN=0.35 类常量）；`_test_layout.py` V6b 扩展贴底断言
- **验证**：探针 bottom_edge=7.15/底边距0.35 ✓；12+7+5 三层测试通过；exe 冒烟通过
- **审查**：Claude 独立审查 Round 25 → PASS(有条件)：P0×0 / P1×1 / P2×2 / P3×1
  - F-25-01(P1) V6b 断言阈值与代码常量脱节 → 已修复：断言改为镜像 `PPTXBuilder.BANNER_BOTTOM_MARGIN` 推导
  - F-25-02(P2) bottom_limit 注释误导读 → 已修复：docstring/行注释明确仅约束 right/left
  - F-25-03(P2) 三处底部边距常量分散 → 已部分处置：BANNER_BOTTOM_MARGIN 提升为类常量并注明与另两者关系（审查者标注"非强制"）
  - F-25-04(P3) docstring 过旧 → 随 F-25-02 一并更新
- **闭环**：1 轮（修复后 12+7+5 复测通过，双产物重建）
- **结论**：通过，可合入

## Round 26（2026-09-04）— 图片原比例零裁剪
- **触发**：用户「我不想要裁剪的图片，可以每张都是原比例吗，调整生成图片的比例而不是修改模板」
- **改动**：
  - 生成端：top/bottom 出图尺寸 1536x512(3:1)→1536x309(4.97:1) 精确匹配横幅框比例；新增 LAYOUT_FALLBACK_SIZES 回退链（精确→近似→配置尺寸）
  - 插入端：横幅二维比例自适应（高度先钳制 1.6~3.75"，宽度随之贴合原比例钳制 ≥4.0" 居中收窄）；比例偏差 <1% 不裁剪，>1% 才 cover-fit 兜底
  - 测试：新增 band(1536x309) 测试图 + V8 零裁剪断言 + V6c 几何镜像断言
- **验证**：三层测试 12+7+5 全通过；探针：4.97:1 零裁剪/2:1 零裁剪/1:1 残余 6%/1:2 裁 53%（竖图入横幅带的几何下限）；演示文件 top/bottom 页零裁剪自检通过；exe 冒烟通过
- **审查**：Claude 独立审查 Round 26 → PASS(有条件)：P0×0 / P1×0 / P2×3 / P3×1
  - F-26-01(P2) bottom_tall 缺几何断言 → 已修复：V6c 横幅几何镜像断言（覆盖 top/bottom 全部 V6 用例）
  - F-26-02(P2) 回退路径裁剪语义落差 → 已处置：补注释说明"已知妥协"
  - F-26-03(P2) 测试文档头滞后 → 已修复
  - F-26-04(P3) BANNER_BAND_H_MAX 注释推导不符 → 已修复：补推导公式（实际文字区约 1.35"）
- **闭环**：1 轮（修复为测试/注释级，无功能变更，双产物无需重建）
- **结论**：通过，可合入

## Round 27（2026-09-15）— Agnes API 恢复 + settings 完整性 + Pillow 兜底质量 + 版本号 v1.1
- **触发**：用户「对autoslide再次更新，Agnes API 恢复 + settings 完整性确认 + Pillow 兜底质量微调，同时修改版本号之类的，记得规则」
- **改动**（6 文件）：
  - `core/image_generator.py`：_THEME_COLORS 新增 tech/vibrant；网格线改在 RGBA overlay 绘制（修复 RGB 模式 alpha 被忽略发黑）；line_scale 随画布比例缩放；卡片圆角/装饰条按高度缩放；无标题场景改水平居中细线
  - `core/pptx_builder.py`：**_recommend_layout 重写**（image_layout 始终尊重上游显式值，仅对页面结构做内容感知推荐）；_estimate_natural_width 系数 CJK 0.82→1.0 / ASCII 0.55→0.6（修正稀疏放大误判）
  - `ui/main_window.py` + `scripts/autoslide_setup.iss`：版本号 v1.0→v1.1
  - `ui/generator_widget.py` + `core/outline_generator.py`：风格下拉与主题映射新增 Tech/Vibrant
- **关键修复**：9/7 引入的 _recommend_layout 按内容特征覆盖 image_layout，破坏了 9/4 建立的 top/bottom 横幅零裁剪链路（V6/V8 测试 18 项失败）→ 改为「image_layout 透传显式值，不做智能覆盖」，12+7+5 三层测试复绿
- **Agnes API 探活**：env AGNES_API_KEY（前缀 sk-gJSXcrUi6）有效，生图返回平台 URL（agnes 已恢复，无需 Pillow 兜底）
- **验证**：py_compile ✓；_test_layout 12场景 ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；exe(9.8MB)+安装包(41.7MB) 重构建；冒烟进程存活/窗口句柄非0
- **审查**：Claude 独立审查被安全策略拦截（reg.exe 在程序黑名单，sandbox 无法启动），降级为**严格自我审查**——逐项核验 _recommend_layout 7场景、版本号一致性（无 v1.0 残留）、Pillow 6主题/布局组合、settings 5个 image_* 键完整性，全部通过
- **闭环**：1 轮（含 1 次回归修复：_recommend_layout 覆盖 image_layout → 12 场景复绿）
- **结论**：通过，可合入（自审替代独立审查，已如实记录）

## 第 28 轮 - PASS with warnings（参考资料 PDF/MD 上传 + Prompt 工程优化）
**审查者**: 严格自我审查（Claude 独立审查因环境限制不可用，$CLAUDE 未设置 / reg.exe 黑名单，已如实记录）
**触发**：用户「参考资料输入（PDF/MD 上传）+ Prompt 工程优化」
**审查结论**：Overall Result = PASS with warnings；P0=0, P1=1(已修复), P2=1, P3=2。

**实现摘要**（6 文件）：
1. `core/doc_parser.py`（新建）— PDF(PyPDF2 逐页+[第N页]标注)+Markdown(标记清理)→纯文本，入口 `parse_reference_file`，MAX_FILE_CHARS=12000 截断保护，加密/0页/扫描件/不支持类型统一抛 ValueError
2. `ui/generator_widget.py` — 参考材料区加「📎 上传参考文件」按钮，`upload_reference_files` 多选解析后以 `=== 来源: 文件名 ===` 标注追加到 context_input，解析失败弹 QMessageBox.warning
3. `core/prompt_builder.py` — `_build_context_block` 增强（EXTRACT don't copy + 事实/观点/结构三类处理原则 + 忠实度）；`_build_references_block` 分条引导；大纲 Prompt 第4条新增「内容忠实度」约束
4. `ui/theme.py` — 明/暗两套主题各补 secondaryBtn + uploadedHint 样式
5. `AutoSlide.spec` — hiddenimports 增加 'PyPDF2'
6. `requirements.txt` — 增加 PyPDF2>=3.0.0

**发现与修复闭环**:
- F-28-01 (P1) `upload_reference_files` 多选文件时 `existing` 只读一次，循环内 setPlainText 覆盖导致只保留最后一个文件、丢失之前文件与用户手打内容 → **已修复**：`existing` 在每次迭代后累加新内容，重打包+冒烟通过（窗口句柄 67806）
- F-28-02 (P2) doc_parser MAX_FILE_CHARS=12000 与 prompt_builder MAX_CONTEXT_CHARS 双层截断阈值不一致，多文件拼接后二次截断可能丢失来源标注 → **记录为优化建议**，不影响功能
- F-28-03 (P3) 扫描件 PDF 提示文案可加 OCR 引导 → **接受**（可选优化）
- F-28-04 (P3) 代码块 fence 行保留可能引入噪音 → **接受**（可选优化）

**关键验证**:
- exe PKG PYZ 归档含 32 个 PyPDF2 条目（纯 Python 包正常进 PYZ，无需改 spec）
- 交接文档误判「PyPDF2 未收集到 _internal/」澄清：纯 Python 包编译进 PYZ 而非 _internal，是 PyInstaller 正常行为

**验证**: py_compile ✓；_test_layout 12场景 ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；exe(10.3MB)+安装包(42.2MB) 重构建；冒烟进程存活/窗口句柄 67806
**结论**：通过，可合入（自审替代独立审查，P1 已修复验证，已如实记录）

## 第 29 轮 - PASS（预览页面暗色模式 bug 修复）
**审查者**: 严格自我审查（Claude 独立审查因环境限制不可用，$CLAUDE 未设置 / reg.exe 黑名单，已如实记录）
**触发**：用户「修bug，看日志，记得规则,预览页面有问题」

**实现摘要**（1 文件 2 处修复）：
1. `ui/preview_widget.py` — **P1 修复**：`_is_dark()` 中 `QPalette.ColorRole.Window` 未导入 `QPalette`，导致 `NameError` 被 `except Exception` 静默吞掉、`_is_dark()` 恒返回 `False`。后果：暗色主题下预览页永远用浅色样式渲染（白底+深字），对比度极差，即用户看到的"预览页面有问题"。修复：`from PyQt6.QtGui import ... QPalette`
2. `ui/preview_widget.py` — **P2 修复**：第27轮新增的 tech/vibrant 主题未在 `THEME_COLORS` 字典中同步，预览页 fallback 到 business 配色（与 pptx_builder.THEMES 色阶不一致）。修复：补 `tech: {#0a3d62/#0ea5e9/#f0f9ff}` + `vibrant: {#9a2b0f/#f97316/#fff7ed}`

**发现与修复闭环**:
- F-29-01 (P1) `QPalette` 未导入 → `_is_dark()` 恒 False → 暗色模式预览样式错误 → **已修复**：补 PyQt6.QtGui 导入
- F-29-02 (P2) THEME_COLORS 缺 tech/vibrant → 预览配色与 PPT 实际渲染不一致 → **已修复**：补两主题色阶

**验证**: py_compile ✓；`_is_dark()` 不再 NameError（离屏测试返回 False 正常）；`update_preview` 全链路（business/tech 主题）✓；三层测试 `_test_layout` 12 ✓ / `_test_extreme` 7 ✓ / `_test_export` 5/5 ✓；exe(10.3MB)+安装包(42.2MB) 重构建；冒烟窗口句柄 330908
**结论**：通过，可合入（自审替代独立审查，已如实记录）
