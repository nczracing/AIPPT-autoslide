你是 AutoSlide 项目的独立代码审查者。请审查本轮改动（第27轮）。

## 本轮改动范围
用户需求：「Agnes API 恢复 + settings 完整性确认 + Pillow 兜底质量微调，同时修改版本号」

改动文件（5个）：
1. `core/image_generator.py` — Pillow 兜底图质量微调
2. `ui/main_window.py` — 版本号 v1.0→v1.1
3. `scripts/autoslide_setup.iss` — AppVersion 1.0→1.1
4. `ui/generator_widget.py` — 风格下拉新增 Tech/Vibrant
5. `core/outline_generator.py` — 主题映射新增 Tech→tech、Vibrant→vibrant
6. `core/pptx_builder.py` — _recommend_layout 重写（尊重显式选择）+ _estimate_natural_width 系数修正

## 审查重点
### 1. core/image_generator.py（Pillow 兜底质量）
- `_THEME_COLORS` 新增 tech/vibrant 两主题配色是否与 pptx_builder.THEMES 色阶一致
- 网格线改为在 RGBA overlay 上绘制（之前画在 RGB 图上 alpha=18 被忽略，线条发黑），是否正确
- `line_scale` 系数（aspect/2.0）对 1024x1280(right) 与 1536x309(top) 的适配是否合理
- 卡片圆角 `card_radius = max(8, min(32, int(height*0.03)))` 在不同画布高度下是否过大/过小
- 无标题场景改为水平居中细线，是否与有标题场景的顶部装饰条逻辑冲突
- `has_title = bool(font_path and slide_title)` 是否覆盖所有标题渲染分支

### 2. core/pptx_builder.py（_recommend_layout 重写 — 重点）
- 原 9/7 版 `_recommend_layout` 按内容特征覆盖 image_layout，破坏了 9/4 建立的 top/bottom 横幅零裁剪链路（V6/V8 测试 18 项失败）
- 本版改为：「image_layout 始终尊重上游显式值（slide.image_layout），不做智能覆盖；仅对页面结构（双栏/单栏）做内容感知推荐」
- 检查 `build()` 方法中 `layout_mode`/`image_layout` 的取值逻辑是否自洽：
  - `visual["layout"].get("image_layout") or (slide.image_layout if slide.image_path else "right")`
  - 当 `_recommend_layout` 返回 `image_layout=None` 时，`or` 兜底到 `slide.image_layout`（默认 "right"），是否正确
- `_estimate_natural_width` 系数从 CJK 0.82/ASCII 0.55 改为 1.0/0.6，是否导致稀疏放大逻辑过度触发（natural_w 偏大 → 放大条件 `region_w - natural_w > 1.0` 更难满足 → 图片不放大）

### 3. settings 完整性
- settings.py 默认配置 5 个 image_* 键是否齐全
- configs/settings.json 源码模式兜底是否合理
- exe 模式 AppData 路径逻辑是否正确

### 4. 版本号一致性
- main_window.py / autoslide_setup.iss / 关于对话框 是否都改为 1.1
- 是否有遗漏的版本引用（如 README / 文档）

## 已做验证
- py_compile 全部通过（image_generator / main_window / generator_widget / outline_generator / settings）
- _test_layout.py 12场景全绿（V1-V8 含横幅零裁剪/裁切兜底/稀疏均衡）
- _test_extreme.py 7极端场景全绿
- _test_export.py 导出链路5项全绿
- PyInstaller 打包 onedir 成功（dist/AutoSlide/AutoSlide.exe 9.8MB）
- ISCC 安装包成功（installer/AutoSlide-Setup.exe 41.7MB）
- 冒烟测试：进程存活、窗口句柄非0、正常停止
- Agnes API 探活成功（env AGNES_API_KEY 有效，生图返回平台URL）

## 输出格式
请输出：
1. **Overall Result**: PASS / PASS(有条件) / NEEDS_FIX
2. **Risk Summary**: P0/P1/P2/P3 计数
3. **Findings**: 每个问题用7字段（ID / 等级 / 文件 / 行号 / 描述 / 建议 / 是否阻断）
4. 若有 P0/P1/P2 需修复，请给出明确修复建议；P3 或审查者明示可接受的请标注"接受风险"
