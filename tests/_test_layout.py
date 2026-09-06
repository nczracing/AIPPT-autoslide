# -*- coding: utf-8 -*-
"""排版回归测试：图文不重叠 + 文字不越界 + 多栏不互相重叠

覆盖场景：
- 单栏正文 + 图片（right / left / top）× 图片比例（方形1:1 / 宽图2:1 / 高图1:2 / 横幅精确比例4.97:1）
- 双栏 two_content + 图片
- 无图片但文字超量（强制触发字号自适应）
- fullscreen 模式
验证项：
V1 图片矩形与正文框矩形无交叠
V2 所有形状在幻灯片边界内
V3 正文估算高度不超过文本框高度
V4 top 模式图片不进入标题区（top >= 1.45）
V6 裁切兜底 + V6b/V6c 横幅几何镜像
V7 稀疏均衡；V8 零裁剪（band 4.97:1 精确比例图原比例完整显示）
"""
import os
import sys
import tempfile

sys.path.insert(0, '.')

from PIL import Image as PILImage
from pptx import Presentation as PptxPresentation
from pptx.util import Emu

from settings_module import Presentation, Slide
from core.pptx_builder import PPTXBuilder

SLIDE_W, SLIDE_H = 13.333, 7.5
FAILURES = []


def make_test_images(tmpdir):
    paths = {}
    ratios = {}
    specs = {
        "square": (800, 800),
        "wide": (1200, 600),
        "tall": (600, 1200),
        "band": (1536, 309),   # 精确匹配横幅框比例（4.97:1），用于零裁剪验证
    }
    for name, (w, h) in specs.items():
        p = os.path.join(tmpdir, f"img_{name}.png")
        img = PILImage.new("RGB", (w, h), (100, 150, 200))
        img.save(p)
        paths[name] = p
        ratios[name] = w / h
    paths["ratio"] = ratios
    return paths


def build_case(tmpdir, tag, slides_spec):
    p = Presentation(title="排版回归测试", theme="business", language="zh")
    for s in slides_spec:
        p.add_slide(s)
    builder = PPTXBuilder()
    out = os.path.join(tmpdir, f"case_{tag}.pptx")
    builder.build(p, out)
    return out


def rects_overlap(a, b, eps=0.02):
    """矩形 (l,t,w,h) 判交叠（英寸），忽略 <eps 的贴边接触"""
    ax1, ay1, ax2, ay2 = a[0], a[1], a[0] + a[2], a[1] + a[3]
    bx1, by1, bx2, by2 = b[0], b[1], b[0] + b[2], b[1] + b[3]
    ox = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    oy = max(0.0, min(ay2, by2) - max(ay1, by1))
    return (ox > eps) and (oy > eps), ox, oy


def verify_pptx(path, tag, builder):
    prs = PptxPresentation(path)
    for idx, slide_obj in enumerate(prs.slides, 1):
        pics, texts = [], []
        for shape in slide_obj.shapes:
            try:
                l, t = shape.left.inches, shape.top.inches
                w, h = shape.width.inches, shape.height.inches
            except Exception:
                continue
            rect = (l, t, w, h)
            has_text = shape.has_text_frame and shape.text_frame.text.strip()
            is_pic = shape.shape_type == 13 or shape.__class__.__name__ == "Picture"
            # V2: 边界检查（容差 0.05）
            # 装饰形状（无文字非图片）允许出血式越界（有意裁切设计），豁免
            if (has_text or is_pic) and (
                l < -0.05 or t < -0.05 or l + w > SLIDE_W + 0.05 or t + h > SLIDE_H + 0.05
            ):
                FAILURES.append(
                    f"[{tag}] V2 第{idx}页 形状越界: {shape.shape_type} "
                    f"rect=({l:.2f},{t:.2f},{w:.2f},{h:.2f})"
                )
            if has_text:
                # V5: 文字不得贴画面边缘（四边安全边距 ≥0.3"，容差 0.05）
                margins = (l, t, SLIDE_W - (l + w), SLIDE_H - (t + h))
                if min(margins) < 0.25:
                    FAILURES.append(
                        f"[{tag}] V5 第{idx}页 文字贴边缘: "
                        f"rect=({l:.2f},{t:.2f},{w:.2f},{h:.2f}) "
                        f"边距 L{margins[0]:.2f}/T{margins[1]:.2f}"
                        f"/R{margins[2]:.2f}/B{margins[3]:.2f} "
                        f"内容: {shape.text_frame.text[:16]!r}"
                    )
            if is_pic:
                pics.append((rect, shape))
            elif has_text:
                # 排除标题占位符（索引0 且位于顶部窄条）
                is_title = False
                try:
                    if shape.is_placeholder and shape.placeholder_format.idx == 0:
                        is_title = True
                except Exception:
                    pass
                if not is_title:
                    texts.append((rect, shape))

        # V1/V4: 图文交叠（fullscreen 模式图片即背景，文字叠加为设计行为，豁免）
        is_fullscreen = "fullscreen" in tag
        for pr, pic in pics:
            if not is_fullscreen and pr[1] < 1.45 - 0.05 and pr[3] < SLIDE_H - 1.0:
                FAILURES.append(
                    f"[{tag}] V4 第{idx}页 图片进入标题区: top={pr[1]:.2f}"
                )
            if is_fullscreen:
                continue
            for tr, tsh in texts:
                hit, ox, oy = rects_overlap(pr, tr)
                if hit:
                    FAILURES.append(
                        f"[{tag}] V1 第{idx}页 图文重叠: 图片rect=({pr[0]:.2f},{pr[1]:.2f},"
                        f"{pr[2]:.2f},{pr[3]:.2f}) 文字rect=({tr[0]:.2f},{tr[1]:.2f},"
                        f"{tr[2]:.2f},{tr[3]:.2f}) overlap=({ox:.2f},{oy:.2f}) "
                        f"文字片段: {tsh.text_frame.text[:20]!r}"
                    )

        # V3: 正文估算高度 vs 框高（用 builder 的估算器）
        for entry in builder._content_registry:
            pass  # 注册表为空（build 已结束），改用直接估算下方逻辑


def verify_text_fit(path, tag):
    """V3: 每个文本框按字号行高直接实测（重新解析 pptx）"""
    prs = PptxPresentation(path)
    for idx, slide_obj in enumerate(prs.slides, 1):
        for shape in slide_obj.shapes:
            if not shape.has_text_frame:
                continue
            try:
                box_h = shape.height.inches
                box_w = shape.width.inches
            except Exception:
                continue
            text = shape.text_frame.text.strip()
            if not text:
                continue
            try:
                if shape.is_placeholder and shape.placeholder_format.idx == 0:
                    continue  # 标题单独处理
            except Exception:
                pass
            need = 0.0
            for para in shape.text_frame.paragraphs:
                if not para.text.strip():
                    continue
                size = (para.font.size.pt if para.font.size else 18.0)
                char_w = size / 72.0 * 0.8
                cpl = max(6, int((box_w - 0.2) / char_w))
                lines = max(1, -(-len(para.text) // cpl))
                ls = para.line_spacing if para.line_spacing else 1.2
                need += lines * size / 72.0 * float(ls)
                if para.space_after:
                    need += para.space_after.pt / 72.0
            if need > box_h + 0.35:  # 容差：normAutofit 兜底 + 估算误差
                FAILURES.append(
                    f"[{tag}] V3 第{idx}页 文字可能溢出: 需{need:.2f}\" 框高{box_h:.2f}\" "
                    f"内容: {text[:24]!r}"
                )


def _expected_band_geometry(src_ratio):
    """镜像 pptx_builder top/bottom 横幅几何：高度先自适应（钳制
    BANNER_BAND_H_MIN~MAX），宽度随之贴合图片比例（钳制 BANNER_BAND_W_MIN，
    居中收窄），返回 (left, width, height)。"""
    band_w_max = 13.333 - 1.4
    h = min(PPTXBuilder.BANNER_BAND_H_MAX,
            max(PPTXBuilder.BANNER_BAND_H_MIN, band_w_max / src_ratio))
    w = min(band_w_max, max(PPTXBuilder.BANNER_BAND_W_MIN, h * src_ratio))
    h = min(PPTXBuilder.BANNER_BAND_H_MAX,
            max(PPTXBuilder.BANNER_BAND_H_MIN, w / src_ratio))
    left = 0.7 + (band_w_max - w) / 2
    return left, w, h


def verify_cover_crop(tmpdir, imgs):
    """V6: 裁切兜底验证——top/bottom 横幅与 fullscreen 背景在图片比例偏离
    显示框超过 1% 时必须设置 crop（防拉伸），且裁切方向正确、裁后比例一致；
    图片比例与显示框匹配（<1%）时零裁剪（见 V8）。"""
    from pptx import Presentation as PptxPresentation
    from settings_module import Presentation as Pres, Slide
    builder = PPTXBuilder()
    for tag, layout, img_key, target_ratio in (
        ("crop_top", "top", "square", None),
        ("crop_bottom", "bottom", "tall", None),
        ("crop_fs", "fullscreen", "square", 13.333 / 7.5),
    ):
        p = Pres(title="裁切测试", theme="business", language="zh")
        p.add_slide(Slide(page=1, title="裁切验证", points=["裁切验证要点"],
                          detail="验证比例不变形。",
                          layout="title_content", image_path=imgs[img_key],
                          image_layout=layout))
        out = os.path.join(tmpdir, f"{tag}.pptx")
        builder.build(p, out)
        prs = PptxPresentation(out)
        for slide_obj in prs.slides:
            for shape in slide_obj.shapes:
                if shape.shape_type != 13 and shape.__class__.__name__ != "Picture":
                    continue
                src_ratio = imgs["ratio"][img_key]
                # top/bottom 横幅几何已按图片比例二维自适应，目标比例需镜像推导；
                # 同时断言实际几何与镜像推导完全一致（防常量被误改，F-26-01）
                if target_ratio is None:
                    exp_l, exp_w, exp_h = _expected_band_geometry(src_ratio)
                    target_ratio = exp_w / exp_h
                    if layout in ("top", "bottom"):
                        if (abs(shape.left.inches - exp_l) > 0.02
                                or abs(shape.width.inches - exp_w) > 0.02
                                or abs(shape.height.inches - exp_h) > 0.02):
                            FAILURES.append(
                                f"[{tag}] V6c 横幅几何偏离镜像推导: "
                                f"left={shape.left.inches:.2f}/{exp_l:.2f} "
                                f"w={shape.width.inches:.2f}/{exp_w:.2f} "
                                f"h={shape.height.inches:.2f}/{exp_h:.2f}"
                            )
                crop_total_h = (shape.crop_left or 0) + (shape.crop_right or 0)
                crop_total_v = (shape.crop_top or 0) + (shape.crop_bottom or 0)
                # 期望：沿过长方向有裁切，另一方向为 0
                if src_ratio > target_ratio + 1e-6:
                    ok = crop_total_h > 0.01 and crop_total_v == 0
                elif src_ratio < target_ratio - 1e-6:
                    ok = crop_total_v > 0.01 and crop_total_h == 0
                else:
                    ok = crop_total_h == 0 and crop_total_v == 0
                if not ok:
                    FAILURES.append(
                        f"[{tag}] V6 裁切异常: src_ratio={src_ratio:.3f} "
                        f"target={target_ratio:.3f} cropH={crop_total_h:.3f} "
                        f"cropV={crop_total_v:.3f}"
                    )
                # V6b: 横幅带区内水平居中（左右边距 ≥0.7"），宽度不超带区上限；
                # bottom 横幅底边不得贴画面底端（≥0.3" 安全边距）
                if layout in ("top", "bottom"):
                    l_in, w_in = shape.left.inches, shape.width.inches
                    right_edge = l_in + w_in
                    if l_in < 0.68 or right_edge > 13.333 - 0.68:
                        FAILURES.append(
                            f"[{tag}] V6b 横幅未在带区内居中: left={l_in:.2f} "
                            f"right_edge={right_edge:.2f}（期望带区 0.70~12.63）"
                        )
                    if w_in > 13.333 - 1.4 + 0.02:
                        FAILURES.append(
                            f"[{tag}] V6b 横幅超宽: width={w_in:.2f}（期望 ≤11.93）"
                        )
                    if layout == "bottom":
                        # 镜像代码常量：底边 = SLIDE_H - BANNER_BOTTOM_MARGIN，
                        # 阈值随常量联动，防止边距被悄悄偷走（F-25-01）
                        bottom_edge = shape.top.inches + shape.height.inches
                        expect_bottom = 7.5 - PPTXBuilder.BANNER_BOTTOM_MARGIN
                        if bottom_edge > expect_bottom + 0.02:
                            FAILURES.append(
                                f"[{tag}] V6b bottom 横幅贴底: bottom_edge="
                                f"{bottom_edge:.2f}（期望 ≤{expect_bottom:.2f}，"
                                f"底边距 ≥{PPTXBuilder.BANNER_BOTTOM_MARGIN}\"）"
                            )


def verify_sparse_balance(tmpdir, imgs):
    """V7: 稀疏内容均衡——right/left 布局文字很少时，
    插图应自动放大（>4.6"），正文块应垂直居中（top 明显下移）。"""
    from pptx import Presentation as PptxPresentation
    from settings_module import Presentation as Pres, Slide
    builder = PPTXBuilder()
    for tag, layout in (("sparse_right", "right"), ("sparse_left", "left")):
        p = Pres(title="稀疏均衡", theme="business", language="zh")
        p.add_slide(Slide(page=1, title="稀疏页", points=["要点一", "要点二"],
                          detail="", layout="title_content",
                          image_path=imgs["square"], image_layout=layout))
        out = os.path.join(tmpdir, f"{tag}.pptx")
        builder.build(p, out)
        prs = PptxPresentation(out)
        pic_w = 0.0
        body_top = None
        for slide_obj in prs.slides:
            for shape in slide_obj.shapes:
                if shape.shape_type == 13 or shape.__class__.__name__ == "Picture":
                    pic_w = max(pic_w, shape.width.inches)
                elif shape.has_text_frame and "要点" in shape.text_frame.text:
                    body_top = shape.top.inches
        if pic_w <= 4.6:
            FAILURES.append(
                f"[{tag}] V7 稀疏页插图未放大: width={pic_w:.2f}（期望 >4.6）"
            )
        if body_top is None or body_top < 2.2:
            FAILURES.append(
                f"[{tag}] V7 稀疏页正文未垂直居中: top={body_top}（期望 >2.2）"
            )


def verify_no_crop_band(tmpdir, imgs):
    """V8: 零裁剪——图片比例精确匹配横幅框比例时（生成端正常出图的情形），
    图片必须原比例完整显示：crop 全 0 + 横幅保持标准高度 +
    bottom 底边距画面底端 BANNER_BOTTOM_MARGIN。"""
    from settings_module import Presentation as Pres, Slide
    builder = PPTXBuilder()
    for tag, layout in (("nocrop_top", "top"), ("nocrop_bottom", "bottom")):
        p = Pres(title="零裁剪", theme="business", language="zh")
        p.add_slide(Slide(page=1, title="零裁剪验证", points=["原比例要点"],
                          detail="图片按原始比例完整显示，不做任何裁剪。",
                          layout="title_content", image_path=imgs["band"],
                          image_layout=layout))
        out = os.path.join(tmpdir, f"{tag}.pptx")
        builder.build(p, out)
        prs = PptxPresentation(out)
        found = False
        for slide_obj in prs.slides:
            for shape in slide_obj.shapes:
                if shape.shape_type != 13 and shape.__class__.__name__ != "Picture":
                    continue
                found = True
                crop_h = (shape.crop_left or 0) + (shape.crop_right or 0)
                crop_v = (shape.crop_top or 0) + (shape.crop_bottom or 0)
                if crop_h > 0.01 or crop_v > 0.01:
                    FAILURES.append(
                        f"[{tag}] V8 应零裁剪: cropH={crop_h:.4f} cropV={crop_v:.4f}"
                    )
                h_in = shape.height.inches
                if abs(h_in - PPTXBuilder.BANNER_BAND_H) > 0.05:
                    FAILURES.append(
                        f"[{tag}] V8 横幅高度应保持标准 {PPTXBuilder.BANNER_BAND_H}\": "
                        f"{h_in:.3f}"
                    )
                # 精确匹配框比例 → 横幅应保持满带宽（11.93"）且靠左 0.7"
                if abs(shape.width.inches - (13.333 - 1.4)) > 0.05:
                    FAILURES.append(
                        f"[{tag}] V8 横幅宽度应保持标准带宽 11.93\": "
                        f"{shape.width.inches:.3f}"
                    )
                if abs(shape.left.inches - 0.7) > 0.02:
                    FAILURES.append(
                        f"[{tag}] V8 横幅应靠左 0.7\": left={shape.left.inches:.3f}"
                    )
                if layout == "bottom":
                    bottom_edge = shape.top.inches + h_in
                    expect = 7.5 - PPTXBuilder.BANNER_BOTTOM_MARGIN
                    if abs(bottom_edge - expect) > 0.02:
                        FAILURES.append(
                            f"[{tag}] V8 bottom 底边应为 {expect:.2f}: {bottom_edge:.3f}"
                        )
        if not found:
            FAILURES.append(f"[{tag}] V8 未找到图片")


def main():
    tmpdir = tempfile.mkdtemp()
    imgs = make_test_images(tmpdir)
    builder = PPTXBuilder()

    heavy_detail = "这是一段极长的详细正文。" * 15
    heavy_points = [f"第{i}个要点：描述参赛选手在赛场上的具体表现与技术细节" for i in range(1, 13)]

    cases = []
    # 场景1: 单栏 + right 图片 × 3 比例
    for name in ("square", "wide", "tall"):
        cases.append((f"right_{name}", [
            Slide(page=1, title="图文混排测试", points=heavy_points[:6], detail=heavy_detail,
                  layout="title_content", image_path=imgs[name], image_layout="right"),
        ]))
    # 场景2: 单栏 + left / top / bottom / fullscreen
    cases.append(("left_tall", [
        Slide(page=1, title="左图测试", points=heavy_points[:6], detail=heavy_detail,
              layout="title_content", image_path=imgs["tall"], image_layout="left"),
    ]))
    cases.append(("top_wide", [
        Slide(page=1, title="顶图测试", points=heavy_points[:6], detail=heavy_detail,
              layout="title_content", image_path=imgs["wide"], image_layout="top"),
    ]))
    cases.append(("bottom_square", [
        Slide(page=1, title="底图测试", points=heavy_points[:6], detail=heavy_detail,
              layout="title_content", image_path=imgs["square"], image_layout="bottom"),
    ]))
    cases.append(("bottom_tall", [
        Slide(page=1, title="底图测试·竖图", points=heavy_points[:6], detail=heavy_detail,
              layout="title_content", image_path=imgs["tall"], image_layout="bottom"),
    ]))
    cases.append(("fullscreen_square", [
        Slide(page=1, title="全图测试", points=heavy_points[:4], detail=heavy_detail,
              layout="title_content", image_path=imgs["square"], image_layout="fullscreen"),
    ]))
    # 场景3: 双栏 + 图片（四种布局）
    for mode in ("right", "left", "top"):
        cases.append((f"two_{mode}", [
            Slide(page=1, title="双栏图文测试", points=heavy_points[:8], detail=heavy_detail,
                  layout="two_content", image_path=imgs["wide"], image_layout=mode),
        ]))
    # 场景4: 无图片超量文字（溢出回归）
    cases.append(("no_img_heavy", [
        Slide(page=1, title="超量文字测试" * 3, points=heavy_points, detail=heavy_detail,
              layout="title_content"),
        Slide(page=2, title="双栏超量", points=heavy_points, detail=heavy_detail,
              layout="two_content"),
    ]))

    for tag, spec in cases:
        out = build_case(tmpdir, tag, spec)
        verify_pptx(out, tag, builder)
        verify_text_fit(out, tag)

    verify_cover_crop(tmpdir, imgs)
    verify_sparse_balance(tmpdir, imgs)
    verify_no_crop_band(tmpdir, imgs)

    print("=" * 60)
    if FAILURES:
        print(f"✗ 发现 {len(FAILURES)} 个问题:")
        for f in FAILURES:
            print("  " + f)
        sys.exit(1)
    else:
        print(f"✓ 全部 {len(cases)} 个场景通过：图文无重叠 / 无越界 / 文字可容纳")


if __name__ == "__main__":
    main()
