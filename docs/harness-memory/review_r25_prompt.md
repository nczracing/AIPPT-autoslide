# CODE REVIEW REQUEST — Round 25

## 项目
E:/study/projects/autoslide（AutoSlide：PyQt6 AI PPT 生成器）

## 本轮改动范围（仅以下两处）
1. `core/pptx_builder.py` `_calc_image_position`：bottom 横幅新增 `banner_bottom_margin = 0.35`，
   top 由 `slide_h - band_h`（=5.1，底边贴 7.5 画面底端）改为 `slide_h - band_h - banner_bottom_margin`（=4.75，底边 7.15）。
   触发原因：用户反馈"底部图片不要贴住屏幕底端"。
2. `_test_layout.py` V6b 断言扩展：bottom 布局横幅底边（top+height）必须 ≤ 7.5-0.3+0.02（贴底检查）。

未改动其他文件。top 布局、right/left/fullscreen、页脚上移逻辑（_relocate_footer_above 仍以横幅 top 为基准上移 0.5"）、文字区计算（bottom 布局 region 以 img_top 为界自动收缩 0.35"）均未触碰。

## 已做验证
- py_compile 两文件通过
- 探针：bottom 横幅 top=4.75 / h=2.40 / bottom_edge=7.15 / 底边距=0.35 ✓
- _test_layout.py 12 场景通过（含 V6/V6b 新断言）
- _test_extreme.py 7 场景通过
- _test_export.py 通过
- samples/AI排版演示_2026-09-04.pptx 已重建，5 页自检 0 问题

## 审查重点
1. bottom 横幅上移 0.35" 后，页脚上移（band_top-0.5=4.25）与文字区（1.5→4.5）是否仍无重叠/越界
2. banner_bottom_margin 硬编码 0.35 是否与其他边距常量体系冲突
3. V6b 新断言容差（±0.02）是否合理
4. 是否存在被遗漏的 bottom 横幅几何依赖点（如装饰元素、_grow_image_for_sparse_content）

## 输出格式（严格遵守）
# CODE REVIEW REPORT
## Overall Result: PASS / PASS(有条件) / FAIL
## Risk Summary
- P0: （数量与简述，无则写 None）
- P1: ...
- P2: ...
- P3: ...
## Findings
每条 finding 格式：F-25-NN | 等级 | 文件:行 | 问题描述 | 判断（真正风险/优化建议/个人偏好）| 依据 | 建议处置
