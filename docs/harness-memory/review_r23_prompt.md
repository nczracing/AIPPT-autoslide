# AutoSlide 第 23 轮独立代码审查请求

你是独立代码审查者（Pi/Claude），本轮审查 AutoSlide 的两项改动。**只审查，不修改任何代码，不输出替代实现。**

## 背景
用户反馈：①top/bottom 横幅插图不要铺满全宽；②优化前端 UI 视觉效果。

## 本轮改动范围
1. `core/pptx_builder.py`
   - `_calc_image_position`：top/bottom 横幅从全宽（left=0, w=13.333）改为与正文边距对齐的居中横幅（left=0.7, w=11.93, 高 2.4 保持）
   - `_add_image`：cover-fit 裁切目标比例改为用 `width.inches / height.inches`（显示框实际比例），替换原 `SLIDE_W/914400` 推导
2. `core/image_generator.py`
   - `LAYOUT_IMAGE_SIZES`/`LAYOUT_FALLBACK_CANVAS`：top/bottom 出图比例 1440x720 → 1536x512（更接近横幅 4.97:1 目标，减少裁切损失）
3. **前端 UI 视觉优化**（新文件 `ui/theme.py` + 各 UI 文件小改）：
   - 新增全局 QSS 主题（`apply_theme`：Fusion 调色板 + APP_QSS），主色 #2f6fed、圆角 8px、悬停/按下/焦点态、渐变进度条、自定义滚动条
   - `main.py`：`app.setStyle('Fusion')` → `apply_theme(app)`
   - `ui/main_window.py`：标题栏 objectName='titleBar'，加 logo 标签，间距统一
   - `ui/generator_widget.py`：字段标签 objectName='fieldLabel'、主按钮 objectName='primaryBtn'、进度/时间标签 objectName、布局 spacing/margins、完成态 doneLabel
   - `ui/settings_dialog.py`：移除两处硬编码深色 QGroupBox 边框、配置提示条改浅色信息条、保存按钮改 primaryBtn（并提为 self.save_btn）、agnes_hint 颜色协调

## 审查要求
输出 CODE REVIEW REPORT，格式：
- Overall Result: PASS / PASS(有条件) / FAIL
- Risk Summary: 按 P0（阻断）/P1（重要）/P2（一般）/P3（建议）分级列出
- Findings: 每项含 [编号/等级/文件:行号/问题描述/建议]
- 重点检查：
  a) 横幅几何改动是否引入新的重叠/越界/文字挤压风险（bottom 模式页脚上移逻辑是否仍正确）
  b) QSS 是否存在控件状态冲突、深浅色不一致、失配的 objectName（如 'QFrame QLabel' 选择器副作用）
  c) apply_theme 中 palette 与 QSS 的相互作用是否有坑（如 Fusion + 自定义 QSS 的 focus 边框 padding 切换）
  d) 出图尺寸 1536x512 对 Agnes API 是否可能非法（格式 WxH 合法即可）
  e) 回归风险：主按钮 disabled 态、进度条 text 居中在渐变 chunk 上的可读性等

## 验证已做
py_compile 全部通过；_test_layout.py 12 场景（V6 裁切 + V6b 非全宽断言）✓；_test_extreme 7 场景 ✓；_test_export 5/5 ✓；offscreen UI 运行时验证（主窗口构建+进度流+设置对话框+primaryBtn objectName）✓

项目根目录：E:/study/projects/autoslide
