# AI自动化PPT制作系统 - 项目规划书

**版本**: v1.0  
**日期**: 2026-09-02  
**状态**: 规划阶段

---

## 一、项目概述

### 1.1 项目名称
**AutoSlide** - AI驱动的全自动PPT生成工具

### 1.2 项目目标
开发一个Windows桌面应用程序，用户只需输入主题或上传资料，AI即可自动生成结构完整、视觉精美的演示文稿。

### 1.3 核心特性
- ✅ 自然语言描述生成PPT大纲和内容
- ✅ 支持多种AI后端（OpenAI / Anthropic / 本地模型）
- ✅ 可视化配置界面（模型选择、API Key、Base URL）
- ✅ 导出标准.pptx格式文件
- ✅ 支持主题模板切换
- ✅ 自动插入配图（可选）

---

## 二、技术架构

### 2.1 技术栈选型

| 层次 | 技术选型 | 理由 |
|------|---------|------|
| **UI框架** | PyQt6 | 跨平台、成熟稳定、打包方便 |
| **语言** | Python 3.10+ | AI生态完善、开发效率高 |
| **PPT生成** | python-pptx | 官方推荐、功能完整 |
| **AI接口** | OpenAI SDK + 兼容API | 支持多后端、灵活切换 |
| **打包工具** | PyInstaller | 单exe分发、无依赖 |
| **配置存储** | JSON + PyQt Settings | 轻量、可读 |

### 2.2 系统架构图

```
┌─────────────────────────────────────────────────────────┐
│                    AutoSlide 桌面应用                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  UI 层      │  │  业务逻辑层  │  │   配置管理层     │  │
│  │  (PyQt6)    │  │  (Generator) │  │  (Settings)     │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
│         │                │                   │           │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌────────▼────────┐  │
│  │  输入模块   │  │  AI 调用层  │  │  导出模块       │  │
│  │  - 主题输入 │  │  - 模型适配 │  │  - pptx导出     │  │
│  │  - 资料上传 │  │  - 流式响应 │  │  - 模板渲染     │  │
│  └─────────────┘  └──────┬──────┘  └─────────────────┘  │
│                          │                               │
│                  ┌───────▼────────────────────────┐      │
│                  │         AI 服务层               │      │
│                  │  - OpenAI API                  │      │
│                  │  - 兼容OpenAI协议的本地模型     │      │
│                  │  - 流式输出处理                │      │
│                  └────────────────────────────────┘      │
└─────────────────────────────────────────────────────────┘
```

---

## 三、功能模块设计

### 3.1 模块划分

```
autoslide/
├── main.py                    # 主入口
├── config/
│   ├── __init__.py
│   ├── settings.py           # 配置管理
│   └── models.py             # 数据模型定义
├── ui/
│   ├── __init__.py
│   ├── main_window.py        # 主窗口
│   ├── settings_dialog.py    # 设置对话框
│   ├── generator_widget.py   # 生成面板
│   └── preview_widget.py     # 预览面板
├── core/
│   ├── __init__.py
│   ├── prompt_builder.py     # Prompt构建
│   ├── ai_client.py          # AI客户端封装
│   ├── outline_generator.py  # 大纲生成
│   ├── content_generator.py  # 内容生成
│   └── pptx_builder.py       # PPTX构建器
├── templates/
│   ├── basic.pptx            # 基础模板
│   └── themes/               # 主题目录
│       ├── business.pptx
│       ├── academic.pptx
│       └── creative.pptx
├── utils/
│   ├── __init__.py
│   ├── file_helper.py        # 文件操作
│   ├── image_helper.py       # 图片处理
│   └── logger.py             # 日志工具
├── resources/
│   └── icons/                # 图标资源
└── requirements.txt
```

### 3.2 核心流程

```
用户输入主题/上传资料
        │
        ▼
   ┌─────────┐
   │ 输入验证 │
   └────┬────┘
        │
        ▼
   ┌─────────────┐
   │ 调用AI生成   │ ◄──┐ 支持多步骤：
   │ 内容大纲     │    │  1. 生成大纲
   └────┬────────┘    │  2. 生成每页内容
        │              │  3. 构建PPTX
        ▼              │
   ┌─────────────┐    │
   │ 用户确认/修改│───┘
   └────┬────────┘
        │
        ▼
   ┌─────────────┐
   │ 渲染PPTX    │
   └────┬────────┘
        │
        ▼
   ┌─────────────┐
   │ 导出文件    │
   └─────────────┘
```

---

## 四、用户配置界面设计

### 4.1 配置项列表

| 配置项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| **AI提供商** | 下拉选择 | OpenAI / Anthropic / 自定义 | OpenAI |
| **模型名称** | 文本输入 | 如 gpt-4 / claude-3-opus / 本地模型 | gpt-4o |
| **API Base URL** | 文本输入 | API端点地址 | https://api.openai.com/v1 |
| **API Key** | 密码输入 | 安全存储 | - |
| **最大Token数** | 数字输入 | 单次生成限制 | 4096 |
| **温度参数** | 滑块 | 创造力控制(0-1) | 0.7 |
| **输出语言** | 下拉选择 | 中文/英文 | 中文 |
| **默认主题模板** | 下拉选择 | 商务/学术/创意 | 商务 |

### 4.2 界面布局草图

```
┌─────────────────────────────────────────────────────┐
│  AutoSlide              [设置] [关于]   [■][□][-]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  📝 创建新PPT                                │   │
│  ├─────────────────────────────────────────────┤   │
│  │  主题/标题: [________________________________] │   │
│  │  页数范围: [10-15] 页                        │   │
│  │  风格: [商务 ▾]                              │   │
│  │  语言: [中文 ▾]                              │   │
│  │                                              │   │
│  │  📎 上传参考资料:                            │   │
│  │  [选择文件]  无文件选择                       │   │
│  │                                              │   │
│  │  [开始生成]                                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  📊 生成进度                                 │   │
│  │  [████████░░░░░░░░] 60%                     │   │
│  │  正在生成第 6/10 页内容...                   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  👁 预览                                     │   │
│  │                                             │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │  第1页  │ │  第2页  │ │  第3页  │  ...  │   │
│  │  │         │ │         │ │         │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘       │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [导出为PPTX] [复制内容] [清空]                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 五、Prompt工程策略

### 5.1 大纲生成Prompt模板

```
你是专业的演示文稿策划专家。请为以下主题生成PPT大纲：

【主题】{topic}
【页数】{page_count}
【语言】{language}
【风格】{style}

要求：
1. 生成 {page_count} 页PPT的完整大纲
2. 每页包含：标题、核心要点（3-5条）、备注说明
3. 结构清晰：封面 → 目录 → 内容页 → 总结 → 致谢
4. 内容专业、简洁、有逻辑性

以JSON格式输出：
{{
  "slides": [
    {{
      "page": 1,
      "title": "页面标题",
      "points": ["要点1", "要点2", "要点3"],
      "notes": "演讲备注",
      "layout": "title_content"
    }}
  ]
}}
```

### 5.2 内容扩写Prompt模板

```
请将以下PPT大纲内容扩展为完整的演示文稿内容：

【大纲】
{outline_json}

要求：
1. 每页内容保持简洁有力，适合演示场景
2. 要点控制在3-5条，每条不超过20字
3. 添加合适的演讲备注（每条30-50字）
4. 保持专业语气和连贯性

以JSON格式输出完整内容。
```

---

## 六、AI接口适配层设计

### 6.1 统一接口协议

```python
class AIClient:
    """AI客户端统一接口"""
    
    def chat(self, messages: list[dict], stream: bool = False):
        """发送聊天请求，支持流式/非流式"""
        pass
    
    def generate(self, prompt: str, model: str, **kwargs) -> str:
        """简化生成接口"""
        pass
```

### 6.2 支持的AI后端

| 后端 | 适配器类 | Base URL示例 |
|------|---------|-------------|
| OpenAI | OpenAIClient | https://api.openai.com/v1 |
| Anthropic | AnthropicClient | https://api.anthropic.com |
| 深度求索 | DeepSeekClient | https://api.deepseek.com |
| 智谱AI | ZhipuClient | https://open.bigmodel.cn/api/paas/v4 |
| 本地Ollama | OllamaClient | http://localhost:11434/api/generate |
| 自定义 | CustomClient | 用户指定 |

### 6.3 API Key安全存储

- 使用操作系统原生密钥存储（Windows Credential Manager）
- 配置文件加密存储
- 不记录日志、不传输到第三方

---

## 七、PPTX构建策略

### 7.1 布局模板系统

```python
LAYOUTS = {
    "title_slide": {  # 封面
        "layout_type": "title_only",
        "elements": [{"type": "title", "placeholder": "幻灯片标题"}]
    },
    "title_content": {  # 标题+内容
        "layout_type": "title_and_content",
        "elements": [
            {"type": "title", "placeholder": "幻灯片标题"},
            {"type": "content", "placeholder": "要点内容"}
        ]
    },
    "two_content": {  # 双栏内容
        "layout_type": "two_columns",
        "elements": [
            {"type": "title", "placeholder": "标题"},
            {"type": "content_left", "placeholder": "左侧内容"},
            {"type": "content_right", "placeholder": "右侧内容"}
        ]
    }
}
```

### 7.2 样式系统

- 基于python-pptx的样式定制
- 支持主题色配置
- 字体预设：微软雅黑/思源黑体
- 图片自动调整比例

---

## 八、打包与分发

### 8.1 PyInstaller配置

```python
# autoslide.spec
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('resources', 'resources'),
    ],
    hiddenimports=['pptx', 'openai', 'requests'],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name='AutoSlide',
    debug=False,
    strip=False,
    upx=True,
    console=False,  # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 8.2 打包命令

```bash
# 安装依赖
pip install -r requirements.txt

# 打包
pyinstaller --noconfirm autoslide.spec

# 输出目录
dist/AutoSlide.exe
```

---

## 九、开发里程碑

| 阶段 | 任务 | 预计工时 | 交付物 |
|------|------|---------|--------|
| **M1** | 基础框架搭建 | 2天 | 项目结构、依赖配置 |
| **M2** | 配置界面开发 | 2天 | 设置对话框、配置存储 |
| **M3** | AI接口适配 | 3天 | 多后端支持、流式输出 |
| **M4** | 大纲生成模块 | 2天 | Prompt工程、JSON解析 |
| **M5** | PPTX构建模块 | 3天 | 模板渲染、样式定制 |
| **M6** | 主界面集成 | 2天 | 完整UI流程 |
| **M7** | 测试优化 | 2天 | Bug修复、性能优化 |
| **M8** | 打包发布 | 1天 | 可执行文件 |

**总计**: 约17个工作日

---

## 十、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| API调用失败 | 高 | 重试机制、错误提示、离线模式 |
| 生成内容质量差 | 中 | 多次迭代优化Prompt、支持手动编辑 |
| 打包体积过大 | 低 | 按需裁剪依赖、使用upx压缩 |
| Windows安全警告 | 中 | 代码签名（可选）、用户提示 |
| 本地模型兼容性 | 中 | 优先支持OpenAI兼容接口 |

---

## 十一、后续扩展方向

- [ ] 支持LaTeX公式渲染
- [ ] AI自动配图（对接DALL-E/Stable Diffusion）
- [ ] Markdown导入生成PPT
- [ ] PDF/Word导入提取内容
- [ ] 云端协作编辑
- [ ] 更多主题模板
- [ ] 快捷键支持
- [ ] 国际化（多语言UI）

---

## 十二、下一步行动

1. ✅ 确认本规划方案
2. ⏳ 创建项目目录结构
3. ⏳ 初始化依赖配置
4. ⏳ 实现基础UI框架
5. ⏳ 开发配置管理模块
6. ⏳ 接入AI接口
7. ⏳ 完成PPT生成逻辑
8. ⏳ 打包测试

---

**请确认以上规划是否符合您的需求，我们将按照此方案开始正式开发。**
