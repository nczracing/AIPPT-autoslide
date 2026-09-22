# AutoSlide 第28轮 交接单（参考资料上传 + Prompt 工程优化）

## 任务目标
用户：「参考资料输入（PDF/MD 上传）+ Prompt 工程优化」，按开发轮次闭环完成。

## 已完成的代码改动（6 文件）
1. **core/doc_parser.py**（新建）— PDF(PyPDF2)+Markdown 解析为纯文本，入口 `parse_reference_file(path)`，带截断保护。PDF 按页加 `[第N页]` 标注；MD 清理标题/加粗/链接/图片/代码块/引用/列表标记。已实测通过
2. **ui/generator_widget.py** — 参考材料区加「📎 上传参考文件 (PDF / MD)」按钮 + `uploaded_label` 提示；`upload_reference_files()` 解析后以 `=== 来源: 文件名 ===` 标注填入 context_input（支持多文件追加）；导入 `from pathlib import Path` + `from core.doc_parser import parse_reference_file`
3. **core/prompt_builder.py** — ① `_build_context_block` 增强：EXTRACT don't copy + 三类材料（事实/观点/结构）处理原则 + 忠实度 ② `_build_references_block` 增强：分条引导 ③ 大纲 Prompt 第4条新增「内容忠实度」约束
4. **ui/theme.py** — 明/暗两套主题各补 `secondaryBtn` + `uploadedHint` 样式
5. **AutoSlide.spec** — hiddenimports 增加 `'PyPDF2'`
6. **requirements.txt** — 增加 `PyPDF2>=3.0.0`

## 已验证
- py_compile 全过（doc_parser / generator_widget / theme / prompt_builder）
- doc_parser：MD 清理（图片/引用/列表正确）+ PDF 提取（RegisterFlow.pdf 实测 3063 字符）
- prompt_builder：context_block/ref_block/full_prompt 断言全过
- UI 离屏：upload_btn + uploaded_label 存在，doc_parser 集成 OK
- 三层测试：`_test_layout` 12 ✓ / `_test_extreme` 7 ✓ / `_test_export` 5/5 ✓

## 卡住的问题（需接手处理）
**PyPDF2 未收集到 dist/AutoSlide/_internal/**，导致打包后的 exe 运行时 `import PyPDF2` 会失败（PDF 上传功能在 exe 模式下不可用，MD 不受影响——MD 是纯标准库解析）。

### 诊断
- `python -m PyInstaller AutoSlide.spec` 构建成功（Build complete），exe 10.3MB，但 `_internal/` 顶层 88 条目里**没有 PyPDF2**
- hiddenimports 已显式声明 `'PyPDF2'`，但 PyInstaller 没把它当二进制/数据收集
- 可能原因：PyPDF2 是**纯 Python 包**，PyInstaller 默认把纯 Python 模块**编译进 PYZ 归档**（而非放 _internal 目录），所以 `_internal/` 里没有它是**正常现象**，不代表没收集
- **真正验证方法**：打包后启动 exe，在 exe 里跑 `import PyPDF2` 看是否成功（或查 `build/AutoSlide/PYZ-00.pyz` 是否含 PyPDF2 条目）

### 待办
1. **确认 PyPDF2 是否已打进 PYZ**（关键，别误判为漏收集）：
   ```bash
   cd E:/study/projects/autoslide
   python -c "import PyInstaller.archive.readers as R; z=R.ZlibArchive('build/AutoSlide/PYZ-00.pyz','r'); names=[n for n in z.zipfile.namelist() if 'PyPDF2' in n]; print(names[:10])"
   ```
   若 PYZ 含 PyPDF2 → 打包其实 OK，exe 能用，无需改 spec；只需补一条测试断言
2. 若 PYZ 确实没有 PyPDF2 → 在 spec 用 `collect_all('PyPDF2')`（同 pptx 处理方式）：
   ```python
   tmp2 = collect_all('PyPDF2'); datas += tmp2[0]; binaries += tmp2[1]; hiddenimports += tmp2[2]
   ```
   重打包后再验证
3. 编译安装包：`"C:/Users/NCZ Racing/InnoSetup6/ISCC.exe" "E:/study/projects/autoslide/scripts/autoslide_setup.iss"` → installer/AutoSlide-Setup.exe
4. 同步根目录 exe：`python -c "import shutil; shutil.copy2('dist/AutoSlide/AutoSlide.exe','AutoSlide.exe')"`
5. 冒烟：启动 exe 7s 查窗口句柄非0
6. Claude 独立审查（写 `.harness-memory/review_r28_prompt.md`，调用时注意 reg.exe 黑名单可能拦截 → 拦截则降级自审并如实记录）
7. 归档 `docs/harness-memory/review-history.md` + `E:/study/.workbuddy/memory/2026-09-15.md`
8. present_files 交付演示 + 双产物

## 环境注意
- Bash 工具 shim 损坏（dirname/cat/tail/grep/ls/sleep/rm 等命令找不到），但 `python -c` 和 `python tests/*.py` 正常；管道类命令（`| tail`/`| grep`）失败 → 改用 `python` 读日志文件解析
- taskkill 参数：bash 里要 `taskkill /F /IM AutoSlide.exe`（单斜杠），`//F` 会报「无效参数」
- 杀残留进程用 Python：`subprocess.run(['taskkill','/F','/IM','AutoSlide.exe'])`（tasklist 有 GBK 编码问题，用 PowerShell `Get-Process AutoSlide | Stop-Process`）
- 第27轮版本号已升 v1.1，本轮保持 v1.1
- spec 文件名是 `AutoSlide.spec`（不是 autoslide.spec），dist 输出到 `dist/AutoSlide/`（onedir，含 _internal/）

## 代码位置索引
- 解析器：`core/doc_parser.py`（`parse_reference_file` / `_parse_pdf` / `_parse_markdown` / `_clean_markdown`）
- UI 上传：`ui/generator_widget.py`（`upload_reference_files` 方法 + `init_ui` 里的 upload_btn/uploaded_label）
- Prompt 优化：`core/prompt_builder.py`（`_build_context_block` / `_build_references_block` / OUTLINE_PROMPT_TEMPLATE 第4条）
- 样式：`ui/theme.py`（明暗两套各含 `QPushButton#secondaryBtn` + `QLabel#uploadedHint`）
