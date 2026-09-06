# -*- coding: utf-8 -*-
"""
PPTX构建器
将内容转换为实际的PPT文件（支持详细正文 + 要点 + 插图图文混排）。

背景采用「内容感知」生成：不再是每主题一张固定背景，而是根据每一页的
标题/正文/要点提取关键词，决定装饰母题（数据柱状图 / 技术节点 / 流程路径 /
学术书页 / 几何圆），再用内容哈希做确定性随机，决定装饰的位置、数量、尺寸、
渐变角度与配色微调。同一主题下不同页面背景各不相同，但同一内容可稳定复现。

增强功能（2026-09-03）：
- 插图布局多样化：right（右）/ left（左）/ top（上）/ fullscreen（全屏背景）
- 页面切换动画：根据页面类型随机选择过渡效果
- 文字出现动画：标题淡入、要点飞入（通过 lxml 直接注入 a:anim XML）
"""
import base64
import hashlib
import logging
import math
import os
import random
from pathlib import Path

from lxml import etree
from PIL import Image
from pptx import Presentation as PptxPresentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.enum.shapes import PP_PLACEHOLDER, MSO_SHAPE
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

from settings_module import Presentation as AppPresentation, Slide

logger = logging.getLogger("autoslide")

# XML 命名空间
NS_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS_ANIM = "http://schemas.openxmlformats.org/drawingml/2006/main"


class PPTXBuilder:
    """PPTX文件构建器"""

    # 布局映射（索引对应 python-pptx 默认模板 slide_layouts）
    # 0=Title Slide, 1=Title and Content, 3=Two Content
    LAYOUTS = {
        "title_slide": 0,  # 标题布局
        "title_content": 1,  # 标题+内容
        "two_content": 3,  # 双栏
    }

    # 主题配色（每个主题含背景渐变、装饰、标题、正文、强调等完整色阶）
    THEMES = {
        "business": {
            "title_color": (0, 51, 102),      # 深蓝（标题/色带/竖条）
            "accent_color": (51, 102, 153),   # 中蓝（强调/装饰线/要点）
            "text_color": (40, 40, 40),
            "bg_top": (255, 255, 255),        # 渐变顶部（白）
            "bg_bottom": (230, 240, 251),     # 渐变底部（极浅蓝）
            "deco_color": (196, 216, 240),    # 装饰圆（浅蓝）
            "deco2_color": (214, 230, 246),   # 装饰圆（更浅蓝）
        },
        "academic": {
            "title_color": (102, 51, 0),      # 棕
            "accent_color": (153, 102, 51),   # 浅棕
            "text_color": (45, 40, 35),
            "bg_top": (255, 253, 247),        # 米白
            "bg_bottom": (242, 232, 213),     # 浅米
            "deco_color": (232, 213, 185),
            "deco2_color": (240, 227, 204),
        },
        "creative": {
            "title_color": (102, 0, 102),     # 紫
            "accent_color": (153, 51, 153),   # 浅紫
            "text_color": (45, 40, 45),
            "bg_top": (255, 253, 255),        # 白
            "bg_bottom": (244, 234, 246),     # 极浅紫
            "deco_color": (232, 208, 238),
            "deco2_color": (240, 222, 244),
        },
    }

    # 关键词 → 装饰母题（按优先级顺序匹配）
    MOTIF_KEYWORDS = {
        "data": ["数据", "增长", "趋势", "分析", "统计", "指标", "性能",
                 "提升", "收益", "营收", "市场", "销售", "效率", "规模",
                 "增速", "比例", "利润", "数量", "上涨", "下降"],
        "tech": ["技术", "系统", "架构", "网络", "算法", "代码", "程序",
                 "软件", "工程", "计算机", "模型", "开发", "平台", "服务",
                 "接口", "自动化", "人工智能", "编程", "数据库", "框架"],
        "flow": ["流程", "路线", "规划", "目标", "路径", "步骤", "阶段",
                 "计划", "战略", "方向", "未来", "进度", "成长", "发展",
                 "演进", "里程碑", "时间线", "蓝图", "路线图"],
        "academic": ["学习", "教育", "研究", "理论", "知识", "方法", "概念",
                     "原理", "课程", "教学", "学术", "论文", "实验", "学科",
                     "基础", "定义", "公式"],
    }

    # 幻灯片尺寸（16:9）
    SLIDE_W = Inches(13.333)
    SLIDE_H = Inches(7.5)

    # bottom 横幅底边距画面底端的安全边距（英寸）。
    # 与文字区底部安全边距（_adjust_textbox_for_image 的 margin_bottom=0.55）、
    # right/left 图片下界（_calc_image_position 的 bottom_limit=7.1，距底 0.4"）
    # 各自独立，互不复用。
    BANNER_BOTTOM_MARGIN = 0.35

    # top/bottom 横幅显示框比例（band_w=slide_w-1.4 : band_h=2.4 ≈ 4.97:1）。
    # 图像生成端按此比例精确出图即可零裁剪（image_generator.LAYOUT_IMAGE_SIZES 镜像此值）。
    BANNER_FRAME_RATIO = (13.333 - 1.4) / 2.4
    BANNER_BAND_H = 2.4       # 标准横幅高度（图片比例精确匹配框比例时）
    BANNER_BAND_H_MIN = 1.6   # 比例自适应下限：防止极端宽图把横幅压成细线
    BANNER_BAND_H_MAX = 3.6   # 比例自适应上限（bottom 布局推导：要求文字区高 ≥1.8"
                              # 且与横幅顶边间距 ≥0.25" → img_top ≥ 1.5+1.8+0.25 = 3.55
                              # → band_h ≤ 7.5 - 0.35(BANNER_BOTTOM_MARGIN) - 3.55 = 3.6"）
    BANNER_BAND_W_MIN = 4.0   # 比例自适应时横幅最小宽度（避免窄成小方块）

    def __init__(self):
        self.themes = self.THEMES
        # 当前页正文注册表：记录正文框及其内容，供图片插入后统一调整几何+字号
        self._content_registry = []

    def build(self, presentation: AppPresentation, output_path: str) -> str:
        """构建PPTX文件"""
        prs = PptxPresentation()
        prs.slide_width = self.SLIDE_W
        prs.slide_height = self.SLIDE_H

        theme_name = presentation.theme or "business"
        theme = self.themes.get(theme_name, self.themes["business"])

        # 封面页和参考文献页无切换动画，其他页面随机选择
        slide_anims = []
        transition_effects = [
            "fade", "push", "wipe", "dissolve", "uncover",
        ]
        for i in range(len(presentation.slides)):
            if presentation.slides[i].layout == "title_slide":
                slide_anims.append(None)  # 封面页无过渡
            elif presentation.slides[i].layout == "references":
                slide_anims.append(None)  # 参考文献页无过渡
            else:
                slide_anims.append(transition_effects[i % len(transition_effects)])

        for idx, slide in enumerate(presentation.slides):
            layout_index = self.LAYOUTS.get(slide.layout, 1)
            try:
                slide_layout = prs.slide_layouts[layout_index]
            except IndexError:
                slide_layout = prs.slide_layouts[1]

            slide_obj = prs.slides.add_slide(slide_layout)
            slide_num = idx + 1  # 使用 1-based 索引

            # 1) 先铺背景与装饰（内容感知，置底，不遮挡正文）
            self._apply_background(slide_obj, theme, slide)

            # 2) 标题
            if slide.layout == "title_slide":
                self._set_title_cover(slide_obj, slide.title, theme)
            else:
                self._set_title(slide_obj, slide.title, theme)

            # 3) 是否有可用插图
            image_path = slide.image_path
            has_image = bool(image_path) and os.path.exists(image_path)

            # 重置正文注册表（每页独立）
            self._content_registry = []

            # 4) 正文内容（带动画）
            if slide.layout == "title_slide":
                self._set_subtitle(slide_obj, slide.detail, theme)
            elif slide.layout == "references":
                self._fill_references(slide_obj, slide, theme)
            elif slide.layout == "two_content":
                self._fill_two_content(slide_obj, slide, theme, has_image)
            else:
                self._fill_content(slide_obj, slide, theme, has_image)

            # 5) 插图（图文混排，带描边，布局多样化）
            if has_image:
                self._add_image(slide_obj, image_path, theme, slide.image_layout)

            # 5.5) 正文自适应：按最终几何重新计算字号，确保文字不溢出屏幕
            self._fit_registered_text()

            # 6) 为整页添加出现动画（标题 → 正文 → 图片，构造合法 timing 树）
            self._add_slide_animations(slide_obj, slide, slide_num, has_image)

            # 7) 备注（演讲者提词）
            if slide.notes:
                try:
                    slide_obj.notes_slide.notes_text_frame.text = slide.notes
                except Exception as e:
                    logger.warning("第 %d 页备注写入失败: %s", slide_num, e)

            # 8) 页面切换动画（非封面、非参考文献页）
            if slide_anims[idx]:
                self._add_slide_transition(slide_obj, slide_anims[idx], slide_num)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))
        return str(output_path)

    # ==================================================================
    # 内容感知：视觉参数推导
    # ==================================================================
    def _derive_slide_visual(self, slide: Slide) -> dict:
        """根据单页内容推导视觉参数：装饰母题、确定性种子、装饰密度。"""
        text = " | ".join(
            filter(None, [slide.title, slide.detail] + list(slide.points or []))
        )
        motif = self._classify_content(text)
        # 参考文献页固定学术母题，避免文献标题触发 data/tech 等语义不匹配的装饰
        if slide.layout == "references":
            motif = "academic"
        # 确定性哈希：同一内容 → 同一种子 → 背景稳定可复现
        digest = hashlib.md5((text or "empty").encode("utf-8")).hexdigest()
        seed = int(digest[:8], 16)
        # 密度：要点越多装饰越少（避免视觉拥挤）
        density = max(0.45, 1.0 - len(slide.points or []) * 0.13)
        return {"motif": motif, "seed": seed, "density": density}

    def _classify_content(self, text: str) -> str:
        """关键词匹配装饰母题；无匹配返回默认几何母题。"""
        if not text:
            return "geo"
        low = text.lower()
        for motif, keywords in self.MOTIF_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in low:
                    return motif
        return "geo"

    # ==================================================================
    # 背景与装饰（内容感知）
    # ==================================================================
    def _apply_background(self, slide_obj, theme, slide):
        """铺内容感知背景：主题色渐变 + 随内容变化的装饰母题 + 页脚。

        视觉差异来源：
        1. 关键词 → 装饰母题（柱状图/节点/路径/书页/几何圆）
        2. 内容哈希 → 装饰位置、数量、尺寸、渐变角度、配色微调
        3. 封面页 vs 内容页 → 结构差异（对称 vs 右下主装饰）

        z-order 注意：`_send_to_back` 用 `insert(2)`，「后调用者更深」，
        故装饰先、页脚次、全屏背景最后，最终背景最底、装饰居中、文字最上。
        """
        try:
            visual = self._derive_slide_visual(slide)
            rng = random.Random(visual["seed"])
            deco_shapes = []

            if slide.layout == "title_slide":
                deco_shapes += self._deco_cover(slide_obj, theme, rng)
            else:
                deco_shapes += self._draw_frame(slide_obj, theme, rng)
                deco_shapes += self._draw_deco_motif(
                    slide_obj, theme, visual["motif"], rng, visual["density"]
                )
                deco_shapes += self._draw_minor_deco(
                    slide_obj, theme, rng, visual["density"]
                )

            footer = self._add_footer(slide_obj, theme)

            # 全屏渐变背景（角度随内容变化：封面固定垂直，内容页随机）
            bg = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, 0, 0, self.SLIDE_W, self.SLIDE_H
            )
            if slide.layout == "title_slide":
                angle = 5400000  # 垂直
            else:
                angle = rng.choice([5400000, 2700000, 8100000])
            self._set_gradient(bg, theme["bg_top"], theme["bg_bottom"], angle)
            bg.line.fill.background()

            # 统一置底：装饰先、页脚次、背景最后 → 背景最底、装饰居中、文字最上
            for shape in deco_shapes:
                if shape is not None:
                    self._send_to_back(shape)
            if footer is not None:
                self._send_to_back(footer)
            self._send_to_back(bg)
        except Exception as e:
            logger.warning("背景装饰绘制失败（不影响内容）: %s", e)

    def _draw_frame(self, slide_obj, theme, rng):
        """主题标识框架：顶部色带 + 左侧竖条（保持主题识别度）。"""
        shapes = []
        band = slide_obj.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, self.SLIDE_W, Inches(0.14)
        )
        band.fill.solid()
        band.fill.fore_color.rgb = self._rgb_to_color(theme["title_color"])
        band.line.fill.background()
        shapes.append(band)

        bar = slide_obj.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, Inches(0.14), Inches(0.14), Inches(7.36)
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = self._rgb_to_color(theme["title_color"])
        bar.line.fill.background()
        shapes.append(bar)
        return shapes

    def _deco_cover(self, slide_obj, theme, rng):
        """封面装饰：四角对称大几何（比内容页更华丽）。"""
        shapes = []
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        deco2 = self._shift_color(theme["deco2_color"], rng.randint(-10, 10))
        title_c = theme["title_color"]

        # 顶部主色带（封面版，更高）
        band = slide_obj.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, self.SLIDE_W, Inches(0.24)
        )
        band.fill.solid()
        band.fill.fore_color.rgb = self._rgb_to_color(title_c)
        band.line.fill.background()
        shapes.append(band)

        # 左下大圆（部分出血）
        c1 = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(-1.2), Inches(4.9), Inches(4.2), Inches(4.2)
        )
        c1.fill.solid()
        c1.fill.fore_color.rgb = self._rgb_to_color(deco)
        c1.line.fill.background()
        shapes.append(c1)

        # 右上大圆环
        ring = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(10.5), Inches(-1.3), Inches(4.0), Inches(4.0)
        )
        ring.fill.background()
        ring.line.color.rgb = self._rgb_to_color(deco2)
        ring.line.width = Pt(3.0)
        shapes.append(ring)

        # 右下小圆
        c2 = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(11.6), Inches(5.6), Inches(2.0), Inches(2.0)
        )
        c2.fill.solid()
        c2.fill.fore_color.rgb = self._rgb_to_color(deco2)
        c2.line.fill.background()
        shapes.append(c2)

        # 左上小圆环
        ring2 = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(0.7), Inches(0.55), Inches(1.1), Inches(1.1)
        )
        ring2.fill.background()
        ring2.line.color.rgb = self._rgb_to_color(deco)
        ring2.line.width = Pt(2.0)
        shapes.append(ring2)
        return shapes

    def _draw_deco_motif(self, slide_obj, theme, motif, rng, density):
        """右下主装饰母题，由关键词决定，返回形状列表。"""
        if motif == "data":
            return self._deco_data(slide_obj, theme, rng, density)
        if motif == "tech":
            return self._deco_tech(slide_obj, theme, rng, density)
        if motif == "flow":
            return self._deco_flow(slide_obj, theme, rng, density)
        if motif == "academic":
            return self._deco_academic(slide_obj, theme, rng, density)
        return self._deco_geo(slide_obj, theme, rng, density)

    def _deco_geo(self, slide_obj, theme, rng, density):
        """几何母题：大小圆 + 圆环。"""
        shapes = []
        deco = self._shift_color(theme["deco_color"], rng.randint(-18, 18))
        deco2 = self._shift_color(theme["deco2_color"], rng.randint(-12, 12))
        big = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(rng.uniform(10.0, 11.2)),
            Inches(rng.uniform(5.0, 5.6)),
            Inches(rng.uniform(2.6, 3.4)),
            Inches(rng.uniform(2.6, 3.4)),
        )
        big.fill.solid()
        big.fill.fore_color.rgb = self._rgb_to_color(deco)
        big.line.fill.background()
        shapes.append(big)

        mid = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(rng.uniform(8.9, 9.9)),
            Inches(rng.uniform(6.0, 6.6)),
            Inches(rng.uniform(1.2, 1.8)),
            Inches(rng.uniform(1.2, 1.8)),
        )
        mid.fill.solid()
        mid.fill.fore_color.rgb = self._rgb_to_color(deco2)
        mid.line.fill.background()
        shapes.append(mid)

        if density > 0.55:
            ring = slide_obj.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(rng.uniform(11.4, 12.4)),
                Inches(rng.uniform(4.7, 5.2)),
                Inches(1.2), Inches(1.2),
            )
            ring.fill.background()
            ring.line.color.rgb = self._rgb_to_color(deco)
            ring.line.width = Pt(2.0)
            shapes.append(ring)
        return shapes

    def _deco_data(self, slide_obj, theme, rng, density):
        """数据母题：柱状图 + 上升箭头。"""
        shapes = []
        accent = self._shift_color(theme["accent_color"], rng.randint(-15, 15))
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        n = rng.randint(3, 4)
        base_x = 10.5
        base_y = 6.5
        for i in range(n):
            h = rng.uniform(0.6, 1.9)
            bar = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(base_x + i * 0.45),
                Inches(base_y - h),
                Inches(0.26), Inches(h),
            )
            bar.fill.solid()
            bar.fill.fore_color.rgb = self._rgb_to_color(accent if i % 2 else deco)
            bar.line.fill.background()
            shapes.append(bar)
        arrow = slide_obj.shapes.add_shape(
            MSO_SHAPE.UP_ARROW,
            Inches(base_x - 0.55), Inches(4.75), Inches(0.7), Inches(1.6),
        )
        arrow.fill.solid()
        arrow.fill.fore_color.rgb = self._rgb_to_color(accent)
        arrow.line.fill.background()
        shapes.append(arrow)
        return shapes

    def _deco_tech(self, slide_obj, theme, rng, density):
        """技术母题：节点网格 + 大圆环。"""
        shapes = []
        accent = self._shift_color(theme["accent_color"], rng.randint(-15, 15))
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        rows = 3
        cols = rng.randint(3, 4)
        start_x = 10.7
        start_y = 5.3
        for r in range(rows):
            for c in range(cols):
                dot = slide_obj.shapes.add_shape(
                    MSO_SHAPE.OVAL,
                    Inches(start_x + c * 0.42),
                    Inches(start_y + r * 0.42),
                    Inches(0.15), Inches(0.15),
                )
                dot.fill.solid()
                dot.fill.fore_color.rgb = self._rgb_to_color(accent)
                dot.line.fill.background()
                shapes.append(dot)
        ring = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(11.5), Inches(4.8), Inches(1.7), Inches(1.7),
        )
        ring.fill.background()
        ring.line.color.rgb = self._rgb_to_color(deco)
        ring.line.width = Pt(2.5)
        shapes.append(ring)
        return shapes

    def _deco_flow(self, slide_obj, theme, rng, density):
        """流程母题：路径节点 + 连线（折线走向）。"""
        shapes = []
        accent = self._shift_color(theme["accent_color"], rng.randint(-15, 15))
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        pts = [
            (9.8, 6.4), (10.9, 5.7), (12.0, 6.0),
        ]
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            seg_w = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            seg = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(min(x1, x2)), Inches(min(y1, y2) - 0.03),
                Inches(seg_w), Inches(0.06),
            )
            seg.fill.solid()
            seg.fill.fore_color.rgb = self._rgb_to_color(accent)
            seg.line.fill.background()
            shapes.append(seg)
        for x, y in pts:
            dot = slide_obj.shapes.add_shape(
                MSO_SHAPE.OVAL,
                Inches(x - 0.12), Inches(y - 0.12), Inches(0.24), Inches(0.24),
            )
            dot.fill.solid()
            dot.fill.fore_color.rgb = self._rgb_to_color(accent)
            dot.line.fill.background()
            shapes.append(dot)
        return shapes

    def _deco_academic(self, slide_obj, theme, rng, density):
        """学术母题：平行书页线。"""
        shapes = []
        accent = self._shift_color(theme["accent_color"], rng.randint(-15, 15))
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        n = rng.randint(3, 5)
        for i in range(n):
            ln = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(10.2), Inches(5.5 + i * 0.35),
                Inches(rng.uniform(1.6, 2.6)), Inches(0.07),
            )
            ln.fill.solid()
            ln.fill.fore_color.rgb = self._rgb_to_color(accent if i == 0 else deco)
            ln.line.fill.background()
            shapes.append(ln)
        return shapes

    def _draw_minor_deco(self, slide_obj, theme, rng, density):
        """次要装饰：左上/右上小圆，位置由内容种子决定。"""
        shapes = []
        if density < 0.55:
            return shapes
        deco = self._shift_color(theme["deco_color"], rng.randint(-15, 15))
        if rng.random() < 0.5:
            x = rng.uniform(0.35, 0.9)
        else:
            x = rng.uniform(12.1, 12.7)
        y = rng.uniform(0.35, 1.0)
        dot = slide_obj.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(0.34), Inches(0.34)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = self._rgb_to_color(deco)
        dot.line.fill.background()
        shapes.append(dot)
        return shapes

    def _add_footer(self, slide_obj, theme):
        """底部页脚：左「AutoSlide」水印。返回文本框以便统一置底。
        注意：默认不显示水印（用户要求无水印），如需启用请取消注释。
        """
        # 水印功能已禁用
        return None
        try:
            box = slide_obj.shapes.add_textbox(
                Inches(0.7), Inches(6.95), Inches(4.0), Inches(0.25)
            )
            tf = box.text_frame
            tf.word_wrap = False
            p = tf.paragraphs[0]
            p.text = "AutoSlide"
            p.font.size = Pt(10)
            p.font.color.rgb = self._rgb_to_color(theme["accent_color"])
            return box
        except Exception as e:
            logger.debug("页脚水印写入失败: %s", e)
            return None

    def _set_gradient(self, shape, color_top, color_bottom, angle=5400000):
        """给形状设置线性渐变填充（纯 XML，兼容性好）。angle 单位 1/60000 度。"""
        spPr = shape._element.spPr
        if spPr is None:
            return
        # 移除既有填充，避免叠加
        for tag in ("a:solidFill", "a:gradFill", "a:noFill",
                    "a:blipFill", "a:pattFill", "a:grpFill"):
            for el in spPr.findall(qn(tag)):
                spPr.remove(el)

        gradFill = etree.SubElement(spPr, qn("a:gradFill"))
        gradFill.set("rotWithShape", "1")
        gsLst = etree.SubElement(gradFill, qn("a:gsLst"))

        gs0 = etree.SubElement(gsLst, qn("a:gs"))
        gs0.set("pos", "0")
        c0 = etree.SubElement(gs0, qn("a:srgbClr"))
        c0.set("val", "%02X%02X%02X" % color_top)

        gs1 = etree.SubElement(gsLst, qn("a:gs"))
        gs1.set("pos", "100000")
        c1 = etree.SubElement(gs1, qn("a:srgbClr"))
        c1.set("val", "%02X%02X%02X" % color_bottom)

        lin = etree.SubElement(gradFill, qn("a:lin"))
        lin.set("ang", str(angle))
        lin.set("scaled", "1")

    def _send_to_back(self, shape):
        """将形状移动到形状树最底层（不遮挡占位符文本）。"""
        try:
            sp = shape._element
            spTree = sp.getparent()
            spTree.remove(sp)
            spTree.insert(2, sp)
        except Exception as e:
            logger.debug("置底失败: %s", e)

    @staticmethod
    def _shift_color(rgb, delta):
        """RGB 元组做细微偏移，用于每页配色微调。"""
        return tuple(max(0, min(255, c + delta)) for c in rgb)

    # ==================================================================
    # 标题
    # ==================================================================
    def _set_title(self, slide_obj, title, theme):
        """内容页标题：加粗主色 + 左对齐 + 标题下装饰线。

        显式设定几何（左右 0.7" 边距、顶部 0.45"），覆盖模板默认的
        0.5"/0.3" 贴边位置，保证标题不贴画面边缘。
        """
        title_box = slide_obj.shapes.title
        if title_box is None:
            title_box = slide_obj.shapes.add_textbox(
                Inches(0.7), Inches(0.45), Inches(11.9), Inches(0.95)
            )
        else:
            title_box.left = Inches(0.7)
            title_box.top = Inches(0.45)
            title_box.width = Inches(11.9)
            title_box.height = Inches(0.95)
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title
        # 按标题长度自适应字号，防止长标题换行后越出标题区
        title_len = len(title or "")
        if title_len > 40:
            p.font.size = Pt(22)
        elif title_len > 30:
            p.font.size = Pt(26)
        elif title_len > 20:
            p.font.size = Pt(30)
        else:
            p.font.size = Pt(34)
        p.font.bold = True
        p.font.color.rgb = self._rgb_to_color(theme["title_color"])
        p.alignment = PP_ALIGN.LEFT
        self._add_title_line(slide_obj, title_box, theme)

    def _set_title_cover(self, slide_obj, title, theme):
        """封面标题：居中大字号 + 居中装饰线。"""
        title_box = slide_obj.shapes.title
        if title_box is None:
            title_box = slide_obj.shapes.add_textbox(
                Inches(1.0), Inches(2.2), Inches(11.3), Inches(1.8)
            )
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.clear()
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(46)
        p.font.bold = True
        p.font.color.rgb = self._rgb_to_color(theme["title_color"])
        p.alignment = PP_ALIGN.CENTER
        # 封面装饰线（居中，稍宽）
        try:
            line = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE,
                Inches(5.17), Inches(4.1), Inches(3.0), Inches(0.06),
            )
            line.fill.solid()
            line.fill.fore_color.rgb = self._rgb_to_color(theme["accent_color"])
            line.line.fill.background()
        except Exception as e:
            logger.debug("封面装饰线绘制失败: %s", e)

    def _add_title_line(self, slide_obj, title_box, theme):
        """标题下方一条主题色装饰短线。"""
        try:
            top = title_box.top + title_box.height - Inches(0.08)
            line = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, Inches(0.72), top, Inches(2.2), Inches(0.06)
            )
            line.fill.solid()
            line.fill.fore_color.rgb = self._rgb_to_color(theme["accent_color"])
            line.line.fill.background()
        except Exception as e:
            logger.debug("标题装饰线绘制失败: %s", e)

    def _set_subtitle(self, slide_obj, subtitle, theme):
        """封面副标题（detail 作为副标题）。"""
        if not subtitle:
            return
        box = slide_obj.shapes.add_textbox(
            Inches(1.0), Inches(4.35), Inches(11.3), Inches(1.8)
        )
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = subtitle
        # 副标题按长度自适应，防止长文本越出文本框
        sub_len = len(subtitle or "")
        if sub_len > 120:
            p.font.size = Pt(14)
        elif sub_len > 70:
            p.font.size = Pt(17)
        else:
            p.font.size = Pt(20)
        p.font.color.rgb = self._rgb_to_color(theme["accent_color"])
        p.alignment = PP_ALIGN.CENTER

    # ==================================================================
    # 正文内容
    # ==================================================================
    def _content_textbox(self, slide_obj, has_image, register=True):
        """创建正文文本框，返回 text_frame；有插图时正文占据左侧。

        register=True 时登记到 _content_registry，插图插入后统一调整几何与字号。
        几何遵循安全边距：左右 0.7"、顶部 1.5"、底部留 0.55"（不贴画面边缘）。
        """
        if has_image:
            box = slide_obj.shapes.add_textbox(
                Inches(0.7), Inches(1.5), Inches(7.2), Inches(5.45)
            )
        else:
            box = slide_obj.shapes.add_textbox(
                Inches(0.7), Inches(1.5), Inches(11.9), Inches(5.45)
            )
        tf = box.text_frame
        tf.word_wrap = True
        if register:
            self._content_registry.append({
                "box": box, "tf": tf, "detail": "", "points": [], "theme": None,
            })
        return tf

    def _fill_content(self, slide_obj, slide, theme, has_image):
        """单栏内容：详细正文段落 + 要点列表。"""
        tf = self._content_textbox(slide_obj, has_image)
        if self._content_registry:
            self._content_registry[-1].update({
                "detail": slide.detail or "",
                "points": list(slide.points or []),
                "theme": theme,
            })
        self._write_body(tf, slide.detail, slide.points, theme)

    def _fill_references(self, slide_obj, slide, theme):
        """参考文献页：逐条编号、小字号常规排版（区别于要点页）。

        动态字号：条目多或单条长时缩小，避免文本框纵向溢出。
        """
        tf = self._content_textbox(slide_obj, has_image=False, register=False)
        tf.clear()
        items = slide.points or []
        max_len = max((len(item) for item in items), default=0)
        if len(items) > 8 or max_len > 90:
            size = Pt(10)
        elif len(items) > 5 or max_len > 60:
            size = Pt(12)
        else:
            size = Pt(13)
        for i, item in enumerate(items, 1):
            p = tf.paragraphs[0] if i == 1 else tf.add_paragraph()
            p.text = f"[{i}] {item}"
            p.font.size = size
            p.font.bold = False
            p.font.color.rgb = self._rgb_to_color(theme["text_color"])
            p.space_after = Pt(8)
            p.line_spacing = 1.15

    def _fill_two_content(self, slide_obj, slide, theme, has_image=False):
        """双栏内容：左栏正文+前半要点，右栏后半要点（对比/并列）。

        has_image 时两栏最终几何由 _adjust_textbox_for_image 在插图插入后
        按图片实际位置统一划分（支持 left/right/top 任意布局），避免重叠。
        """
        boxes = []
        for shape in slide_obj.shapes:
            if not shape.is_placeholder:
                continue
            t = shape.placeholder_format.type
            if t in (PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT):
                boxes.append(shape)
        if len(boxes) < 2:
            # 布局退化：仅一个内容区，按单栏处理（透传 has_image）
            self._fill_content(slide_obj, slide, theme, has_image)
            return

        left, right = boxes[0], boxes[1]
        # 按视觉位置显式排序左/右栏，不依赖占位符在 XML 中的出现顺序
        try:
            boxes.sort(key=lambda s: (s.left, s.top))
            left, right = boxes[0], boxes[1]
        except Exception:
            pass
        # 无图双栏：显式设为安全区几何（左右 0.7" 边距、底部 0.55"），
        # 替换模板默认的 0.5" 边距与不对称布局；有图时由
        # _adjust_textbox_for_image 按图片实际位置重新划分
        if not has_image:
            region_x, region_y = 0.7, 1.5
            region_w = 13.333 - 0.7 * 2  # 11.933：与单栏/标题区宽度约定一致
            region_h = 5.45
            col_gap = 0.4
            col_w = (region_w - col_gap) / 2
            for i, b in enumerate((left, right)):
                b.left = Inches(region_x + i * (col_w + col_gap))
                b.top = Inches(region_y)
                b.width = Inches(col_w)
                b.height = Inches(region_h)
        for b in (left, right):
            b.text_frame.word_wrap = True
            # 登记到注册表：插图插入后统一调整几何，正文写入后统一自适应字号
            self._content_registry.append({
                "box": b, "tf": b.text_frame, "detail": "", "points": [], "theme": theme,
            })

        half = (len(slide.points) + 1) // 2
        left_points = slide.points[:half]
        right_points = slide.points[half:]

        self._content_registry[0].update({
            "detail": slide.detail or "", "points": left_points,
        })
        self._content_registry[1].update({
            "detail": "", "points": right_points,
        })

        self._write_body(left.text_frame, slide.detail, left_points, theme)
        self._write_body(right.text_frame, "", right_points, theme)

    def _write_body(self, tf, detail, points, theme, scale=1.0, compact=False):
        """写入正文：可选的详细段落 + 要点列表。

        scale 为字号缩放系数（0.5~1.0），由 _fit_registered_text 按内容量计算。
        compact=True 时启用紧凑排版（缩小段后距与行距），用于极端内容量兜底。
        """
        tf.clear()
        d_size = max(10, int(16 * scale))
        p_size = max(11, int(18 * scale))
        if compact:
            d_after, p_after, d_ls, p_ls = 8, 5, 1.15, 1.05
        else:
            d_after, p_after, d_ls, p_ls = 14, 10, 1.3, 1.2
        first = True
        if detail:
            p = tf.paragraphs[0]
            p.text = detail
            p.font.size = Pt(d_size)
            p.font.color.rgb = self._rgb_to_color(theme["text_color"])
            p.space_after = Pt(d_after)
            p.line_spacing = d_ls
            first = False
        for point in points:
            p = tf.paragraphs[0] if first else tf.add_paragraph()
            first = False
            p.text = f"• {point}"
            p.font.size = Pt(p_size)
            p.font.bold = True
            p.font.color.rgb = self._rgb_to_color(theme["accent_color"])
            p.space_after = Pt(p_after)
            p.line_spacing = p_ls

    # ==================================================================
    # 插图布局多样化
    # ==================================================================
    def _add_image(self, slide_obj, image_path, theme, layout_mode="right"):
        """在幻灯片插入插图，支持多种布局模式

        layout_mode 选项：
        - "right"（默认）：图片在右侧
        - "left"：图片在左侧
        - "top"：图片在上方，文字在下方
        - "fullscreen"：图片铺满全屏作为背景（不叠加正文）
        """
        try:
            if not os.path.exists(image_path):
                logger.warning("插图文件不存在: %s", image_path)
                return

            # 全图模式：图片作为背景，不叠加正文
            if layout_mode == "fullscreen":
                self._add_fullscreen_image(slide_obj, image_path, theme)
                return

            # 获取图片实际尺寸
            img_width, img_height = self._get_image_dimensions(image_path)
            if img_width == 0 or img_height == 0:
                logger.warning("无法获取图片尺寸: %s", image_path)
                return

            img_ratio = img_width / img_height

            # 根据布局模式和图片比例计算最优尺寸
            left, top, width, height = self._calc_image_position(img_ratio, layout_mode)

            pic = slide_obj.shapes.add_picture(image_path, left, top, width=width, height=height)

            # 零裁剪：生成端按框比例精确出图，横幅高度随图片比例自适应后
            # 残余偏差 <1% 视为原比例显示，不裁剪；偏差较大（API 回退尺寸）
            # 才做 cover-fit 居中裁切兜底，避免拉伸变形
            if layout_mode in ("top", "bottom"):
                target_ratio = width.inches / height.inches
                if abs(img_ratio - target_ratio) / target_ratio > 0.01:
                    self._apply_cover_crop(pic, target_ratio, img_ratio)

            # bottom 通栏横幅会盖住页脚水印，将页脚上移到横幅上方
            if layout_mode == "bottom":
                self._relocate_footer_above(slide_obj, top.inches)
            try:
                pic.line.color.rgb = self._rgb_to_color(theme["accent_color"])
                pic.line.width = Pt(1.25)
            except Exception:
                pass

            # 根据布局调整文本框位置
            self._adjust_textbox_for_image(slide_obj, layout_mode, pic)
        except Exception as e:
            logger.warning("插图插入失败 [%s]（%s）: %s", layout_mode, image_path, e)

    def _get_image_dimensions(self, image_path):
        """获取图片的实际尺寸（像素）"""
        try:
            with Image.open(image_path) as img:
                return img.size  # (width, height)
        except Exception as e:
            logger.warning("读取图片尺寸失败: %s", e)
            return (1024, 768)  # 默认16:10比例

    def _calc_image_position(self, img_ratio, layout_mode):
        """根据图片比例和布局模式计算最优位置和尺寸

        目标：图片保持原始比例，视觉平衡，留出足够文字空间。
        关键约束：图片顶边不得高于 1.45"（避开标题区 0.4~1.35"），
        底边不得低于 7.1"（仅 right/left 分支；top/bottom 横幅由
        BANNER_BOTTOM_MARGIN 单独控制底边距），左右不越出边距。
        """
        slide_h = 7.5  # 幻灯片高度
        slide_w = 13.333  # 幻灯片宽度
        padding = 0.3  # 边距
        title_zone_bottom = 1.45  # 标题区下界（含装饰线）
        bottom_limit = 7.1  # 仅约束 right/left 分支（top/bottom 横幅豁免）

        if layout_mode == "left":
            # 左侧模式：图片靠左，最大宽度4.5英寸
            max_width_inches = 4.5
            if img_ratio >= 1:  # 宽图或方形
                width = Inches(max_width_inches)
                height = Inches(max_width_inches / img_ratio)
            else:  # 高图
                height = Inches(min(5.3, bottom_limit - title_zone_bottom))
                width = Inches(height.inches * img_ratio)
            left = Inches(padding)
            top = Inches(max(title_zone_bottom, (slide_h - height.inches) / 2))

        elif layout_mode in ("top", "bottom"):
            # 顶部/底部模式：横幅带默认与正文 0.7" 边距对齐（band_w_max）。
            # 零裁剪策略：生成端按 BANNER_FRAME_RATIO 精确出图 → 横幅保持
            # 标准几何（11.93×2.4"）、图片原比例完整显示；图片比例偏离框比例时
            # （API 回退尺寸等），横幅高度先自适应（钳制 H_MIN~H_MAX）、
            # 宽度随之贴合图片原比例（钳制 W_MIN，居中收窄），双维容纳时零裁剪；
            # 极端比例残余偏差 <1% 不裁剪，否则 cover-fit 居中裁切兜底防拉伸。
            band_w_max = slide_w - 1.4  # 左右各留 0.7" 边距
            banner_bottom_margin = self.BANNER_BOTTOM_MARGIN  # bottom 横幅不贴画面底端
            band_w, band_h = band_w_max, self.BANNER_BAND_H
            if img_ratio > 0:
                h_fit = min(self.BANNER_BAND_H_MAX,
                            max(self.BANNER_BAND_H_MIN, band_w_max / img_ratio))
                w_fit = h_fit * img_ratio
                band_w = min(band_w_max, max(self.BANNER_BAND_W_MIN, w_fit))
                band_h = min(self.BANNER_BAND_H_MAX,
                             max(self.BANNER_BAND_H_MIN, band_w / img_ratio))
            width = Inches(band_w)
            height = Inches(band_h)
            # 横幅收窄时在带区内水平居中
            left = Inches(0.7 + (band_w_max - band_w) / 2)
            if layout_mode == "top":
                top = Inches(title_zone_bottom)
            else:  # bottom：近底横幅（底边距画面底端 0.35"）
                top = Inches(slide_h - band_h - banner_bottom_margin)

        else:  # right (default)
            # 右侧模式：图片靠右，最大宽度4.5英寸
            max_width_inches = 4.5
            if img_ratio >= 1:  # 宽图或方形
                width = Inches(max_width_inches)
                height = Inches(max_width_inches / img_ratio)
            else:  # 高图
                height = Inches(min(5.3, bottom_limit - title_zone_bottom))
                width = Inches(height.inches * img_ratio)
            left = Inches(slide_w - width.inches - padding)
            top = Inches(max(title_zone_bottom, (slide_h - height.inches) / 2))

        # 兜底：高度不得使图片越出下边界（同时保证图片最小高度 1.2"，
        # 避免极端比例下图片被压成细线）。
        # top/bottom 横幅带由 cover-fit 裁切控制比例，豁免此约束。
        if layout_mode not in ("top", "bottom"):
            avail_h_in = bottom_limit - top.inches
            if avail_h_in < 1.2:
                top = Inches(max(title_zone_bottom, bottom_limit - 1.2))
                avail_h_in = bottom_limit - top.inches
            if top.inches + height.inches > bottom_limit or height.inches > avail_h_in:
                height = Inches(avail_h_in)
                width = Inches(avail_h_in * img_ratio)

        return left, top, width, height

    @staticmethod
    def _apply_cover_crop(pic, target_ratio, img_ratio):
        """cover-fit 裁切：让图片铺满目标区域且不变形。

        图片比目标更宽 → 左右居中裁切；更高 → 上下居中裁切。
        crop 值为单边裁掉的比例（0~1）。
        """
        try:
            if img_ratio > target_ratio:
                total = 1.0 - target_ratio / img_ratio
                pic.crop_left = total / 2
                pic.crop_right = total / 2
            elif img_ratio < target_ratio:
                total = 1.0 - img_ratio / target_ratio
                pic.crop_top = total / 2
                pic.crop_bottom = total / 2
        except Exception as e:
            logger.debug("cover-fit 裁切失败（保持拉伸显示）: %s", e)

    @staticmethod
    def _relocate_footer_above(slide_obj, band_top_inches):
        """将页脚水印移到底部横幅上方，避免被通栏图片盖住。"""
        for shape in slide_obj.shapes:
            try:
                if shape.has_text_frame and shape.text_frame.text.strip() == "AutoSlide":
                    # 偏移 0.5"：保证页脚顶边与正文文字区底边留出 ~0.22" 间隙（F-23-05）
                    shape.top = Inches(band_top_inches - 0.5)
            except Exception:
                continue

    def _add_fullscreen_image(self, slide_obj, image_path, theme):
        """全图模式：图片铺满全屏作为背景（cover-fit 居中裁切，不拉伸变形）"""
        try:
            pic = slide_obj.shapes.add_picture(
                image_path, 0, 0, self.SLIDE_W, self.SLIDE_H
            )
            # 非全屏比例的图片按 16:9 居中裁切，避免拉伸变形
            try:
                img_w, img_h = self._get_image_dimensions(image_path)
                if img_w > 0 and img_h > 0:
                    self._apply_cover_crop(pic, self.SLIDE_W / self.SLIDE_H, img_w / img_h)
            except Exception:
                pass
            # 设置半透明蒙层让文字更清晰
            try:
                spPr = pic._element.spPr
                for blip in spPr.findall(qn("a:blip")):
                    alpha = etree.SubElement(blip, qn("a:alpha"))
                    alpha.set("val", "200000")  # 约31%透明度
            except Exception:
                pass
            # 添加文字蒙层
            overlay = slide_obj.shapes.add_shape(
                MSO_SHAPE.RECTANGLE, 0, 0, self.SLIDE_W, self.SLIDE_H
            )
            overlay.fill.solid()
            overlay.fill.fore_color.rgb = RGBColor(0, 0, 0)
            overlay.line.fill.background()
            try:
                spPr = overlay._element.spPr
                cnvPr = etree.SubElement(spPr, qn("a:solidFill"))
                srgb = etree.SubElement(cnvPr, qn("a:srgbClr"))
                srgb.set("val", "000000")
                alpha = etree.SubElement(srgb, qn("a:alpha"))
                alpha.set("val", "40000")  # 25%不透明度
            except Exception:
                pass
            # 将图片置底
            self._send_to_back(pic)
            self._send_to_back(overlay)
            logger.info("全图背景模式已应用")
        except Exception as e:
            logger.warning("全图背景插入失败: %s", e)

    @staticmethod
    def _estimate_natural_width(detail, points):
        """估算正文块的自然宽度（各段不换行时的最大行宽，英寸）。

        中文按字宽 ≈ 0.82×字号、ASCII ≈ 0.55×字号 估算，
        用于判断内容是否稀疏（自然宽度远小于文字区宽度）。
        """
        def line_w(text, size):
            if not text:
                return 0.0
            cjk = sum(1 for ch in text if ord(ch) > 0x2E80)
            asc = len(text) - cjk
            return (cjk * 0.82 + asc * 0.55) * size / 72.0

        widths = []
        if detail:
            widths.append(line_w(detail, 16))
        for p in points or []:
            widths.append(line_w("• " + str(p), 18))
        return max(widths) if widths else 0.0

    def _grow_image_for_sparse_content(self, layout_mode, pic, img_left, img_top,
                                        img_width, img_height, region_w):
        """稀疏内容时放大插图，填补文字与图片之间的中部留白。

        仅作用于 right/left 单栏场景：当正文自然宽度远小于文字区时，
        图片在锚点（right 保持右边缘 / left 保持左边缘）与比例不变的前提下
        向文字侧扩展，最多到 5.6 英寸宽。返回更新后的图片矩形。
        """
        natural_w = 0.0
        entries = [e for e in self._content_registry if e.get("box") is not None]
        if len(entries) == 1:
            natural_w = self._estimate_natural_width(
                entries[0].get("detail"), entries[0].get("points")
            )
        # 非稀疏（自然宽度接近文字区）或无双栏场景不放大
        if natural_w <= 0 or region_w - natural_w <= 1.0:
            return img_left, img_top, img_width, img_height

        extra = min(1.1, (region_w - natural_w - 0.4) * 0.5)
        new_w = min(img_width + extra, 5.6)
        ratio = img_width / img_height
        new_h = new_w / ratio
        if new_h > 5.5:  # 高度约束：不越出标题区与底边距
            new_h = 5.5
            new_w = new_h * ratio
        if layout_mode == "right":
            new_left = img_left + (img_width - new_w)  # 右边缘锚定
        else:
            new_left = img_left  # 左边缘锚定
        new_top = max(1.45, (7.5 - new_h) / 2)
        if new_top + new_h > 7.1:
            new_top = 7.1 - new_h
        try:
            pic.left, pic.top = Inches(new_left), Inches(new_top)
            pic.width, pic.height = Inches(new_w), Inches(new_h)
        except Exception as e:
            logger.debug("稀疏内容放大插图失败（保持原尺寸）: %s", e)
            return img_left, img_top, img_width, img_height
        return new_left, new_top, new_w, new_h

    def _adjust_textbox_for_image(self, slide_obj, layout_mode, pic=None):
        """根据图片实际占据的矩形，计算安全文字区并应用到所有正文框。

        关键修复：
        1. 同时覆盖 add_textbox 创建的正文框和 BODY/OBJECT 占位符
           （旧版只调整占位符，导致单栏正文在 left/top 模式下压在图片上）。
        2. 双栏正文在文字区内均分，不再互相重叠。
        3. 图片矩形来自 pic 实际位置（含 top 模式避开标题区后的偏移）。
        """
        if pic is not None:
            img_left = pic.left.inches
            img_top = pic.top.inches
            img_width = pic.width.inches
            img_height = pic.height.inches
        else:
            img_left, img_top, img_width, img_height = 8.5, 1.5, 4.5, 4.5

        slide_w, slide_h = 13.333, 7.5
        # 图文间距：right/left 模式下文字区边缘与图片边缘的最小距离。
        # right 模式文字区右边界 = 图片左边缘 - gap（有意设计，非侧边距）；
        # top 模式垂直间距另行取 0.25。
        gap = 0.4
        margin_bottom = 0.55  # 底部安全边距：文字区底边不贴画面边缘
        margin_side = 0.5  # 文字区远端侧边距

        # 稀疏内容均衡：right/left 单栏且正文较少时，先放大插图填补中部留白
        if layout_mode in ("right", "left") and pic is not None:
            region_w_now = (
                (img_left - gap - 0.7) if layout_mode == "right"
                else (slide_w - img_left - img_width - gap - margin_side)
            )
            (img_left, img_top, img_width, img_height) = (
                self._grow_image_for_sparse_content(
                    layout_mode, pic, img_left, img_top,
                    img_width, img_height, region_w_now,
                )
            )

        # 计算安全文字区 (x, y, w, h)
        if layout_mode == "left":
            region_x = img_left + img_width + gap
            region = (region_x, 1.5, slide_w - region_x - margin_side,
                      slide_h - 1.5 - margin_bottom)
        elif layout_mode == "top":
            region_y = img_top + img_height + 0.25
            region = (0.7, region_y, slide_w - 1.4, slide_h - region_y - margin_bottom)
        elif layout_mode == "bottom":
            # 图片为底部通栏横幅，文字区在标题与横幅之间
            # 关键修复：使用 img_top - 1.5 - 0.25（与 top 对称），
            # 确保文字区与横幅之间有足够间距；区域高度兜底 ≥ 1.8"。
            region_h = max(1.8, img_top - 1.5 - 0.25)
            region = (0.7, 1.5, slide_w - 1.4, region_h)
        else:  # right
            # region_w 由文字区左边距 0.7 与图文间距 gap 推导：
            # 文字区右边界 = img_left - gap，与图片保持 gap 间距
            region_w = img_left - gap - 0.7
            region = (0.7, 1.5, region_w, slide_h - 1.5 - margin_bottom)

        # 兜底：文字区过窄时压缩到最小可用宽度
        region = (
            region[0], region[1],
            max(3.0, region[2]),
            max(1.5, region[3]),
        )

        # 收集需要调整的正文框：注册表优先，再补充占位符。
        # 注意：python-pptx 每次迭代 shapes 都会生成新代理对象，
        # 必须按底层 lxml 元素去重，否则同一形状会被重复计入导致多栏错分。
        target_boxes = []
        seen = set()

        def _element_key(shape):
            try:
                return id(shape._element)
            except Exception:
                return id(shape)

        for entry in self._content_registry:
            b = entry["box"]
            if b is not None and _element_key(b) not in seen:
                target_boxes.append(b)
                seen.add(_element_key(b))
        for shape in slide_obj.shapes:
            try:
                if not shape.is_placeholder:
                    continue
                if shape.placeholder_format.type not in (
                    PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT
                ):
                    continue
                # 跳过未写入内容的空占位符（模板自带 BODY 槽位），
                # 否则单栏正文会被误判为双栏拆分，文字被挤进半宽窄列
                if not (shape.has_text_frame and shape.text_frame.text.strip()):
                    continue
                if _element_key(shape) not in seen:
                    target_boxes.append(shape)
                    seen.add(_element_key(shape))
            except Exception:
                continue

        if not target_boxes:
            return

        n = len(target_boxes)
        if n == 1:
            b = target_boxes[0]
            box_top, box_h = region[1], region[3]
            # 稀疏内容垂直居中：估算正文实际高度，远小于文字区时将文字块
            # 居中放置，消除底部大片空白。高度留 0.35" 余量防止触发字号缩放。
            if layout_mode in ("right", "left") and len(self._content_registry) == 1:
                entry = self._content_registry[0]
                est_h = self._estimate_body_height(
                    entry.get("detail"), entry.get("points"),
                    region[2] - 0.3, 1.0,
                )
                if est_h > 0.5 and est_h < region[3] - 0.9:
                    new_h = min(region[3], est_h + 0.35)
                    box_top = region[1] + (region[3] - new_h) / 2
                    box_h = new_h
            b.left = Inches(region[0])
            b.top = Inches(box_top)
            b.width = Inches(region[2])
            b.height = Inches(box_h)
            b.text_frame.word_wrap = True
        else:
            # 多栏：在文字区内均分，栏间距 0.4"
            col_gap = 0.4
            col_w = (region[2] - col_gap * (n - 1)) / n
            for i, b in enumerate(target_boxes):
                b.left = Inches(region[0] + i * (col_w + col_gap))
                b.top = Inches(region[1])
                b.width = Inches(col_w)
                b.height = Inches(region[3])
                b.text_frame.word_wrap = True

    # ==================================================================
    # 正文自适应字号
    # ==================================================================
    def _estimate_body_height(self, detail, points, avail_w, scale, compact=False):
        """估算正文在给定字号缩放下所需的高度（英寸）。

        中文按字宽 ≈ 0.8×字号 估算每行字符数，保守取整保证不低估。
        compact 参数须与 _write_body 的紧凑参数保持一致。
        """
        d_size = max(10, int(16 * scale))
        p_size = max(11, int(18 * scale))
        if compact:
            d_after, p_after, d_ls, p_ls = 8, 5, 1.15, 1.05
        else:
            d_after, p_after, d_ls, p_ls = 14, 10, 1.3, 1.2

        def para_lines(text, size):
            if not text:
                return 0
            char_w = size / 72.0 * 0.8
            cpl = max(6, int(avail_w / char_w))
            return max(1, math.ceil(len(text) / cpl))

        total = 0.15  # 文本框内边距余量（含渲染误差预留）
        if detail:
            total += para_lines(detail, d_size) * d_size / 72.0 * d_ls + d_after / 72.0
        for point in points:
            total += para_lines("• " + point, p_size) * p_size / 72.0 * p_ls + p_after / 72.0
        return total

    def _fit_registered_text(self):
        """对注册表中所有正文框按最终几何做字号自适应，防止文字溢出屏幕。

        两级策略：
        1. 常规排版下逐级缩小字号（1.0 → 0.55）；
        2. 仍装不下则切换紧凑排版（缩小段后距/行距）再试；
        最后写入 normAutofit，由 PowerPoint 打开时进一步兜底微调。
        """
        ladder = (1.0, 0.92, 0.85, 0.78, 0.7, 0.62, 0.55)
        for entry in self._content_registry:
            box, tf = entry["box"], entry["tf"]
            theme = entry["theme"]
            if box is None or tf is None or theme is None:
                continue
            try:
                avail_w = box.width.inches - 0.3
                avail_h = box.height.inches - 0.25
            except Exception:
                continue
            if avail_w <= 0 or avail_h <= 0:
                continue

            chosen_scale, chosen_compact = 0.55, True  # 兜底：最小字号+紧凑
            found = False
            for compact in (False, True):
                for s in ladder:
                    if self._estimate_body_height(
                        entry["detail"], entry["points"], avail_w, s, compact
                    ) <= avail_h:
                        chosen_scale, chosen_compact = s, compact
                        found = True
                        break
                if found:
                    break

            # 仅当偏离默认排版时才重写，避免无谓的清空重填
            if chosen_scale < 1.0 or chosen_compact:
                self._write_body(
                    tf, entry["detail"], entry["points"], theme,
                    scale=chosen_scale, compact=chosen_compact,
                )
                # normAutofit 兜底：仅在内容确实超量时启用，
                # 避免与 word_wrap=True 在旧版 Office/WPS 下产生截断冲突
                try:
                    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
                except Exception:
                    pass

    # ==================================================================
    # 页面切换动画
    # ==================================================================
    # ==================================================================
    # 幻灯片切换动画（合法 OOXML：<p:transition> 直接作为 sld 子元素）
    # ==================================================================
    # 切换效果：元素名（无 Effect 后缀）→ 是否需要 dir 属性
    TRANSITION_SPECS = {
        "fade": ("fade", False),
        "push": ("push", True),
        "wipe": ("wipe", True),
        "dissolve": ("dissolve", False),
        "uncover": ("uncover", True),
        "cover": ("cover", True),
        "cut": ("cut", False),
    }

    def _add_slide_transition(self, slide_obj, effect, slide_num=0, spd="slow"):
        """添加合法的页面切换动画。

        正确结构（OOXML schema，元素顺序敏感）：
            <p:sld>...<p:transition spd="slow" advClick="1"><p:fade/></p:transition>...</p:sld>

        旧实现错误地套了一层 <p:sldTrans>，且效果元素名误加 Effect 后缀
        （<p:fadeEffect>），并用不存在的 <p:dur> 子元素控制时长——这些都不是
        PowerPoint schema 的元素，会被 PowerPoint 直接忽略。
        """
        try:
            spec = self.TRANSITION_SPECS.get(effect)
            if spec is None:
                return
            elem_name, need_dir = spec

            sld_el = slide_obj._element
            # 清理旧实现遗留的非法 <p:sldTrans>
            for old in sld_el.findall(f"{{{NS_NS}}}sldTrans"):
                sld_el.remove(old)
            # 已存在 transition 则先移除，避免重复叠加
            for old in sld_el.findall(f"{{{NS_NS}}}transition"):
                sld_el.remove(old)

            trans = etree.Element(f"{{{NS_NS}}}transition")
            trans.set("spd", spd)
            trans.set("advClick", "1")
            eff = etree.SubElement(trans, f"{{{NS_NS}}}{elem_name}")
            if need_dir:
                eff.set("dir", "l")

            # schema 顺序：cSld → clrMapOvr → transition → timing → extLst
            # 必须插在 timing 之前，否则 PowerPoint 判定结构非法
            timing = sld_el.find(f"{{{NS_NS}}}timing")
            if timing is not None:
                timing.addprevious(trans)
            else:
                sld_el.append(trans)

            logger.debug("第 %d 页添加切换动画: %s", slide_num, effect)
        except Exception as e:
            logger.warning("第 %d 页添加切换动画失败: %s", slide_num, e)

    # ==================================================================
    # 元素出现动画（合法 OOXML：<p:timing> 动画树）
    # ==================================================================
    # 入场效果预设（presetID 为 PowerPoint 标准值）
    ENTRANCE_PRESETS = {
        "fade": {"preset_id": 10, "filter": "fade", "subtype": 0, "dur": 500},
        "fly":  {"preset_id": 2,  "filter": "fly",  "subtype": 2, "dur": 500},
        "wipe": {"preset_id": 16, "filter": "wipe", "subtype": 1, "dur": 500},
        "zoom": {"preset_id": 19, "filter": "zoom", "subtype": 0, "dur": 600},
    }

    def _add_slide_animations(self, slide_obj, slide, slide_num=0, has_image=False):
        """为整页构造合法的 <p:timing> 动画树。

        播放顺序：标题 → 正文（逐框） → 图片。
        首个动画点击触发，其余在其后自动依次播放（afterEffect）。
        """
        try:
            title_spid = None
            body_spids = []
            pic_spid = None

            for shape in slide_obj.shapes:
                try:
                    spid = shape.shape_id
                except Exception:
                    continue
                is_pic = shape.shape_type == 13 or shape.__class__.__name__ == "Picture"
                if is_pic:
                    pic_spid = spid
                    continue
                if not (shape.has_text_frame and shape.text_frame.text.strip()):
                    continue
                is_title = False
                try:
                    if shape.is_placeholder and shape.placeholder_format.idx == 0:
                        is_title = True
                except Exception:
                    pass
                if is_title:
                    title_spid = spid
                else:
                    body_spids.append(spid)

            specs = []
            if title_spid is not None:
                specs.append((title_spid, "fade", "clickEffect", 0))
            for _spid in body_spids:
                specs.append((_spid, "fly", "afterEffect", 150))
            if pic_spid is not None:
                specs.append((pic_spid, "zoom", "afterEffect", 150))

            if not specs:
                return

            self._write_timing_tree(slide_obj, specs)
            logger.debug("第 %d 页添加 %d 个元素动画", slide_num, len(specs))
        except Exception as e:
            logger.warning("第 %d 页添加元素动画失败: %s", slide_num, e)

    def _write_timing_tree(self, slide_obj, specs):
        """构造并写入 <p:timing> 动画树（OOXML 标准结构）。

        结构：timing/tnLst/par/cTn(tmRoot)/childTnLst/seq/cTn(mainSeq)/
              childTnLst/par* —— 每个 par 承载一个形状的一段入场动画，
              由 <p:set>（置为可见）+ <p:animEffect>（入场效果）组成。
        """
        counter = [1]

        def nid():
            counter[0] += 1
            return counter[0]

        def el(tag, **attrs):
            e = etree.Element(f"{{{NS_NS}}}{tag}")
            for k, v in attrs.items():
                e.set(k, str(v))
            return e

        def sub(parent, tag, **attrs):
            e = el(tag, **attrs)
            parent.append(e)
            return e

        timing = el("timing")
        tnLst = sub(timing, "tnLst")
        par = sub(tnLst, "par")
        cTn = sub(par, "cTn", id=nid(), dur="indefinite",
                  restart="never", nodeType="tmRoot")
        childTnLst = sub(cTn, "childTnLst")
        seq = sub(childTnLst, "seq", concurrent="1", nextAc="seek")
        seq_cTn = sub(seq, "cTn", id=nid(), dur="indefinite", nodeType="mainSeq")
        seq_child = sub(seq_cTn, "childTnLst")

        for spid, preset_key, node_type, delay in specs:
            preset = self.ENTRANCE_PRESETS.get(
                preset_key, self.ENTRANCE_PRESETS["fade"]
            )
            a_par = sub(seq_child, "par")
            a_cTn = sub(a_par, "cTn")
            a_cTn.set("id", str(nid()))
            a_cTn.set("presetID", str(preset["preset_id"]))
            a_cTn.set("presetClass", "entr")
            a_cTn.set("presetSubtype", str(preset["subtype"]))
            a_cTn.set("fill", "hold")
            a_cTn.set("grpId", "0")
            a_cTn.set("nodeType", node_type)
            stCondLst = sub(a_cTn, "stCondLst")
            sub(stCondLst, "cond", delay=str(delay))
            a_child = sub(a_cTn, "childTnLst")

            # 1) 置为可见（动画播放前元素处于隐藏状态）
            set_el = sub(a_child, "set")
            bhv = sub(set_el, "cBhvr")
            sub(bhv, "cTn", id=nid(), dur="1", fill="hold")
            tgt = sub(bhv, "tgtEl")
            sub(tgt, "spTgt", spid=str(spid))
            anl = sub(bhv, "attrNameLst")
            sub(anl, "attrName").text = "style.visibility"
            to = sub(set_el, "to")
            sub(to, "strVal", val="visible")

            # 2) 入场效果本体
            eff = sub(a_child, "animEffect", transition="in",
                      filter=preset["filter"])
            bhv2 = sub(eff, "cBhvr")
            sub(bhv2, "cTn", id=nid(), dur=str(preset["dur"]))
            tgt2 = sub(bhv2, "tgtEl")
            sub(tgt2, "spTgt", spid=str(spid))

        # 翻页触发条件
        prevCondLst = sub(seq, "prevCondLst")
        c1 = sub(prevCondLst, "cond", evt="onPrev", delay="0")
        sub(sub(c1, "tgtEl"), "sldTgt")
        nextCondLst = sub(seq, "nextCondLst")
        c2 = sub(nextCondLst, "cond", evt="onNext", delay="0")
        sub(sub(c2, "tgtEl"), "sldTgt")

        # 写入 sld（timing 必须位于 transition 之后）
        sld_el = slide_obj._element
        for old in sld_el.findall(f"{{{NS_NS}}}timing"):
            sld_el.remove(old)
        sld_el.append(timing)

    def _rgb_to_color(self, rgb_tuple):
        """RGB元组转颜色对象"""
        return RGBColor(*rgb_tuple)

    # ==================================================================
    # HTML 预览（内容感知）
    # ==================================================================
    def preview_html(self, presentation: AppPresentation) -> str:
        """生成HTML预览（含详细正文与插图，插图以 base64 内嵌）。
        每页背景装饰随内容变化，与 PPTX 保持一致的内容感知逻辑。
        """
        theme = self.themes.get(
            presentation.theme or "business", self.themes["business"]
        )

        def _hex(rgb):
            return "#%02x%02x%02x" % rgb

        title_c = _hex(theme["title_color"])
        accent_c = _hex(theme["accent_color"])
        text_c = _hex(theme["text_color"])
        bg_top = _hex(theme["bg_top"])
        bg_bottom = _hex(theme["bg_bottom"])

        html_parts = [
            '<!DOCTYPE html>',
            '<html><head>',
            '<meta charset="UTF-8">',
            '<title>预览 - ' + presentation.title + '</title>',
            '<style>',
            'body { font-family: "Microsoft YaHei", sans-serif; padding: 24px; '
            f'background: linear-gradient(160deg, {bg_top}, {bg_bottom}); min-height: 100vh; }}',
            '.slide { background: #ffffff; border-radius: 12px; padding: 34px 40px; '
            'margin: 24px 0; box-shadow: 0 4px 18px rgba(0,0,0,0.10); '
            'border-top: 4px solid ' + accent_c + '; position: relative; overflow: hidden; }',
            '.deco { position: absolute; border-radius: 50%; pointer-events: none; }',
            f'.slide h2 {{ color: {title_c}; margin: 0 0 14px; font-size: 24px; '
            f'padding-bottom: 10px; border-bottom: 2px solid {accent_c}; }}',
            f'.detail {{ color: {text_c}; font-size: 15px; line-height: 1.8; margin: 0 0 14px; }}',
            '.slide ul { line-height: 1.9; margin: 0; padding-left: 4px; list-style: none; }',
            f'.slide li {{ margin: 8px 0; padding-left: 18px; position: relative; font-weight: 600; color: {accent_c}; }}',
            '.slide li::before { content: "●"; position: absolute; left: 0; color: ' + accent_c + '; }',
            '.refs li { font-weight: 400; padding-left: 0; color: ' + text_c + '; }',
            '.refs li::before { content: none; }',
            '.imgbox { margin: 14px 0; text-align: center; }',
            f'.imgbox img {{ max-width: 62%; border-radius: 8px; border: 2px solid {accent_c}; '
            'box-shadow: 0 4px 14px rgba(0,0,0,0.15); }}',
            '.notes { color: #777; font-size: 13px; font-style: italic; margin-top: 16px; '
            'padding-top: 10px; border-top: 1px solid #eee; }',
            '</style>',
            '</head><body>',
            f'<h1 style="color:{title_c}">{presentation.title}</h1>',
        ]

        for slide in presentation.slides:
            visual = self._derive_slide_visual(slide)
            rng = random.Random(visual["seed"])
            deco_c = _hex(self._shift_color(theme["deco_color"], rng.randint(-18, 18)))
            size = rng.randint(140, 200)
            # 装饰圆位置随内容变化
            corner = rng.choice(["right:-40px; bottom:-40px;",
                                 "left:-40px; top:-40px;",
                                 "right:-40px; top:-40px;"])
            html_parts.append('<div class="slide">')
            html_parts.append(
                f'<div class="deco" style="{corner} width:{size}px; height:{size}px; '
                f'background:{deco_c}; opacity:0.55;"></div>'
            )
            html_parts.append(f'<h2>{slide.page}. {slide.title}</h2>')
            if slide.detail:
                html_parts.append(f'<p class="detail">{slide.detail}</p>')
            if slide.points:
                if slide.layout == "references":
                    html_parts.append('<ul class="refs">')
                    for i, point in enumerate(slide.points, 1):
                        html_parts.append(f'<li>[{i}] {point}</li>')
                else:
                    html_parts.append('<ul>')
                    for point in slide.points:
                        html_parts.append(f'<li>{point}</li>')
                html_parts.append('</ul>')
            img_b64 = self._image_to_base64(slide.image_path)
            if img_b64:
                html_parts.append(
                    f'<div class="imgbox"><img src="data:image/png;base64,{img_b64}" /></div>'
                )
            if slide.notes:
                html_parts.append(f'<div class="notes">备注：{slide.notes}</div>')
            html_parts.append('</div>')

        html_parts.extend(['</body></html>'])
        return ''.join(html_parts)

    @staticmethod
    def _image_to_base64(image_path):
        """读取图片为 base64；失败返回 None。"""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        except Exception:
            return None
