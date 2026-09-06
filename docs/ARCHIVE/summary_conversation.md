# AutoSlide 项目对话概要

## 背景
- **项目定位**：基于 PyQt6 与 python‑pptx 的 AI 自动化 PPT 制作系统。
- **主要技术栈**：Python 3.13.12、PyQt6、python‑pptx、Pillow、PyInstaller、InnoSetup。
- **目标**：从需求 → 实现 → 打包 → 多版本发布（onedir、安装包、单文件）。

## 近期开发进度
1. **动画系统**：
   - 迁移到合法的 OOXML `<p:timing>` 结构，重写 `pptx_builder.py` 中的 `_add_slide_transition()` 与 `_add_slide_animations()`。
   - 支持入场动画与过渡（`fade`, `push`, `wipe`, `uncover`, …）。
2. **主题支持**：`ui/theme.py` 中实现 `apply_theme(app, mode)`，可在运行时切换轻/暗模式。
3. **预览组件**：使用 `preview_widget.py` 开发幻灯片式卡片浏览，提升内部预览体验。
4. **打包方案**：
   - **onedir**：`dist/AutoSlide/`（含 `_internal/`）
   - **安装包**：`installer/AutoSlide-Setup.exe`（InnoSetup）
   - **单文件**：`dist/AutoSlide_oneline.exe`（PyInstaller onefile）
   - 解决 `--onefile` 的解压卡死问题，改用 onedir+InnoSetup。
5. **目录重组**：创建 `tests/`、`docs/`、`scripts/`，清理 `build/` 与 `__pycache__/`。
6. **README 更新**：待完成，计划加入动画、主题、构建方法、目录结构等信息。

## 待完成任务
- **整理项目文件夹**：移除 `build/`、`__pycache__/`、过旧日志，归类 `samples/` 和 `.harness-memory/`。
- **完善 `README.md`**：内容细化，徽章更新至 `Python 3.13.12`。
- **Agnes API Key 通知**：当前返回 401，需更新以恢复 AI 功能。

## 会议记录
- **用户提问**：如何继续推进项目？
- **助手回应**：已展示项目进度与待实现点，提供进一步行动方案。

---

> 说明：此文件为对话概要，后续更新保存在 `E:/study/.workbuddy/memory` 中。
