# AutoSlide 第28轮 交接单（AI 参考资料上传 + Prompt 工程优化）

## 任务目标
参考资料输入（PDF/MD 上传）+ Prompt 工程优化，并完成开发轮次闭环。

## 已完成的代码改动（5 个文件）
1. **core/doc_parser.py**（新建）— PDF(PyPDF2) + Markdown 解析为纯文本，统一入口 `parse_reference_file(path)`，带截断保护。py_compile ✓，PDF/MD 解析实测通过
2. **ui/generator_widget.py** — 参考材料区加「📎 上传参考文件 (PDF / MD)」按钮 + 已加载文件提示标签，`upload_reference_files()` 解析后带 `=== 来源: 文件名 ===` 标注填入 context_input；导入 `from pathlib import Path` + `from core.doc_parser import parse_reference_file`
3. **core/prompt_builder.py** — ① `_build_context_block` 增加结构化引导（EXTRACT don't copy + 三类材料处理 + 忠实度）② `_build_references_block` 增加引用格式规范 ③ 大纲 Prompt 第4条增加"内容忠实度"约束
4. **ui/theme.py** — 明/暗两套主题各补 `secondaryBtn` + `uploadedHint` 样式
5. **AutoSlide.spec** + **requirements.txt** — 增加 `PyPDF2`（hiddenimports + 依赖声明）

## 已验证
- py_compile 全部通过（doc_parser / generator_widget / theme / prompt_builder）
- doc_parser：MD 清理 + PDF 提取（RegisterFlow.pdf 实测）通过
- prompt_builder：上下文块/参考文献块/完整 prompt 断言全过
- UI 离屏测试：upload_btn + uploaded_label 存在，doc_parser 集成 OK
- 三层测试：`_test_layout` 12场景 ✓ / `_test_extreme` 7 ✓ / `_test_export` 5/5 ✓

## 未完成（卡在打包，需接手）
- **PyInstaller 打包中断**：上一轮有 AutoSlide.exe 进程占用 `dist/AutoSlide`，导致 COLLECT 阶段目录被锁定/重建失败。`dist/AutoSlide/` 与 `_internal/` 当前为空
- **待办清单**：
  1. 杀掉残留 AutoSlide.exe 进程：`taskkill //F //IM AutoSlide.exe`（或 PowerShell `Get-Process AutoSlide | Stop-Process -Force`）
  2. 重打包：`python -m PyInstaller AutoSlide.spec --clean --noconfirm --distpath dist --workpath build`
  3. 验证 `dist/AutoSlide/AutoSlide.exe` 生成 + `dist/AutoSlide/_internal/PyPDF2` 已收集 + `dist/AutoSlide/_internal/core/doc_parser.py` 存在
  4. 编译安装包：`"C:/Users/NCZ Racing/InnoSetup6/ISCC.exe" "E:/study/projects/autoslide/scripts/autoslide_setup.iss"` → `installer/AutoSlide-Setup.exe`
  5. 同步根目录快捷 exe：`python -c "import shutil; shutil.copy2('dist/AutoSlide/AutoSlide.exe','AutoSlide.exe')"`
  6. 冒烟：启动 exe 7s 查窗口句柄非0
  7. Claude 独立审查（`.harness-memory/review_r28_prompt.md`，注意 reg.exe 黑名单可能拦截）
  8. 归档 `docs/harness-memory/review-history.md` + `E:/study/.workbuddy/memory/2026-09-15.md`
  9. present_files 交付演示 + 双产物

## 环境注意
- Bash 工具 shim 脚本损坏（dirname/cat/tail/grep/ls 等命令找不到），`python -c` 与 `python tests/*.py` 可正常跑，但管道类命令（| tail、grep）会失败——改用 `python` 直接读日志文件解析
- PyPDF2 已可用（环境预装），spec hiddenimports 已显式声明，打包后需确认 _internal/PyPDF2 存在
- 第27轮已把版本号升到 v1.1，本轮保持 v1.1 不变（除非用户要求升 v1.2）
