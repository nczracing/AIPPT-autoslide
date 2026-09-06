# 第 17 轮审查请求：界面全量汉化

## 原始需求（用户）
> 所有界面全部汉化，可以在括号中写英文

## 实现摘要
对 4 个 UI 文件做「中文为主、括号内附英文」的界面汉化：

1. **ui/generator_widget.py**：主题/页数/风格/语言标签、参考文献/参考材料标签、按钮（生成/导出/预览）、进度消息（正在生成内容/插图/完成）、全部 QMessageBox 提示汉化。**关键改动**：风格下拉框由 `addItems(['Business','Academic','Creative'])` + `currentText()` 改为 `addItem('商务 (Business)', 'Business')` + `currentData()`。
2. **ui/main_window.py**：窗口标题、顶栏标题、Settings/About 按钮、状态栏、关于弹窗汉化。
3. **ui/preview_widget.py**：预览标签、提示文字、HTML 内 `Page X`→`第 X 页`、`Notes:`→`备注 (Notes):`。
4. **ui/settings_dialog.py**：Base URL→接口地址、API Key→API 密钥、Temperature→温度、Custom→自定义、图像 Base URL→图像接口地址、图像 API Key→图像 API 密钥、语言下拉框中文显示。

## 修改文件
- ui/generator_widget.py
- ui/main_window.py
- ui/preview_widget.py
- ui/settings_dialog.py

## 关键 Diff（核心逻辑）
```python
# generator_widget.py —— 风格下拉框：中文显示 + userData 承载英文值
self.style_combo = QComboBox()
self.style_combo.addItem('商务 (Business)', 'Business')
self.style_combo.addItem('学术 (Academic)', 'Academic')
self.style_combo.addItem('创意 (Creative)', 'Creative')

# 语言下拉框：显示中文，逻辑仍基于 currentIndex
self.lang_combo.addItems(['中文 (Chinese)', '英文 (English)'])

# start_generate —— 取值从 currentText() 改为 currentData()
self.thread = GenerateThread(
    topic, self.pages_spin.value(), language,
    self.style_combo.currentData(),   # 原来是 currentText()
    references, context,
)
```

```python
# outline_generator.py（未改动）—— 依赖 style 为英文值做主题映射
theme = {"Business": "business", "Academic": "academic", "Creative": "creative"}.get(style, "business")
```

## 验证结果
- py_compile：4 个文件全部通过
- 离屏测试：style 下拉框 `itemText`=中文 / `itemData`=英文 / `currentData()` 返回 'Business'；
  语言下拉框 `currentIndex()` 逻辑不变；按钮文本汉化确认；`currentData → theme` 映射正确
- `_test_export.py` 全量 5 项全绿
- exe 重新打包 59.4 MB，冒烟测试进程存活、日志无报错

## 审查范围
请独立审查以上汉化是否有 P0/P1/P2/P3 风险，特别关注：
1. **style 下拉框 `currentText()`→`currentData()` 变更**：`currentData()` 在未选中任何项 / 数据为空时是否可能返回 `None`，导致 `outline_generator` 的 theme 映射 `dict.get(None)` 回退 "business" 是否可接受；所有取值路径是否一致
2. **语言下拉框**：`addItems(['中文 (Chinese)', '英文 (English)'])` 后，`start_generate` 里 `language = 'zh' if currentIndex()==0 else 'en'` 是否仍正确；settings_dialog 里 `lang_val` 的 index 映射是否同步
3. **是否有遗漏的界面英文字符串**（QMessageBox、QLabel、QPushButton、状态栏、窗口标题、placeholder、预览 HTML 等）
4. **中文是否影响功能**：任何以界面文本作为逻辑判断值的地方（如 `.text()` 被用于比较/映射）
5. 其他兼容性/健壮性问题

请独立判断，禁止修改代码，仅输出 CODE REVIEW REPORT 格式报告。
