# AutoSlide 第 24 轮独立代码审查请求

你是独立代码审查者（Pi/Claude）。**只审查，不修改任何代码，不输出替代实现。**

## 背景
用户反馈：图文左右结构（right/left 布局）文字较少时，文字与图片之间空出一段明显留白。

## 本轮改动范围（仅 core/pptx_builder.py + _test_layout.py）
1. **新增 `_estimate_natural_width`**：按 CJK≈0.82×字号 / ASCII≈0.55×字号 估算正文自然宽度
2. **新增 `_grow_image_for_sparse_content`**：right/left 单栏且自然宽度比文字区窄 >1" 时，插图在锚点（right 保右边缘 / left 保左边缘）与比例不变前提下放大，最多 5.6" 宽 / 5.5" 高，垂直居中于 [1.45, 7.1]
3. **`_adjust_textbox_for_image`**：
   - right/left 时先调用上述放大逻辑，再计算文字区
   - 单栏且 est_h < region_h - 0.9 时正文块垂直居中（top 下移、高度收为 est_h+0.35，防止触发字号缩放）
4. **修复连带 Bug**：空 BODY 占位符（模板自带、无文字）此前被计入文字框集合，导致单栏正文被误拆为双栏（文字挤进 3" 窄列）——现在跳过无文字占位符
5. **_test_layout.py**：新增 `verify_sparse_balance`（V7：稀疏页插图宽 >4.6"、正文 top >2.2）

## 审查重点
a) 放大逻辑与 _calc_image_position 的兜底约束（bottom_limit/title_zone/最小高1.2"）是否有冲突路径
b) 垂直居中后 _fit_registered_text 以新几何（较小 box_h）评估，est_h+0.35 余量是否足够避免误缩字号（estimator 有 0.15 基数余量）
c) 空占位符跳过是否会误伤"有占位符但内容延迟写入"的路径（fullscreen 模式文字、references 页）
d) 双栏（two_content）+ 图片场景不受放大影响（registry 2 条 → 不放大），确认无回归
e) 极端：空内容页（无 detail 无 points）natural_w=0 不放大、est_h=0 不居中，确认无除零/越界

## 验证已做
py_compile ✓；_test_layout 12 场景+V7 ✓；_test_extreme 7 ✓；_test_export 5/5 ✓；probe 验证 sparse/rich/sparse_left 三场景几何符合预期 ✓

项目根目录：E:/study/projects/autoslide
输出：CODE REVIEW REPORT（Overall Result + Risk Summary P0-P3 + Findings 7字段）
