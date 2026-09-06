# AutoSlide - AI自动化PPT制作系统

![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt-6.5+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

## ✨ 功能特性

- 🎯 自然语言生成PPT大纲和内容
- 🔧 多AI后端支持（OpenAI/Anthropic/本地模型）
- ⚙️ 可视化配置界面
- 📄 导出标准.pptx格式
- 🎨 多种主题模板（学术/商务/创意）
- 🌗 深色/浅色主题切换
- 🖼️ 智能配图（AI生成 + Pillow 兜底）
- ✨ OOXML 合法动画（Transition + 入场动画）
- 🔒 API Key安全存储
- 📐 智能排版（图片防触底、横幅自适应）

## 📦 构建与安装

### 打包产物（三种形态）

| 形态 | 路径 | 大小 | 说明 |
|------|------|------|------|
| onedir | `dist/AutoSlide/AutoSlide.exe` | ~131MB | 开发调试用，启动快 |
| 安装包 | `installer/AutoSlide-Setup.exe` | ~42MB | InnoSetup 绿色安装 |
| 单文件 | `dist/AutoSlide_oneline.exe` | ~57MB | 便携分发（不推荐生产使用） |

### 构建命令

```bash
# 1. 构建 onedir（推荐用于开发）
python -m PyInstaller AutoSlide.spec

# 2. 构建安装包（需要 Inno Setup 6）
cd scripts
ISCC.exe autoslide_setup.iss
```

> ⚠️ **铁律**：生产部署必须用 onedir 模式 + InnoSetup 安装包，禁用 `--onefile`（57MB 单文件每次启动需解压到临时目录，易卡死/被杀软拦截）。

### InnoSetup 要求

- 路径：`C:\Users\NCZ Racing\InnoSetup6\ISCC.exe`
- 必须递归打包 `dist\{#MyAppName}\*`（含 `_internal/` 依赖）
- 用户级安装：`DefaultDirName={localappdata}\Programs\{#MyAppName}`

## 📖 使用指南

1. **配置AI接口**：点击"设置"按钮，填入API Key和Base URL
   - 当前默认 provider: `openai`
   - Agnes API 需要有效 Key（历史遗留：Agnes Key 401 失效时走 Pillow 兜底）
2. **输入主题**：在主页输入PPT主题或上传参考资料
3. **开始生成**：选择页数范围和风格，点击"开始生成"
4. **预览修改**：幻灯片式卡片浏览（每页独立展示，含要点列表 + 缩略图）
5. **导出PPT**：点击"导出为PPTX"保存文件

## 🏗️ 项目结构

```
autoslide/
├── main.py                 # 主入口
├── requirements.txt        # Python 依赖（PyQt6, python-pptx, Pillow, lxml, openai）
├── configs/                # 运行时配置（settings.json，不含敏感Key）
├── core/                   # 核心逻辑
│   ├── ai_client.py        # AI接口封装（支持多provider）
│   ├── content_generator.py
│   ├── outline_generator.py
│   ├── pptx_builder.py     # PPT生成（含动画/排版/主题）
│   └── image_generator.py  # 图像生成（AI + Pillow兜底）
├── ui/                     # 用户界面（PyQt6）
│   ├── main_window.py      # 主窗口
│   ├── preview_widget.py   # 幻灯片卡片预览
│   ├── theme.py            # 深/浅色主题切换
│   └── generator_widget.py
├── settings_module/        # 数据模型与配置持久化
├── utils/                  # 工具函数（日志/文件/图像）
├── resources/              # 资源文件（图标等）
├── samples/                # 生成示例与演示
│   ├── presentations/      # .pptx 成品 + .html 预览
│   ├── screenshots/        # UI 截图
│   └── layout-tests/       # 布局测试图（横幅/比例验证）
├── scripts/                # 构建脚本
│   ├── autoslide_setup.iss # InnoSetup 配置
│   ├── install.py          # 依赖安装辅助
│   └── AutoSlide.spec      # PyInstaller spec
├── tests/                  # 回归测试
│   ├── test_project.py     # 综合测试
│   ├── _test_layout.py     # 布局验证（12场景）
│   ├── _test_export.py     # 导出验证（5项）
│   ├── _verify_anim.py     # 动画XML合法性验证
│   └── _test_agnes.py      # Agnes API 测试
├── docs/                   # 项目文档
│   ├── PROJECT_PLAN.md     # 规划书
│   ├── DEPENDENCIES.md     # 依赖说明
│   ├── REVIEW_EXECUTION_REPORT.md
│   ├── REVIEW_PACKAGE.md
│   ├── PROJECT_LESSONS_LEARNED.md
│   ├── ARCHIVE/            # 归档文件
│   └── harness-memory/     # 双审查机制评审记录（r12~r27）
├── installer/              # 安装包产物（AutoSlide-Setup.exe）
├── dist/                   # PyInstaller 打包产物
├── logs/                   # 运行日志（自动清理）
└── AutoSlide*.spec         # PyInstaller spec 文件
```

## ⚙️ API Key 配置

### 配置文件位置

```
configs/settings.json
```

### 当前支持 provider

| Provider | base_url | model |
|----------|----------|-------|
| OpenAI | `https://api.openai.com/v1` | gpt-4o |
| Agnes（内部） | `https://agnes.internal/v1` | agnes-2.5-flash |
| 本地模型 | 自定义 | 自定义 |

### 注意事项

- ⚠️ **Agnes API Key 401 失效**：当前配置为测试 Key，AI 出图功能走 Pillow 兜底
- 建议更新为有效 Key，或直接使用 OpenAI provider
- Key 加密存储在本地，不提交 Git

## 🎨 动画系统

### Transition（页面切换）

支持 6 种合法 OOXML transition：
- fade / push / wipe / dissolve / uncover / cover

### 入场动画（Entrance Animations）

支持 3 种 preset：
- fade（淡入）
- fly（飞入）
- zoom（缩放）

> 所有动画均通过 `<p:timing>` 树结构生成，符合 OOXML 规范，PowerPoint 可直接播放。

## 📐 智能排版

- **图片防触底**：top/bottom 区域自动计算可用高度，保证文字区 ≥ 1.8"
- **横幅自适应**：`BANNER_BAND_H_MAX = 3.6"` 防止横幅遮挡内容
- **间距保护**：图片与文字间距 ≥ 0.25"

## 🧪 测试覆盖

```bash
# 运行全套回归测试
python tests/_test_layout.py    # 布局验证（12场景）
python tests/_test_export.py    # 导出验证（5项）
python tests/_verify_anim.py    # 动画XML合法性验证
```

## 📝 开发计划

详见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)

## 📄 License

MIT License

---

**维护者**: NCZ Racing  
**最后更新**: 2026-09-06
