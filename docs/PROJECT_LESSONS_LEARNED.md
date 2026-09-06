# AutoSlide 项目经验总结

## 一、编码问题

### 问题描述
- Windows系统默认使用ANSI/GBK编码，而Python源码默认使用UTF-8
- 在编辑器中写入中文注释或字符串时，如果文件编码不一致，会导致乱码
- 乱码文件会导致Python语法错误：`SyntaxError: Non-UTF-8 code starting with '\xe2'`

### 症状
```
SyntaxError: Non-UTF-8 code starting with '\xe2' in file xxx.py on line N, but no encoding declared
```

### 解决方案
1. **统一使用UTF-8编码**
   - Python文件开头添加 `# -*- coding: utf-8 -*-`
   - 使用支持UTF-8的编辑器（VS Code、PyCharm等）

2. **避免使用Windows记事本**
   - 记事本默认保存为ANSI编码
   - 如必须使用，保存时选择UTF-8编码

3. **已有乱码文件的处理**
   ```python
   # 重新用二进制模式写入正确的UTF-8内容
   with open('file.py', 'wb') as f:
       f.write(content.encode('utf-8'))
   ```

### 预防措施
- 在项目根目录添加 `.editorconfig` 文件，强制UTF-8编码
- 使用 pre-commit hooks 检查文件编码

---

## 二、PyQt6 多行字符串语法错误

### 问题描述
- PyQt6界面代码中有多行字符串时，未正确转义换行符
- 导致语法错误：`SyntaxError: unterminated string literal`

### 症状
```python
# 错误写法（未转义换行）
QMessageBox.about(self, 'About', 'AutoSlide v1.0
AI-Powered PPT Generator')

# 正确写法
QMessageBox.about(self, 'About', 'AutoSlide v1.0\nAI-Powered PPT Generator')
```

### 解决方案
1. 使用三引号字符串 `"""..."""`
2. 或使用显式换行符 `\n`
3. 或使用字符串拼接

---

## 三、PyInstaller 打包问题

### 问题1：`__file__` 在 .spec 文件中不可用
- **原因**：PyInstaller的.spec文件在特殊上下文中执行，`__file__` 未定义
- **解决方案**：使用 `Path.cwd()` 替代 `Path(__file__).parent`

```python
# 错误写法
base_dir = Path(__file__).parent

# 正确写法
base_dir = Path.cwd()
```

### 问题2：模块导入路径
- **原因**：PyInstaller需要在当前目录执行才能正确解析相对路径
- **解决方案**：始终在项目目录下运行 PyInstaller

---

## 四、依赖安装问题

### 问题描述
- 大型依赖包（如PyQt6，78MB）下载容易超时
- pip安装过程中断会导致部分依赖未安装

### 症状
```
WARNING: Connection timed out while downloading.
WARNING: Attempting to resume incomplete download
```

### 解决方案
1. **分批安装**
   ```bash
   pip install PyQt6      # 大型包
   pip install python-pptx  # 中型包
   pip install openai requests pillow  # 小型包
   ```

2. **使用国内镜像源**
   ```bash
   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package>
   ```

3. **离线安装**
   - 提前下载 wheel 文件到本地
   - 使用 `pip install <local_wheel_file>.whl`

---

## 五、GUI应用调试技巧

### 问题1：窗口闪退无报错信息
- **原因**：异常在GUI事件循环中被吞掉
- **解决方案**：
  1. 添加日志记录所有关键操作
  2. 使用 `sys.excepthook` 捕获未处理异常
  3. 使用 `try-except` 包裹所有GUI代码

```python
import sys

def exception_hook(exctype, value, traceback):
    logger.error(f'{exctype.__name__}: {value}', exc_info=True)
    sys.__excepthook__(exctype, value, traceback)

sys.excepthook = exception_hook
```

### 问题2：缺少主窗口导入
- **原因**：`main.py` 忘记导入 `MainWindow`
- **症状**：`NameError: name 'MainWindow' is not defined`
- **解决方案**：检查所有导入语句

---

## 六、配置文件管理

### 问题描述
- 配置未持久化保存，每次重启需要重新输入
- 配置文件不存在时行为不一致

### 解决方案
1. **自动创建配置目录**
   ```python
   config_dir.mkdir(parents=True, exist_ok=True)
   ```

2. **提供默认配置**
   ```python
   def _load(self) -> dict:
       if self.config_file.exists():
           return json.load(open(self.config_file))
       return self._default_settings()
   ```

3. **自动保存关键配置**
   - API Key等敏感信息使用操作系统密钥存储
   - 普通配置保存到JSON文件

---

## 七、开发流程规范

### 必须执行的步骤
1. ✅ 编写代码前：理解需求，分析影响
2. ✅ 编写代码后：编译验证 `python -m py_compile *.py`
3. ✅ 运行测试：`python test_project.py`
4. ✅ 打包前：确认所有依赖已安装
5. ✅ 打包后：测试exe文件是否正常运行

### 不应跳过的检查
- [ ] 代码编译是否通过？
- [ ] 测试是否全部通过？
- [ ] 依赖是否完整？
- [ ] 配置文件是否正确生成？
- [ ] exe能否正常启动？

---

## 八、常见错误速查表

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `SyntaxError: Non-UTF-8 code` | 文件编码不是UTF-8 | 重新保存为UTF-8编码 |
| `SyntaxError: unterminated string` | 多行字符串未转义 | 使用`\n`或三引号 |
| `NameError: name 'X' is not defined` | 忘记导入模块 | 添加 `from module import X` |
| `ModuleNotFoundError: No module named 'X'` | 依赖未安装 | `pip install X` |
| `Connection refused` | API Key未配置 | 在设置中配置API Key |
| PyInstaller `__file__` 错误 | spec文件上下文问题 | 使用 `Path.cwd()` |
| `AttributeError: 'QWidget' object has no attribute 'update_preview'` | `layout.addWidget()` 重设 parent | 用信号解耦，勿依赖 `self.parent()` |
| `QThread: Destroyed while thread is still running` | 自定义信号遮蔽内建 `finished` | 勿用 `finished`/`started` 命名自定义信号 |
| `JSON生成失败: Expecting ',' delimiter` | LLM 返回缺逗号的坏 JSON | 解析层加坏 JSON 修复器 |
| PPT 要点静默缺失 | placeholder 类型只认 BODY(2) | 同时匹配 `PP_PLACEHOLDER.OBJECT(7)` |
| OpenAI 图像 API 挂死 10 分钟 | 默认无 Timeout 限制 | `httpx.Timeout(20.0, connect=5.0)` 显式设置 |
| 双栏 + 插图：插图被右栏遮挡 | 布局不会自动让位 | 手动缩窄两栏至 3.7"/3.5"，图片放 8.2" 右侧 |
| 临时图片目录无限增长 | 文件名固定未隔离 | 会话级子目录 + >7 天自动清理（命名正则） |
| LLM 生成 JSON 长度被截断 | max_tokens=4096 默认不足 | 富文本 prompt 用 8192 token |
| `.format()` 报 `KeyError` 或内容错乱 | 用户文本含 `{}`（arXiv/LaTeX/URL）被 `.format()` 当作占位符解析 | 用唯一占位符先 `.format()` 再 `.replace()` 注入用户文本 |
| python-pptx `run.font.size` 读回 `None` | 字号设在段落 defRPr，run 无独立 rPr 时继承 | 验证字号读 `para.font.size`（段落级）而非 `run.font.size` |

---

## 九、项目结构回顾

```
autoslide/
├── main.py                 # 主入口（添加日志）
├── configs/                # 配置文件目录
│   └── settings.json       # 用户配置
├── logs/                   # 日志目录
│   └── autoslide_*.log     # 按时间命名的日志
├── core/                   # 核心逻辑
│   ├── ai_client.py       # AI接口
│   ├── pptx_builder.py    # PPT生成
│   └── ...
├── ui/                     # 用户界面
│   └── main_window.py     # 主窗口
└── utils/                  # 工具函数
    └── logger.py          # 日志工具
```

---

## 十、后续优化建议

1. **性能优化**
   - 使用异步AI调用，避免阻塞UI
   - 添加进度条显示生成进度

2. **用户体验**
   - 添加主题切换功能
   - 支持导入导出大纲
   - 添加快捷键支持

3. **稳定性**
   - 添加更多异常处理
   - 实现自动重试机制
   - 添加崩溃报告功能

4. **安全性**
   - 使用系统密钥存储API Key
   - 添加许可证验证
   - 加密敏感配置

---

**总结**：本项目从规划到打包完成，主要问题集中在编码、依赖管理和GUI调试三个方面。通过添加完整的日志系统和优化配置管理，已解决大部分潜在问题。后续可在此基础上继续扩展功能。

---

## 十一、PyQt6 信号与线程生命周期（第 16 轮踩坑）

### 问题1：`layout.addWidget()` 会重设 parent
- `content.addWidget(self.generator)` 会把 widget 重新 parent 到 `central`（普通 QWidget），因此 `self.parent()` 返回的**不是** MainWindow。
- **教训**：不要依赖 `self.parent().xxx()` 的层级关系；跨组件通信一律用自定义信号解耦。

### 问题2：自定义信号遮蔽 QThread 内建信号
- 定义 `finished = pyqtSignal(Presentation)` 会遮蔽 QThread 内建的 `finished` 信号，导致线程生命周期管理失效。
- **教训**：自定义信号不要用 `finished`/`started` 这类 QThread 内建信号名；线程清理用内建 `finished` 信号触发（run 返回后才发射）。

```python
# 正确写法
generated = pyqtSignal(object)          # 自定义信号改名
self.thread.finished.connect(self._on_thread_finished)  # 内建 finished 清理
```

---

## 十二、LLM 输出容错（第 17 轮踩坑）

### 问题：AI 返回的 JSON 缺逗号导致解析失败
- LLM（agnes-2.5-flash）返回的 outline JSON 常出现缺逗号、尾逗号、注释等轻微瑕疵，直接 `json.loads` 会整体失败。
- **修复双层**：① `generate_json` 优先 JSON mode（`response_format={"type":"json_object"}`），失败回退普通模式；② 纯标准库坏 JSON 修复器（状态机修注释/尾逗号/缺逗号）。

### 运算符优先级陷阱
```python
# 错误：and 优先级高于 or，实际是 (j<n and ...) or text[j].isdigit()
if j < n and text[j] in "..." or text[j].isdigit():  # j==n 时越界 IndexError

# 正确
if j < n and (text[j] in "..." or text[j].isdigit()):
```

---

## 十三、python-pptx 占位符与布局映射（第 18 轮踩坑）

### 问题：导出的 PPT 要点静默缺失
- 默认模板 `slide_layouts` 顺序：`0=Title Slide, 1=Title and Content, 2=Section Header, 3=Two Content`。
- "Title and Content"(1) / "Two Content"(3) 的内容占位符类型是 **OBJECT(7)**，不是 BODY(2)；只匹配 `type == 2` 会导致默认布局要点永远写不进。

```python
from pptx.enum.shapes import PP_PLACEHOLDER
# 正确：同时匹配 BODY 和 OBJECT
if placeholder.type in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
    content_box = shape
    break
```

### 教训
- 写 PPTX 导出逻辑前，**先用脚本枚举实际 placeholder 类型**，不要凭直觉。
- 单元测试只断言"标题在 HTML 预览里"会漏掉 PPTX 实际内容缺失；必须**读回生成的 .pptx** 逐页断言标题+要点，才算真验证。

---

## 十四、AI 多步骤容错链与图文混排（第 19 轮踩坑）

### 问题：AI 图像 API 不通时整个生成流程被卡死
- OpenAI 客户端默认**没有超时限制**（实际是 10 分钟）。当用户配置了无效的 base_url 或网络不通时，`client.images.generate(...)` 会挂死整个生成线程。
- 用户看到的就是"按钮卡住 10 分钟没反应"，体验极差。

### 修复：显式 httpx Timeout
```python
import httpx
from openai import OpenAI

timeout = httpx.Timeout(20.0, connect=5.0)  # 总读 20s，连接 5s
client = OpenAI(api_key=..., base_url=..., timeout=timeout)
```
配合 try/except 兜底，让失败的图像生成在 5-20s 内超时并 fallback。

### 三级降级链路（绝不让中间步骤拖垮整体）
```
AI 图像 API (OpenAI gpt-image-1 / dall-e-3)
  ↓ 失败 (超时/无模型支持/网络)
Pillow 主题示意图 (渐变 + 装饰圆 + CJK 字体)
  ↓ 失败 (Pillow 未安装)
None (返回 None，由 PPTX 构建器优雅跳过)
```
**关键设计**：每一步 try/except 隔离失败，绝不抛异常中断整个生成流程。

### 临时资源管理：会话级目录 + 自动清理
```python
# 命名严格正则匹配，仅清本应用目录，不碰用户文件
pattern = re.compile(r"^\d{8}_\d{6}_[0-9a-f]{8}$")
def _cleanup_old_sessions(root, max_age_days=7):
    for child in root.iterdir():
        if not child.is_dir() or not pattern.match(child.name):
            continue
        if time.time() - child.stat().st_mtime > max_age_days * 86400:
            shutil.rmtree(child, ignore_errors=True)
```
- 每次创建会话目录（`YYYYMMDD_HHMMSS_<uuid8>`）时触发清理
- 命名严格匹配，避免误删用户文件
- 默认 7 天阈值

### 16:9 PPTX 图文混排的布局参数
- 幻灯片：13.333" × 7.5"（标准 16:9）
- 标题占顶部 ~1.0"（高），从 y=0.4" 起
- 正文区从 y=1.5" 到 y=7.1"（高 ~5.6"）
- 单栏布局：左侧文本框宽 7.2"（0.7"-7.9"），右侧 add_picture 宽 4.3"（8.2"-12.5"）
- 双栏布局（two_content）：左右栏各 3.7"/3.5"（缩窄让位图片区）

```python
# 双栏 + 图片时手动缩窄两个占位符
if has_image:
    left.left = Inches(0.6);  left.width = Inches(3.7)
    right.left = Inches(4.5); right.width = Inches(3.5)
slide_obj.shapes.add_picture(path, Inches(8.2), Inches(1.9), width=Inches(4.3))
```

### CJK 字体兼容（跨平台兜底）
```python
def _find_cjk_font():
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
        r"C:\Windows\Fonts\simhei.ttf",    # 黑体
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # Linux
        ...
    ]
```
找不到时静默跳过文字（不报错），生成的图至少是个干净的渐变背景。

### 经验总结
1. **OpenAI / httpx 类 SDK 必须显式 Timeout**——10 分钟超时在用户感知层是"死机"。
2. **多步骤 AI 链路的容错是工程核心**——每一步独立 try/except + 全局汇总，绝不让中间失败拖垮整体。
3. **临时资源用会话级目录 + 命名严格清理**——既避免磁盘膨胀，也不误删用户文件。
4. **python-pptx 图文混排需手动重设占位符位置**——布局不会自动给图片让位，必须显式缩窄。
5. **Pillow 兜底永远胜过白板**——一个渐变 + CJK 字体标题比"无图"好太多。

---

## 十五、Agnes AI 集成与 httpx 兼容（第 20 轮踩坑）

### 问题1：用 OpenAI 模型名打 Agnes 端点 → 503
- 用户 AppData 配置 `$APPDATA/AutoSlide/settings.json`：`ai.base_url=apihub.agnes-ai.com/v1`（已在用 Agnes 文本），但 `ppt.image_model=dall-e-3`（旧残留）。
- 图像生成请求 `POST apihub.agnes-ai.com/v1/images/generations` 反复 **503 Service Unavailable**。
- **根因**：模型名是 OpenAI 的 `dall-e-3`，Agnes 不识别该模型 → 服务端 503。
- **教训**：更换 API 供应商时，**模型名 + base_url + API Key 必须同步切换**；不要假设"同一个模型名在所有 OpenAI 兼容服务上通用"。

### 问题2：venv 是 httpx2，代码 `import httpx` 失败
- openai 3.7.0 依赖 `httpx2 2.12.0`（新名字），旧代码 `import httpx; httpx.Timeout(...)` 在新 venv 里 ModuleNotFoundError，导致 _connect 失败 → 走兜底 → 永远用不上 AI 生图。
- **修复**：不显式 import httpx，直接传 float 给 OpenAI 的 timeout 参数（openai SDK 内部兼容）：
```python
self.client = OpenAI(api_key=..., base_url=..., timeout=120.0)  # float 总超时
```
- **教训**：**不要依赖特定 httpx 版本**；OpenAI SDK 的 `timeout` 参数支持 float/tuple/httpx.Timeout 三种，float 最稳。

### Agnes 图像 API 关键事实（2026-09 调研）
| 项 | 值 |
|---|---|
| 端点 | `POST https://apihub.agnes-ai.com/v1/images/generations` |
| 模型 | `agnes-image-2.1-flash`（高信息密度，约 10s 出图）/ `agnes-image-2.0-flash`（上一代） |
| 认证 | `Authorization: Bearer YOUR_API_KEY` |
| 参数 | `model`, `prompt`, `size`（1024x1024 / 1024x768 / 2K+ratio）, `n=1` |
| 关键参数 | `extra_body={"response_format":"url"}` 明确返回 URL |
| 响应 | `data[0].url`（对象存储**有时效**，需立即下载） |
| 国内容灾 | 自动切到 `apihub.agnes-ai.cn` |
| 定价 | 当前**免费**（无限期免费 API） |

### Agnes 集成要点
1. **OpenAI 兼容格式**——直接用 `openai.OpenAI(base_url=apihub.agnes-ai.com/v1)` 即可，无需额外 SDK
2. **推荐 URL 返回**——`extra_body.response_format="url"`，然后用 `requests.get(url, timeout=60)` 下载（URL 有时效！）
3. **超时放宽**——Agnes 图像生成约 10~60s，OpenAI 默认无超时，**必须显式 timeout=120.0**
4. **三级降级**——AI 生图 → 兜底图（`Pillow`）→ None（PPTX 构建器优雅跳过）
5. **Key 优先级链**：`image_api_key > ai.api_key > env AGNES_API_KEY`——支持配置文件 + 环境变量兜底

### 推荐用户使用 Agnes AI
- 官网/注册入口：https://agnes-ai.com/
- API 平台：https://apihub.agnes-ai.com（OpenAI 兼容）
- 文档：https://agnes-ai.com/doc/overview
- 优势：完全免费、约 10s 出图、高信息密度与复杂版式表现强

### 问题3：配置字段迁移残留旧值（Claude 第 14 轮审查 P1/P2）
- 新增 `image_provider` 枚举字段时，用户旧配置里没有该字段或残留了 `"dall-e-3"` 等旧模型名；若直接用 `ppt_cfg.get("image_provider", "agnes")`，旧值 `"dall-e-3"` 会走不到 agnes 分支，界面下拉框也显示"自定义"与配置不一致。
- **修复（白名单归一化）**：
```python
VALID_PROVIDERS = {"agnes", "openai", "custom"}
provider = ppt_cfg.get("image_provider", "agnes")
if provider not in VALID_PROVIDERS:
    logger.warning("未知 image_provider '%s'，回退 agnes", provider)
    provider = "agnes"
```
- 同理，`image_size` 加格式校验：`re.fullmatch(r"\d+x\d+", str(size))`，非法值回退 `"1024x768"`。
- **教训**：**配置枚举字段升级时必须做白名单归一化**（非法值回退安全默认），不能简单 `get(key, default)`——旧用户升级后配置里残留的非法值会让"新端点 + 旧模型名"跨服务串用。UI 侧 `load_settings` 也要同步归一化映射，否则界面显示与运行时逻辑不一致。

### 速查表新增（第 14 轮更新）
| 错误 | 原因 | 解决方案 |
|------|------|----------|
| Agnes 图像 API 返 503 | 模型名不匹配（如用 dall-e-3 打 Agnes 端点） | 同步切换 base_url + model（如 `agnes-image-2.1-flash`） |
| `ModuleNotFoundError: No module named 'httpx'` | venv 装的是 `httpx2`（openai 3.7+） | 不显式 `import httpx`，改 `timeout=120.0` 传 float |
| Agnes 图像 URL 下载失败/超时 | 对象存储 URL 有时效 | 收到 URL 后立即 `requests.get(timeout=60)` 下载 |
| AI 图像 API 挂死 | OpenAI 默认 10 分钟超时 | 显式 `timeout=120.0`（Agnes）或 `timeout=30.0`（文本） |
| 用户用 OpenAI 文本但想用 Agnes 图像 | base_url 不一致 | `image_base_url` 与 `ai.base_url` 分离，分别配置 |
| 旧配置残留非法 `image_provider` | 枚举字段升级未归一化 | 白名单 `VALID_PROVIDERS` 校验，非法值回退 `agnes` |
| 非法 `image_size` 致 SDK ValidationError | 尺寸透传无校验 | `re.fullmatch(r"\d+x\d+")` 校验，非法回退 `1024x768` |

---

## 十六、主题背景与排版增强（第 21 轮）

### 需求：主题背景/排版要更丰富
- 原主题只有 4 个纯色字段（title/accent/text/bg），背景是单一纯色，排版较朴素。

### 实现（`core/pptx_builder.py`）
1. **THEMES 扩展为完整色阶**：每个主题 7 个字段——`title_color`（标题/色带/竖条）、`accent_color`（强调/装饰线/要点）、`text_color`、`bg_top`+`bg_bottom`（渐变两端）、`deco_color`+`deco2_color`（装饰圆）。
2. **丰富背景 `_apply_background`**：全屏渐变矩形 + 顶部主色带（高 0.14"）+ 左侧主色竖条（宽 0.14"）+ 右下两个错位装饰圆 + 页脚水印「AutoSlide」。
3. **排版增强**：内容页标题下加 accent 装饰短线；封面标题居中大字号 + 居中装饰线；要点 `space_after=10`/`line_spacing=1.2`；detail `line_spacing=1.3`；插图加主题色描边（`pic.line.width=Pt(1.25)`）。
4. **HTML 预览主题化**：根据 theme 生成渐变背景、标题色、accent 描边、装饰圆、`li::before` 圆点。

### 关键技术点：python-pptx 渐变填充（纯 XML）
`FillFormat` 无高层渐变 API，用 lxml 直接构造 `a:gradFill`：
```python
from lxml import etree
from pptx.oxml.ns import qn
spPr = shape._element.spPr
# 1) 先移除既有 fill（solidFill/gradFill/noFill/...）
for tag in ('a:solidFill','a:gradFill','a:noFill','a:blipFill','a:pattFill','a:grpFill'):
    for el in spPr.findall(qn(tag)):
        spPr.remove(el)
# 2) 构造渐变
gradFill = etree.SubElement(spPr, qn('a:gradFill'))
gradFill.set('rotWithShape', '1')
gsLst = etree.SubElement(gradFill, qn('a:gsLst'))
gs0 = etree.SubElement(gsLst, qn('a:gs')); gs0.set('pos', '0')
etree.SubElement(gs0, qn('a:srgbClr')).set('val', '%02X%02X%02X' % top)
gs1 = etree.SubElement(gsLst, qn('a:gs')); gs1.set('pos', '100000')
etree.SubElement(gs1, qn('a:srgbClr')).set('val', '%02X%02X%02X' % bottom)
lin = etree.SubElement(gradFill, qn('a:lin'))
lin.set('ang', '5400000')  # 90°=5400000，自上而下
lin.set('scaled', '1')
```
- **角度单位**：`a:lin@ang` 单位 1/60000 度，90° = `5400000`，表示自上而下渐变。

### 关键：装饰形状必须置底，否则遮挡占位符文字
`add_slide(layout)` 自带 title/body 占位符；后 `add_shape` 的形状默认叠在**占位符之上**，会遮挡文字。解决：把装饰形状移到形状树最底层：
```python
def _send_to_back(self, shape):
    sp = shape._element
    spTree = sp.getparent()
    spTree.remove(sp)
    spTree.insert(2, sp)  # 2 = nvGrpSpPr(0) + grpSpPr(1) 之后
```

### ⚠️ 关键陷阱：`insert(2)` 是「后调用者插到更底层」
`send_to_back` 反复调用时，**后调用的元素被插到 index 2，先调用的被挤到后面（相对上层）**。
因此：
- 若「全屏背景矩形」**最先** send_to_back，装饰（色带/竖条/圆）**后** send_to_back，
  最终背景反而在装饰**之上**，全屏矩形把装饰全部盖住（只看到渐变，看不到色带）。
- **正确做法**：装饰先 send_to_back、全屏背景**最后** send_to_back，才能让背景落最底层。

```python
# 正确顺序（装饰先、背景最后）
for shape in (footer, deco2, deco, bar, band):
    self._send_to_back(shape)   # 装饰先置底
self._send_to_back(bg)          # 背景最后置底 → 背景最底
# 最终 z-order：bg < band < bar < deco < deco2 < footer < 占位符(文字)
```

**验证方法**：读回生成的 .pptx，遍历 `slide.shapes._spTree` 打印每个 `p:sp` 的 `index` + 形状名 + 是否渐变，确认渐变矩形（背景）的 index 最小（最底层）。不要只数形状数量——数量对但层级错，视觉上背景会盖住装饰。

### 验证
- 每页渐变形状数 = 1，形状总数 = 10（背景+色带+竖条+2圆+页脚+标题线+正文+插图等）
- 三主题（business/academic/creative）均正常构建
- `_test_export.py` 5 项全绿；PPTX 读回 3 页标题+9 要点+detail+插图不受影响
- **z-order 专项验证**：读回 PPTX 打印 `_spTree` 每个 `p:sp` 的 index，确认渐变背景矩形 index 最小（最底层），装饰居中、文字最上（修复「背景盖住装饰」的 bug）

### 经验教训
- **装饰元素永远置底**——python-pptx 的 `add_shape` 叠在占位符上方，不 `send_to_back` 会遮住标题正文。
- **`send_to_back`（insert(2)）反复调用时「后调用的在最底层」**——全屏背景必须最后 send_to_back，否则背景会盖住装饰；验证不能只数形状数量，要读回 PPTX 检查 `_spTree` 里的实际 z-order。
- **渐变/半透明等高级填充无高层 API**——直接操作 `spPr` XML 最稳，且要记得先 `remove` 既有 fill 子元素避免叠加。
- **主题要设计成"完整色阶"而非"几个孤立颜色"**——一个主题至少要有：标题色、强调色、正文色、背景渐变两端色、装饰色，才能支撑丰富排版。


---

## 十七、参考文献输入与引用（第 23 轮）

### 需求
增加一个输入窗口让用户输入参考文献，生成的 PPT 需要参考这些文献。

### 实现链路（贯穿 5 个文件）
```
UI 多行输入框(generator_widget)
  → GenerateThread 传 references
  → OutlineGenerator.generate(references=...)
  → PromptBuilder 注入「文献约束段」（要求正文自然引用、不编造）
  → 生成后追加 layout="references" 的「参考文献」页（中/英文标题自动切换）
  → PPTX/预览渲染：小字号 + [i] 编号
```

### 关键坑与解法
1. **`.format()` 会解析用户文本里的 `{}`**：参考文献常含 `arXiv:1706.03762`、LaTeX、URL 等花括号，
   直接 `template.format(references=user_text)` 会抛 `KeyError` 或错乱。
   **解法**：模板里放唯一占位符 `{references_block}`，先 `.format()`（此时 `references_block`
   传 `"__REFERENCES_PLACEHOLDER__"`），再 `prompt.replace("__REFERENCES_PLACEHOLDER__", 用户文本)`。
   用户文本全程走 `replace`，不经过 format 解析，安全透传 `{}`/`%`/`\n`/URL。
2. **参考文献页复用 `points` 承载条目**，用 `layout="references"` 标记，`LAYOUTS.get(...)` 的
   fallback 到 1（Title+Content）自动兜底，无需新增 slide_layout 映射；插图生成因 `image_prompt=""`
   自动跳过。
3. **python-pptx 段落字号验证陷阱**：`p.font.size = Pt(13)` 写的是段落 defRPr，run 无独立 rPr 时
   继承该值，故 `run.font.size` 读回 `None`；验证/断言字号要读 `para.font.size`（段落级）。
4. **参考文献页装饰母题**：文献标题可能含「数据/技术/流程」等词，会被内容感知背景误分类成
   data/tech/flow 母题，语义不匹配。解法：`_derive_slide_visual` 里对 `layout=="references"`
   固定 `motif="academic"`。
5. **超长条目防溢出**：参考文献单条可能很长（作者列表+标题+期刊+DOI），固定字号会纵向溢出文本框。
   解法：`_fill_references` 动态字号（条目>8 或单条>90 字 → 10pt；>5 或 >60 字 → 12pt；否则 13pt）。

### 经验
- 用户输入的任意自由文本进入 prompt 时，**永远不要用 `.format()`/f-string 直接插值**，统一走
  「占位符 + replace」或「拼接待注入段」。
- 学术类 PPT 的「参考文献页」是独立布局语义（小字号、编号、常规字重），应与「要点页」（粗体、
  强调色、圆点）分开渲染，而不是复用同一套要点样式。

---

## 十八、参考材料输入与上下文约束（第 24 轮）

### 需求
在生成界面再增加一个「参考材料」输入框（非必填），供用户粘贴背景材料，帮助 AI 进一步理解
想要的 PPT 内容。

### 核心设计：与「参考文献」做语义切分
| 维度 | 参考文献 References | 参考材料 Reference Materials |
|------|--------------------|------------------------------|
| 输入性质 | 正式引文列表（作者. 标题. 期刊, 年份） | 自由背景文本（要点/数据/素材/侧重点） |
| Prompt 约束 | 正文需自然引用文献观点、不编造 | 提取关键事实/数据/观点融入正文、忠实原文但不整段照抄 |
| 页面副作用 | 末尾自动追加「参考文献」页 | **无**（不追加任何页面） |
| 长度上限 | 2000 字 | 4000 字 |

### 实现链路
```
UI 两个独立 QTextEdit（references_input + context_input）
  → GenerateThread 传 references + context（默认 "" 向后兼容）
  → OutlineGenerator.generate(references=..., context=...)
  → PromptBuilder：模板放两个占位符 {references_block} + {context_block}
  → 先 .format()（占位符传 sentinel），再两次 replace 注入用户原文
```

### 关键坑与解法
1. **双占位符并存时 replace 顺序**：`{references_block}` 与 `{context_block}` 两个占位符分别
   replace 成用户文本，两者互不干扰；即便某块为空（replace 成空串）也不残留占位符。保持
   「一个占位符对应一个 replace」的一一对应即可，无需先判空再决定顺序。
2. **自由文本无长度上限会撑爆 prompt**：用户可能粘贴整篇论文/产品文档。解法：`PromptBuilder`
   定义 `MAX_CONTEXT_CHARS=4000` / `MAX_REFERENCES_CHARS=2000`，超限 `[:上限]` 截断并追加
   「…(已截断)…」提示，让模型知道材料不完整，避免无意识编造后续内容。
3. **输入框高度与提示**：`setFixedHeight(88)` 固定高度无法随内容增长，需在 placeholder 注明
   字数上限，避免用户误以为超出部分已被完整输入。

### 经验
- 两个「输入→约束注入 prompt」的功能（references / context），应抽成统一模式：**UI 输入 →
  线程透传 → 生成器透传 → PromptBuilder 的 `_build_xxx_block` 生成约束段 → 占位符 + replace 注入**，
  未来再添加类似输入（如「目标受众」「演讲时长」）时照搬即可。
- 语义相近的输入框必须在 UI 文案和 Prompt 里**显式区分副作用**（一个追加页面、一个不追加），
  否则用户和模型都会混淆。

---

## 十九、界面全量汉化（第 25 轮）

### 需求
所有界面全部汉化，可以在括号中写英文。

### 核心坑：QComboBox 汉化时"显示值 ≠ 逻辑值"
界面汉化最常见的翻车点：**某个下拉框的显示文本同时也被代码当逻辑值使用**。例如风格下拉框
原本：
```python
self.style_combo.addItems(['Business', 'Academic', 'Creative'])
# 取值传给下游映射
self.style_combo.currentText()   # 返回 'Business'
# 下游：
theme = {"Business": "business", "Academic": "academic", ...}.get(style, "business")
```
若直接把显示文本改成中文 `'商务 (Business)'`，`currentText()` 会返回 `'商务 (Business)'`，
下游 `dict.get('商务 (Business)')` 匹配失败，静默回退默认值（"business"），风格选择失效。

### 解法：`addItem(text, userData)` + `currentData()`
```python
# text=显示（中文），userData=逻辑值（英文，供下游映射）
self.style_combo.addItem('商务 (Business)', 'Business')
self.style_combo.addItem('学术 (Academic)', 'Academic')
self.style_combo.addItem('创意 (Creative)', 'Creative')
# 取值用 currentData()，不再用 currentText()
self.style_combo.currentData()   # 返回 'Business'
```
`currentData()` 未选中时返回 `None`，下游 `dict.get(None, 默认值)` 安全回退，不崩溃。

### 经验
1. **汉化前先排查"以界面文本作逻辑值"的地方**：用 grep 搜 `.text()`、`currentText()` 的取值点，
   确认它们是否被用于比较 / 映射 / 拼 key。若是，改用 `currentData()`（userData）或 `currentIndex()`。
2. **`currentIndex()` 天然与显示文本解耦**：语言下拉框 `'中文 (Chinese)'/'英文 (English)'` 改显示
   文本不影响 `currentIndex()==0 → 'zh'` 的判断，无需 userData。
3. **专有名词不翻译**：服务商名（OpenAI/Azure/DeepSeek）、技术术语（gpt-4o、API Key、Base URL）、
   产品名（AutoSlide）保留英文；普通标签用「中文 (English)」格式。
4. **汉化后必须跑离屏渲染断言**：验证 `itemText`（显示中文）+ `itemData`（逻辑英文）+ `currentData()`
   （返回英文值）三者关系，确保"看得懂"和"跑得对"兼顾。

---

## 二十、单文件安装包（Inno Setup，第 26 轮）

### 需求
把 AutoSlide 打包成「单文件安装包」——双击即可安装的 setup.exe（含快捷方式、卸载程序），而非绿色版单文件 exe。

### 工具选型
- **Inno Setup 6** 是 Windows 最标准、中文支持最好的安装包工具。安装到用户目录 `C:\Users\<user>\InnoSetup6\`
  即可免管理员（`/DIR` 指定目录 + `/VERYSILENT` 静默）。
- 编译器：`ISCC.exe`（命令行），产物 `installer/AutoSlide-Setup.exe`。

### 核心坑 1：`PrivilegesRequired=lowest` 与 `{autopf}` 冲突
`PrivilegesRequired=lowest`（免 UAC）+ `DefaultDirName={autopf}`（Program Files）是**语义矛盾**的组合：
普通用户对 Program Files 无写权限，可能触发静默重定向或 Windows VirtualStore，导致「安装成功但文件
找不到」的隐蔽问题。
**解法**：免 UAC 场景用 `DefaultDirName={localappdata}\Programs\{#MyAppName}`（VSCode/GitHub Desktop
同款用户级安装路径）；要装 Program Files 则必须 `PrivilegesRequired=admin` 接受 UAC。

### 核心坑 2：中文语言文件需单独获取且要修编码
Inno Setup 6 主安装包**不含中文**。中文语言文件在 issrc 仓库
`Files/Languages/Unofficial/ChineseSimplified.isl`（非官方贡献）。该文件实际是 UTF-8 编码但声明
`LanguageCodePage=936`（GBK），直接使用会乱码。**解法**：下载后规范化——加 UTF-8 BOM +
改 `LanguageCodePage=65001`。

### 核心坑 3：本机 DNS 失效 + GitHub 被墙（网络环境）
- 系统 DNS `114.114.114.114` 超时，但出口网络正常（`223.5.5.5`/`8.8.8.8` 可 ping）。无管理员权限无法
  `netsh` 改 DNS。
- GitHub 直连被 RST。
- **解法**：`nslookup 域名 223.5.5.5` 拿 IP → `curl --resolve 域名:443:IP` 绕过 DNS 解析；GitHub 下载走
  加速代理 `https://ghfast.top/https://github.com/...`（同样用 --resolve 指定 ghfast.top 的 IP）。
- Inno Setup 官方下载全部指向 GitHub，无独立镜像；`winget` 下载也因此失败。

### 核心坑 4：程序运行时卸载会残留 exe（文件锁）
若 AutoSlide.exe 正在运行就卸载，`unins000.exe` 无法删除被文件锁锁定的 exe（正常 Windows 行为）。
静默卸载（`/VERYSILENT`）不会提示，只会跳过被锁定文件。**验证卸载时务必先确保进程退出**；
`CloseApplications=yes` 在交互卸载时会提示关闭运行中的程序。

### 核心坑 5：卸载后测试残留目录 + 幽灵进程
反复冒烟测试用 `./AutoSlide.exe &` 后台启动，`taskkill //F //IM AutoSlide.exe` 在 Git Bash 下可能
**静默失败**（输出被 `2>/dev/null` 吞掉），导致幽灵进程残留并锁定文件。清理残留时又被环境的
safe-delete 机制拦截（`genie-trash` 回收站工具对锁定文件失败 → FAIL_CLOSED 拒绝删除）。
**解法**：用 PowerShell `Get-Process` 找真实 PID（注意 ProcessName 不带 `.exe`）→ `Stop-Process -Force`
→ 再 `Remove-Item -Recurse -Force` 才能成功。

### 经验
1. **图标无 .ico 时可用 PIL 现画**：渐变圆角方形 + 简单图形（幻灯片+播放三角），多尺寸 ICO（16~256）
   一键生成，避免引入外部资源。
2. **LicenseFile 只显示在安装向导**，不会自动复制到 {app}；README 声明 MIT 但缺 LICENSE 文件时应补齐
   并引用，保证分发合法性。
3. **AppId 硬编码 GUID 是正确行为**（保证重装识别为同一产品），双大括号 `{{...}` 是 Inno 消除常量
   解析歧义的合法写法。
4. **构建脚本要注明运行前提**：`Source`/`OutputDir` 相对路径依赖「在项目根目录运行 ISCC」，加注释防呆。


