你是 AutoSlide 项目的独立代码审查者。请审查本轮改动（第28轮）。

## 本轮改动范围
用户需求：「参考资料输入（PDF/MD 上传）+ Prompt 工程优化」

改动文件（6个）：
1. `core/doc_parser.py`（新建）— PDF(PyPDF2)+Markdown 解析为纯文本，入口 `parse_reference_file(path)`，带 MAX_CHARS 截断保护。PDF 按页加 `[第N页]` 标注；MD 清理标题/加粗/斜体/链接/图片/代码块/引用/列表标记/水平线/HTML标签
2. `ui/generator_widget.py` — 参考材料区加「📎 上传参考文件 (PDF / MD)」按钮 + `uploaded_label` 提示；`upload_reference_files()` 解析后以 `=== 来源: 文件名 ===` 标注填入 context_input（支持多文件追加）；新增 `from pathlib import Path` + `from core.doc_parser import parse_reference_file`
3. `core/prompt_builder.py` — ① `_build_context_block` 增强：EXTRACT don't copy + 三类材料（事实/观点/结构）处理原则 + 忠实度 ② `_build_references_block` 增强：分条引导 ③ OUTLINE_PROMPT_TEMPLATE 第4条新增「内容忠实度」约束
4. `ui/theme.py` — 明/暗两套主题各补 `secondaryBtn` + `uploadedHint` 样式
5. `AutoSlide.spec` — hiddenimports 增加 `'PyPDF2'`
6. `requirements.txt` — 增加 `PyPDF2>=3.0.0`

## 审查重点
### 1. core/doc_parser.py（新建解析器 — 重点）
- `parse_reference_file(path)` 对 `.pdf` / `.md` / `.markdown` 后缀的路由是否正确（大小写不敏感）
- `_parse_pdf` 使用 PyPDF2 PdfReader：加密 PDF（is_encrypted）与 0 页 PDF（len(reader.pages)==0）是否抛 ValueError 而非裸异常
- PDF 按页 `[第N页]` 边界标注是否影响 PPT 内容（页码提示会被 AI 当作正文内容吗？建议考虑是否要去掉或改为 HTML 注释风格）
- `_clean_markdown` 的清理规则覆盖是否完整：
  - 整行图片 `![alt](url)` 是否被正确删除（而非留 `!alt` 残留）
  - 行内图片/链接 `[text](url)` 是否保留文字
  - 引用 `> text` 是否去掉 `>`
  - 代码块（fence + 内容）是否整体保留还是只保留 fence 之间的纯文本
  - 水平线 `---` / `***` 是否被删除
  - HTML 标签 `<br>` / `<p>` 是否被删除
- MAX_CHARS 截断阈值（8000）对超长 PDF 的截断是否合理（截断后是否保留原文前 8000 字符，还是按语义边界截）
- 文件不存在/无读取权限时的异常类型是否一致（ValueError/PermissionError）

### 2. ui/generator_widget.py（上传 UI）
- `upload_reference_files()` 用 QFileDialog.getOpenFileNames 多选，解析每个文件后用 `\n\n=== 来源: 文件名 ===\n` 前缀拼接到 context_input
- 多个文件追加时，context_input 已有内容（用户手打的参考文字）是否被覆盖而非追加？需要确认是 `setText(旧内容 + 新文件)` 还是 `setText(仅新文件)`
- 解析失败（不支持的文件/损坏的 PDF）是否弹 QMessageBox.warning 而不崩溃
- 文件名显示在 `uploaded_label`（QLabel#uploadedHint）是否过长被截断

### 3. core/prompt_builder.py（Prompt 工程）
- `_build_context_block` 的「三类材料」分类（facts/viewpoints/structure）是否会导致 AI 把参考材料内容误认为需要输出 references slide
- 大纲 Prompt 第4条「内容忠实度」约束与第3条「Be accurate and specific — cite real concepts」是否冲突（忠实度要求不能编造，但 specific 要求举例）
- `_build_references_block` 增强后是否会导致 AI 在正文里过度引用（引用密度过高，影响 PPT 可读性）

### 4. ui/theme.py（样式补充）
- 明/暗两套主题是否都补了 `secondaryBtn` 和 `uploadedHint`（若漏一套，明/暗切换时按钮/提示无样式）
- 新增的 QSS 选择器是否与现有选择器冲突（优先级）

### 5. AutoSlide.spec + requirements.txt（依赖声明）
- hiddenimports 加 `'PyPDF2'` 是否必要（纯 Python 包默认会被 PyInstaller 收集，但显式声明更稳）
- requirements.txt 的 `PyPDF2>=3.0.0` 与实际可用版本是否匹配（本机 PyPDF2 已可用，版本号确认）

## 打包产物验证
- PyInstaller 打包后 `dist/AutoSlide/AutoSlide.exe`（10.3MB）
- 已验证：exe PKG 归档 PYZ 中含 32 个 PyPDF2 条目（纯 Python 包正常进 PYZ，无需改 spec）
- 冒烟：进程存活 + 窗口句柄 721146 + 标题「AutoSlide - AI PPT 生成器」
- 三层测试：`_test_layout` 12 ✓ / `_test_extreme` 7 ✓ / `_test_export` 5/5 ✓

## 输出格式
按 CODE REVIEW REPORT 规范：
- Overall Result: PASS / CONDITIONAL / REJECT
- Risk Summary: P0/P1/P2/P3 各条数量
- Findings: 每条含 [file:line / severity / title / detail / recommendation / confidence]
- 末尾附「接受的优化建议」（P3 个人偏好）与「拒绝的修复」（含理由）

## 限制
- 禁止修改代码
- 禁止输出完整替代实现
- 禁止扩大需求
- 禁止风格重构
- 必须区分「真正风险 / 优化建议 / 个人偏好」
