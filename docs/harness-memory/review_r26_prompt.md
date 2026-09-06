# CODE REVIEW REQUEST — Round 26

## 项目
E:/study/projects/autoslide（AutoSlide：PyQt6 AI PPT 生成器）

## 本轮需求
用户：「我不想要裁剪的图片，可以每张都是原比例吗，调整生成图片的比例而不是修改模板」
即：图片按原始比例完整显示（零裁剪），从生成端解决，不改模板。

## 本轮改动范围
1. `core/image_generator.py`：
   - `LAYOUT_IMAGE_SIZES` top/bottom 由 "1536x512"(3:1) 改为 "1536x309"(4.971:1)，
     精确匹配横幅显示框比例 (13.333-1.4)/2.4≈4.972 → 零裁剪；right/left 与 fullscreen 不变
   - 新增 `LAYOUT_FALLBACK_SIZES`（API 拒绝精确尺寸时的次级回退 1536x512），
     `_generate_ai` 回退链改为 精确比例→近似比例→用户配置尺寸（去重保序）
   - `LAYOUT_FALLBACK_CANVAS` top/bottom 同步 (1536, 309)
2. `core/pptx_builder.py`：
   - 新增类常量：BANNER_FRAME_RATIO=(13.333-1.4)/2.4、BANNER_BAND_H=2.4、
     BANNER_BAND_H_MIN=1.6、BANNER_BAND_H_MAX=3.75、BANNER_BAND_W_MIN=4.0
   - `_calc_image_position` top/bottom 分支：横幅高度先按图片比例自适应
     （钳制 1.6~3.75"），宽度随之贴合图片比例（钳制 ≥4.0"，居中收窄
     left=0.7+(band_w_max-band_w)/2）；生成比例精确时几何与旧版完全一致
   - `_add_image`：横幅裁剪仅在比例偏差 >1% 时执行（<1% 视为原比例显示）；
     fullscreen 背景裁剪逻辑未动
3. `_test_layout.py`：
   - 新增测试图 band(1536,309)；`_expected_band_geometry` 镜像二维自适应几何
   - V6 裁切断言改用镜像推导目标比例；V6b 改为验证带区内居中+不超宽+bottom 不贴底
   - 新增 V8 零裁剪断言：精确比例图 → crop 全 0 + 标准带宽/高 + bottom 底边 7.15

未改动：fullscreen 背景裁切、right/left 布局、页脚上移、文字区计算（随实际图片矩形自适应）、
AI prompt/大纲解析。

## 已做验证
- py_compile 三文件通过
- 三层测试：12 场景（含 V8）+ 7 极端 + 导出链路 全部通过
- 探针（bottom 布局）：
  - 4.97:1 图（生成端正常出图）：11.93×2.40 零裁剪，几何与旧版一致
  - 2:1 图：7.50×3.75 居中，零裁剪（原比例完整显示）
  - 1:1 图：4.00×3.75，残余裁切 6.3%（宽度下限钳制所致，有界）
  - 1:2 图：4.00×3.75，裁切 53%（竖图入横幅带，几何上不可避免，有界）
- samples/AI排版演示_2026-09-04.pptx 已重建（top/bottom 页用 1536x309 精确比例配图，零裁剪自检通过）

## 审查重点
1. 二维自适应（高度优先→宽度贴合→二次钳制）逻辑是否有边界死循环/几何越界
2. 横幅收窄后与文字区/页脚/装饰元素是否可能重叠（bottom 文字区 region_h 用 img_top 推导）
3. 1% 裁剪容忍阈值是否合理；LAYOUT_FALLBACK_SIZES 回退链是否会产生重复请求
4. V8/V6b 测试镜像是否与实现严格一致（F-25-01 教训：断言必须镜像代码常量）
5. 1536x309 极端比例对 AI 出图质量的潜在影响（无法离线验证，评估风险即可）

## 输出格式（严格遵守）
# CODE REVIEW REPORT
## Overall Result: PASS / PASS(有条件) / FAIL
## Risk Summary
- P0/P1/P2/P3: （数量与简述，无则写 None）
## Findings
每条格式：F-26-NN | 等级 | 文件:行 | 问题描述 | 判断（真正风险/优化建议/个人偏好）| 依据 | 建议处置
