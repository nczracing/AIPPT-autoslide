# CODE REVIEW REPORT — 第28轮

> 审查说明：Claude 独立审查因环境限制（`$CLAUDE` 未设置 / reg.exe 在程序黑名单，sandbox 无法启动 claude.exe）不可用，按协议降级为**严格自我审查**（独立视角逐项核验本轮 6 文件改动）。

## Overall Result: PASS

## Risk Summary
- **P0**: 0
- **P1**: 1（已修复）
- **P2**: 1
- **P3**: 2

## Findings

### [P1] upload_reference_files 多选文件时数据丢失
- **file**: `ui/generator_widget.py:296-310`
- **severity**: P1
- **detail**: `existing = self.context_input.toPlainText().strip()` 在循环外只读取一次，循环内 `setPlainText(existing + 新文件)` 未把新追加内容累回 `existing`。当一次选多个文件（或连点两次上传）时，**每个文件都基于同一份旧 `existing` 覆盖写入，最终只保留最后一个文件，之前的文件与用户手打的参考文字全部丢失**。
- **recommendation**: 让 `existing` 在每次迭代后累加新内容：`existing = (existing + '\n\n' if existing else '') + f'=== 来源: {name} ===\n{text}'` 再 `setPlainText(existing)`。**已修复**。
- **confidence**: 高

### [P2] MAX_FILE_CHARS=12000 与 prompt_builder.MAX_CONTEXT_CHARS 双层截断
- **file**: `core/doc_parser.py:21`
- **severity**: P2
- **detail**: `MAX_FILE_CHARS=12000` 在 doc_parser 层截断，prompt_builder 的 `MAX_CONTEXT_CHARS` 会二次截断。两层阈值接近但非同一值，极端场景（用户上传多个 12000 字符文件）拼接后可能远超 prompt_builder 上限，导致二次截断时丢失部分文件来源标注。
- **recommendation**: 可考虑 doc_parser 截断阈值与 prompt_builder 对齐，或在 UI 上传时给用户提示"材料过长将截断"。**未修复**（属优化建议，不影响功能，PPT 生成仍可用）。
- **confidence**: 中

### [P3] PDF 扫描件无文本时抛 ValueError 的提示文案
- **file**: `core/doc_parser.py:83`
- **severity**: P3
- **detail**: 扫描件 PDF（无可提取文本）抛 `ValueError("PDF 无可提取文本（可能是扫描件）")`，文案准确但 UI 层可加"建议用 OCR 后上传"的引导。
- **recommendation**: P3 个人偏好，可选优化。
- **confidence**: 低

### [P3] 代码块 fence 行 `cleaned.append(line.strip('\`').strip())` 保留了 fence 行文字
- **file**: `core/doc_parser.py:116`
- **severity**: P3
- **detail**: 代码块 ``` 围栏行被保留为纯文本（去掉反引号后若围栏带语言标识如 ```python 则保留 "python"），可能引入少量噪音。
- **recommendation**: P3 个人偏好。
- **confidence**: 低

## 已核验（PASS）
| 项 | 结果 |
|----|------|
| doc_parser 后缀路由（pdf/md/markdown） | ✓ |
| 加密/0页 PDF 抛 ValueError | ✓ |
| `[第N页]` 页边界标注 | ✓ |
| MD 清理：整行图片/链接/加粗/引用/水平线/HTML/代码块 | ✓ |
| generator_widget 上传 + 保留旧 context（修复 P1 后） | ✓ |
| QMessageBox.warning 解析失败提示 | ✓ |
| theme.py 明暗两套 secondaryBtn(6处) + uploadedHint(2处) | ✓ |
| spec hiddenimports + requirements 含 PyPDF2 | ✓ |
| exe PKG PYZ 归档含 32 个 PyPDF2 条目 | ✓ |

## 修复闭环
- P1（多选覆盖 bug）：接受 → 修改 → 重打包 → 冒烟通过（窗口句柄 67806）
- P2/P3：记录为优化建议，人工接受风险，不影响本轮功能可用性

## 结论
通过。P1 已修复并验证，P2/P3 为优化建议不阻塞。双产物（dist exe 10.3MB + installer 42.2MB）已重新编译并冒烟通过。
