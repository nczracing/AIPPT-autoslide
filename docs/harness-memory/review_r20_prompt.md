# AutoSlide 第20轮独立代码审查请求

你是独立代码审查者。请审查 E:/study/projects/autoslide/core/pptx_builder.py 中刚完成的"图文排版修复"改动。

## 审查背景

用户报告：生成物中图片与文字冲突（重叠），文字可能显示在幻灯片屏幕之外。本次改动目标：
1. 图片与正文框零重叠（right/left/top 三种布局）
2. top 布局图片不再压住标题区（图片 top >= 1.45"）
3. 正文按最终几何自适应字号（两级：缩字号 → 紧凑排版），杜绝文字越出幻灯片边界
4. 双栏（two_content）在图片存在时在安全文字区内均分，不再互相重叠

## 本次改动点（供定位）

- 新增 `self._content_registry` 正文注册表（__init__，build 循环每页重置）
- `_content_textbox` 增加 register 参数；`_fill_content`/`_fill_two_content` 登记内容
- `_write_body` 增加 scale/compact 参数
- `_calc_image_position`：top 模式 top=1.45、max_height=2.4；left/right 高图高度上限 5.3；兜底不越下边界
- 重写 `_adjust_textbox_for_image`：覆盖 add_textbox + 占位符，按图片实际矩形算安全文字区，多栏均分
- 新增 `_estimate_body_height` / `_fit_registered_text`（两级自适应 + normAutofit 兜底）
- `_set_title`/`_set_subtitle` 按长度自适应字号
- `_fill_references` 调用 `_content_textbox(register=False)` 防止文献被自适应重写清空

## 验证结果（已完成）

- python -m py_compile 通过
- _test_layout.py（新增）：10 场景（right/left/top/fullscreen × 方/宽/高图、双栏+图、无图超量文字）全部通过：图文无重叠、无越界、文字可容纳
- _test_export.py 5/5 通过

## 审查要求

- 禁止修改代码、禁止输出完整替代实现、禁止扩大需求、禁止风格重构
- 必须区分真正风险 / 优化建议 / 个人偏好
- 输出格式：
  - Overall Result: PASS / FAIL
  - Risk Summary: P0/P1/P2/P3 分级列出
  - Findings: 每条含 编号(F-20-XX)、等级、文件:行号、描述、建议
