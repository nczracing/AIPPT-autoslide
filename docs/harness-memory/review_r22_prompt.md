# AutoSlide 第22轮独立代码审查请求

你是独立代码审查者。请审查 E:/study/projects/autoslide 中刚完成的"AI驱动布局 + 图片比例协调 + UI进度细化"改动。

## 改动背景

用户两点需求：
1. 排版种类太少（随机轮换），希望 AI 按内容语义决定每页布局；图片比例不对、画面不协调
2. UI 生成进度无法直观了解所需时间

## 本次改动点

### core/prompt_builder.py
- 大纲 prompt 新增 image_layout 字段说明：AI 从 right/left/top/bottom/fullscreen 按内容语义与视觉节奏选择

### core/outline_generator.py
- 新增 `_normalize_image_layout(value, page)`：校验 AI 返回（大小写/空白容忍），非法值回退按页码确定性轮换 (right,left,top,bottom)

### core/pptx_builder.py
- `_calc_image_position`：top 模式改为全宽横幅带（left=0, w=13.333, h=2.4, top=1.45）；新增 bottom 模式（贴底通栏）；两者豁免底部越界兜底
- 新增 `_apply_cover_crop`：cover-fit 居中裁切（crop 属性），top/bottom/fullscreen 图片保持比例不拉伸
- `_add_fullscreen_image`：全屏背景按 16:9 裁切（修复原拉伸变形）
- 新增 `_relocate_footer_above`：bottom 横幅盖住页脚时页脚自动上移
- `_adjust_textbox_for_image`：新增 bottom 分支（文字区在标题与横幅之间）
- 修复：`_add_image` 中曾引用未定义的 slide_w（NameError 被吞），已改用 self.SLIDE_W 换算

### core/image_generator.py
- 新增 LAYOUT_IMAGE_SIZES：right/left→1024x1280(4:5)、top/bottom→1440x720(2:1)、fullscreen→1024x576(16:9)
- `generate()`/`_generate_ai()` 接受 layout 参数；布局尺寸被 AI 拒绝时回退用户配置尺寸重试一次
- 重构出 `_request_image` + `_save_image_result`
- `_generate_fallback`：Pillow 兜底画布按 LAYOUT_FALLBACK_CANVAS 匹配布局比例

### ui/generator_widget.py
- GenerateThread 新增 progress_step(percent, msg, eta) 信号：大纲阶段 3~45%（ETA 60s 经验值）、插图 45~95%（按已完成图片实测均耗时推算剩余）、打包 96~100%
- Widget：进度条改确定模式、新增时间标签（QTimer 每秒刷新"已用时 mm:ss · 预计剩余约 mm:ss"）

## 验证结果（已完成）

- py_compile 全部通过
- _test_layout.py 12 场景（含 bottom×2 + V6 裁切验证）✓
- _test_extreme.py 7 场景 ✓
- _test_export.py 5/5 ✓
- _normalize_image_layout 6 断言 ✓
- 演示文件 5 页（5 种布局×匹配比例插图）生成成功
- exe 冒烟 ✓

## 审查要求

- 禁止修改代码、禁止输出完整替代实现、禁止扩大需求、禁止风格重构
- 必须区分真正风险 / 优化建议 / 个人偏好
- 输出格式：
  - Overall Result: PASS / FAIL
  - Risk Summary: P0/P1/P2/P3 分级列出
  - Findings: 每条含 编号(F-22-XX)、等级、文件:行号、描述、建议
