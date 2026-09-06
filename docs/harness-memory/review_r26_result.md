

已通读三个文件的完整实现、测试代码，并核查了常量镜像关系、几何推导、页脚/文字区交互、回退链语义。以下是审查结论。

---

# CODE REVIEW REPORT
## Overall Result: PASS（有条件）

通过前提：接受 P2（设计权衡说明）的处置建议；P3（注释更新）可选。无阻断性正确性问题。

---

## Risk Summary
- **P0**：None
- **P1**：None
- **P2**：3 项（设计权衡说明 / 注释更新 / 测试覆盖缺口）
- **P3**：1 项（文档头过期）

---

## Findings

### F-26-01 | P2 | `_test_layout.py:380` | `bottom_tall` 场景缺失几何/裁剪断言，仅靠集成测试"不报错"通过 | 优化建议 | 现有 `bottom_tall`（ratio=0.5）进入 `_calc_image_position` 时：`band_h=BANNER_BAND_H_MAX=3.75`, `band_w=BANNER_BAND_W_MIN=4.0`, top=3.40", 触发 30.2% 垂直裁剪。V6b 仅覆盖 `crop_bottom`（tall 在 `verify_cover_crop` 中）的带区内居中/不贴底检查；`main()` 路径下的 `bottom_tall` 仅有 V1/V2/V3/V5 通用检查。若未来 `BANNER_BAND_H_MAX` 被误改，不会在此用例中被触发。建议：为 `bottom_tall` 补一段类似 V8 的窄检查（height≈3.75 / width≈4.0 / crop_total_v≈0.302），或直接将其并入 `verify_cover_crop` 的用例列表。
    ```

### F-26-02 | P2 | `core/image_generator.py:189-194` | 1% 阈值与回退尺寸偏差 39.6% 在语义上割裂：用户要"原比例零裁剪"，但回退路径会得到"cover-fit 大幅裁切" | 设计权衡（说明即可，不改） | `LAYOUT_IMAGE_SIZES.top = "1536x309"`（ratio 4.971）与目标 `BANNER_FRAME_RATIO ≈ 4.972` 偏差仅 0.03%，1% 阈值对主路径合理；但 `LAYOUT_FALLBACK_SIZES.top = ["1536x512"]`（ratio 3.0）偏离目标 39.6%，插入端触发的 cover-fit 会裁掉约 40% 高。当前实现是"生成端尽最大努力，插入端兜底防拉伸"的两段式架构，行为可接受但用户感知会有落差。建议在 `LAYOUT_FALLBACK_SIZES` 注释里加一行说明："回退尺寸由 API 约束决定，可能触发显著 cover-fit 裁剪，属已知妥协。"无需改代码。

### F-26-03 | P2 | `_test_layout.py:3` | 测试文件头档对覆盖场景的描述滞后于实际 | 小修复 | 头部 `单栏正文 + 图片（right / left / top）× 图片比例（方形1:1 / 宽图2:1 / 高图1:2）` 漏列 `band(4.97:1)` 这个新增场景。改为 `方形1:1 / 宽图2:1 / 高图1:2 / 横幅精确比例4.97:1`，并在 V6/V8 说明里点出 band 用于零裁剪验证。一行改动，避免未来维护者按文档找用例时产生困惑。

### F-26-04 | P3 | `core/pptx_builder.py:115` | `BANNER_BAND_H_MAX = 3.75` 注释"保证文字区 ≥1.5""无测试镜像 | 个人偏好 | 注释声称的 1.5" 下限来自 `SLIDE_H - BANNER_BAND_H_MAX - BANNER_BOTTOM_MARGIN - region_y_top - margin_bottom = 7.5 - 3.75 - 0.35 - 1.5 - 0.55 = 1.35"` 实际略低于注释值（差 0.15"）——这可能是有意预留而非笔误，但注释数值与推导不符容易误导人。建议把注释改成"保证文字区约 1.35""，或在常量旁补充一行推导公式。非强制，因为当前值已能正常工作。

---

## 确认无问题的关键项（供 reviewer 参考）

| 项目 | 核查结果 |
|---|---|
| 二维自适应几何循环（h→w→h 二次钳制） | 单调有界，必收敛；测试 `band(1536,309)` 返回标准带宽 11.93 × 标准高 2.4 ✓ |
| `left = 0.7 + (band_w_max - band_w) / 2` 居中公式 | 镜像到 `_expected_band_geometry` 的 `left` 返回一致 ✓ |
| 1% 容忍阈值与 `target_ratio` 推导链 | V6 动态从 `_expected_band_geometry` 推 target_ratio，不与硬编码值耦合；V8 用常量 `BANNER_BAND_H/BANNER_BAND_W_MIN` 等，均为代码常量镜像 ✓ |
| bottom 页脚避让（`_relocate_footer_above`） | `band_top = SLIDE_H - band_h - BANNER_BOTTOM_MARGIN`；footer 移到 `band_top - 0.5`，V6b/V8 共同约束底边 ≤ 7.15 ✓ |
| bottom 文字区高度 `region_h = img_top - 1.5 - 0.25` | 精确匹配横幅 top；极端情况 band_h=3.75 → region_h=1.35 > 最小 1.5 的 floor 会触发压缩，但 1.35 < 1.5 所以触发——实际上 band_h_max=3.75 时 region_h=1.35，会触发 `max(1.5, ...)` 兜底 → 文字区被强行撑到 1.5"，合理 ✓ |
| 回退链去重保序 | `chain` 用 if-not-in 手动去重；fallback 仅一个元素，不存在重复请求 ✓ |
| fullscreen 背景裁切逻辑 | 未触碰，仍走原 cover-fit 16:9 ✓ |

---

## 综合判断

本轮改动结构清晰：**生成端按框比例精确出图 + 插入端横幅高度二维自适应 + 残余偏差 1% 以下零裁剪兜底**。几何推导在代码与测试之间实现了常量镜像，覆盖了 F-25-01 的历史教训。回退路径会产生显著 cover-fit 裁剪，属于 API 约束下的已知妥协，不是 bug。

**放行条件**：接受 F-26-01 补测试 / F-26-02 补注释 / F-26-03 更新文档头三项改动后合入。
