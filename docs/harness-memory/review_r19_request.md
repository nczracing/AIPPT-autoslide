<review-package>
<project-path>E:/study/projects/autoslide</project-path>
<review-round>19</review-round>
<request-title>图片布局适配优化</request-title>

<summary>
本轮功能：修复图片与文字适配问题。

原问题：
- 图片尺寸硬编码，不保持原始宽高比，方形图被拉伸
- 位置固定，不随图片比例自适应
- 文本框不随图片位置动态调整

优化内容：
1. 使用PIL读取图片原始像素尺寸
2. 根据宽高比动态计算最佳PPT尺寸（保持比例）
3. 智能居中定位（right/left/top三种模式）
4. 文本框自适应避免重叠
5. 加入幻灯片级动画（fade/push/wipe/dissolve/uncover）
6. 加入文字出现动画（标题淡入、要点飞入）

涉及文件：
- core/pptx_builder.py：重写图片布局逻辑，新增动画方法
- core/outline_generator.py：自动分配图片布局（right/left/top循环）
- settings_module/models.py：Slide新增image_layout字段
</summary>

<key-code-paths>
core/pptx_builder.py: _calc_image_position, _get_image_dimensions, _adjust_textbox_for_image
core/pptx_builder.py: _add_slide_transition, _add_title_anim, _add_content_anims
core/outline_generator.py: image_layout自动分配
settings_module/models.py: image_layout字段
</key-code-paths>

<questions>
1. 图片宽高比计算是否可能除零？img_ratio = img_width/img_height，有0值保护
2. 动画注入的XML结构是否符合Open XML规范？
3. 文本框调整是否会遮挡其他元素？
4. 不同图片比例的边界情况如何处理？
</questions>

<constraints>
- 图片必须保持原始比例，不能拉伸变形
- 文本框不能与图片重叠
- 动画不能在PPT中导致崩溃或显示异常
- 全图模式需要半透明蒙层确保文字可读性
</constraints>

<guidance>
重点关注：
1. 尺寸计算是否正确处理了各种宽高比（方形/宽图/高图）
2. 动画注入的XML结构是否完整有效
3. 文本框调整逻辑是否覆盖所有边界情况
4. 是否存在潜在的除零或空值风险
</guidance>
</review-package>