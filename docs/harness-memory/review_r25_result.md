

所有信息已收集完毕，输出审查报告。

---

# CODE REVIEW REPORT

## Overall Result: **PASS(有条件)**

改动本身几何正确，无 P0 缺陷。存在一处测试容差设计弱于代码的实际约束（F-25-01）、一处文档/常量的不一致性（F-25-02），以及一个命名体系的观察点（F-25-03）。

---

## Risk Summary

- **P0: None**
- **P1: 1** — V6b 断言阈值（7.20）与代码实际输出（7.15）之间存在 0.05" 冗余容差，导致回归保护力下降
- **P2: 2** — bottom_limit=7.1 注释与 bottom 模式实际底边（7.15）不一致；`banner_bottom_margin` 与其他底部边距常量未做同名/集中定义
- **P3: 1** — 函数 docstring 描述偏旧，不影响功能

---

## Findings

**F-25-01 | P1 | `_test_layout.py:228` | V6b 断言容差值与常量体系脱节，削弱回归保护** | 真正风险 | 代码硬编码 `banner_bottom_margin = 0.35`，产生 bottom_edge = 7.15。测试断言阈值写为 `7.5 - 0.3 + 0.02 = 7.20`，比实际值宽松 0.05"。若未来有人（或自动化重构）误将 `banner_bottom_margin` 改为 0.30，bottom_edge 将变为 7.20，刚好通过测试，但安全边距已被偷走 0.05"。

建议处置：将断言阈值改为与实际代码一致的表达式，使测试成为代码行为的"镜像"而非独立阈值。例如：

```python
# 当前（弱约束）
if bottom_edge > 7.5 - 0.3 + 0.02:

# 建议（强约束：直接用代码中的常量推导）
# 需同时把 banner_bottom_margin 提升为模块级常量
if bottom_edge > SLIDE_H - band_h + 0.02:
    # 或：SLIDE_H - BANNER_BOTTOM_MARGIN
```

---

**F-25-02 | P2 | `pptx_builder.py:929` / `:923` | `bottom_limit = 7.1` 的注释与 bottom 模式实际底边不一致** | 真正风险（误读风险） | Docstring 写"底边不得低于 7.1\""，而 bottom 模式的实际底边是 `slide_h - band_h - banner_bottom_margin = 7.15`。`bottom_limit` 仅作用于 right/left 分支（line 973 有 `if layout_mode not in ("top", "bottom")` 豁免），bottom 分支根本不读这个变量。注释会让读者误以为 bottom 横幅也受 7.1 约束。

建议处置：更新 docstring 明确说明该约束仅适用于 right/left 分支，或在 bottom 分支附近加一行注释说明实际底边为 7.15。

---

**F-25-03 | P2 | `pptx_builder.py:929/948/1141` | 三处底部安全边距散落在函数体内，缺乏集中定义** | 优化建议 | 代码中存在三个语义相似的"距底边最小距离"常量，但分别定义在不同函数内：
- `bottom_limit = 7.1`（距底边 0.4"）— right/left 图片下界（line 929）
- `banner_bottom_margin = 0.35`（距底边 0.35"）— bottom 横幅底边距（line 948）
- `margin_bottom = 0.55`（距底边 0.55"）— 文字区底边距（line 1141）

三者数值各异、互不冲突，各自服务于不同元素，但命名不统一（一个用 limit，一个用 margin），阅读时容易混淆。

建议处置：在类级别集中定义底部边距常量（如 `BOTTOM_IMAGE_LIMIT = 7.1`、`BANNER_BOTTOM_MARGIN = 0.35`、`TEXT_REGION_MARGIN_BOTTOM = 0.55`），或在现有 `band_h`/`band_w` 附近追加一行说明与另外两个常数的关系。非强制，仅作可读性改进。

---

**F-25-04 | P3 | `pptx_builder.py:918-924` | 函数 docstring 描述过旧** | 个人偏好 | Docstring 末句"底边不得低于 7.1\""现在对 bottom 模式不再准确（实际为 7.15）。建议同步 F-25-02 一起更新。

---

## 补充验证（审查中自行核查，不在原始 Prompt 列出的 Findings 中）

| 检查项 | 结论 |
|---|---|
| 页脚位置：footer_top = band_top − 0.5 = 4.75 − 0.5 = **4.25**，footer 底边 = 4.50 | ✓ 远低于文字区顶 4.75 |
| 文字区 top = 4.75，bottom = band_top = 4.75（紧贴但无重叠，gap=0） | ✓ 几何上无侵入 |
| 装饰元素是否侵入 band [4.75, 7.15] | ✓ flow deco 最低 y=6.4 < 6.97（band 顶）；其他母题均在 y<6.0 范围 |
| `_grow_image_for_sparse_content` 影响 bottom | ✗ 仅在 `right`/`left` 分支执行，bottom 不受影响 |
| `_adjust_textbox_for_image` bottom 分支 region_h = 4.75 − 1.5 − 0.25 = **3.0"** | ✓ region_h ≥ 1.5（line 1179 兜底），无越界 |
| _test_extreme.py / _test_export.py | ✓ 通过，未见 bottom 相关失败 |
| 样本 PPTX 自检 0 问题 | ✓ |
