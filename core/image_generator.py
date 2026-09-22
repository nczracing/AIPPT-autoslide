# -*- coding: utf-8 -*-
"""
插图生成器
为每页幻灯片生成配图：优先调用 AI 图像 API，失败则用 Pillow 绘制主题示意图，
两者都失败时返回 None（由调用方优雅跳过插图）。
"""
import base64
import logging
import os
import re
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("autoslide")

# 合法的图像服务提供商标识；旧配置中可能残留非法值（如 "dall-e-3"），需归一化。
VALID_PROVIDERS = {"agnes", "openai", "custom"}
# 图像尺寸必须为 "宽x高" 格式，非法值回退此默认。
DEFAULT_IMAGE_SIZE = "1024x768"


# 主题配色（与 pptx_builder 的 THEMES 对应，用于本地兜底示意图）
_THEME_COLORS = {
    "business": ((0, 51, 102), (51, 102, 153), (230, 240, 250)),
    "academic": ((102, 51, 0), (153, 102, 51), (250, 244, 230)),
    "creative": ((102, 0, 102), (153, 51, 153), (250, 240, 250)),
    "tech": ((0, 102, 153), (0, 153, 204), (235, 245, 252)),
    "vibrant": ((180, 60, 30), (220, 90, 50), (252, 240, 232)),
}


def _find_cjk_font() -> Optional[str]:
    """查找可渲染中文的系统字体（Windows 优先，含常见 Linux 字体兜底）。"""
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
        r"C:\Windows\Fonts\msyhbd.ttc",    # 微软雅黑粗体
        r"C:\Windows\Fonts\simhei.ttf",    # 黑体
        r"C:\Windows\Fonts\simsun.ttc",    # 宋体
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


class ImageGenerator:
    """插图生成器：AI 图像优先，本地示意图兜底。"""

    def __init__(self, client=None):
        """client 可选注入（用于测试）；默认根据配置自行建立 OpenAI 客户端。"""
        from settings_module import get_settings
        self.settings = get_settings()
        self.client = client
        if self.client is None:
            self._connect()

    def _connect(self):
        """建立图像客户端；无 Key 或连接失败时保持 None，走兜底。"""
        config = self.settings.get_ai_config()
        ppt_cfg = self.settings.get_ppt_config()
        # 图像 API Key 优先级：ppt.image_api_key > ai.api_key > 环境变量 AGNES_API_KEY
        api_key = (
            ppt_cfg.get("image_api_key", "")
            or config.get("api_key", "")
            or os.environ.get("AGNES_API_KEY", "")
        )
        if ppt_cfg.get("image_api_key", ""):
            key_source = "image_api_key"
        elif config.get("api_key", ""):
            key_source = "ai.api_key"
        elif os.environ.get("AGNES_API_KEY", ""):
            key_source = "env AGNES_API_KEY"
        else:
            key_source = ""
        base_url = ppt_cfg.get("image_base_url", "") or "https://apihub.agnes-ai.com/v1"
        if not api_key:
            logger.info("未配置图像 API Key，将使用本地示意图兜底")
            return
        try:
            from openai import OpenAI
            # 图像生成较慢（Agnes 约 10s~60s），超时放宽，避免误判失败。
            # 直接传 float 总超时，避免显式依赖 httpx（不同环境可能是 httpx2）。
            self.client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=120.0,
            )
            logger.info(
                "图像客户端已连接: %s (model=%s, key来源=%s)",
                base_url,
                ppt_cfg.get("image_model", "agnes-image-2.1-flash"),
                key_source or "未知",
            )
        except Exception as e:
            logger.warning("图像客户端初始化失败，将使用本地示意图: %s", e)
            self.client = None

    def generate(
        self,
        image_prompt: str,
        slide_title: str = "",
        output_dir: str = "",
        filename_prefix: str = "slide",
        theme: str = "business",
        layout: str = "right",
    ) -> Optional[str]:
        """生成一页插图，返回本地图片路径；失败返回 None。

        image_prompt: 英文图像描述；slide_title 用于兜底示意图上的文字。
        layout: 目标版面布局，用于请求与版面区域匹配的图片比例，消除比例失调。
        """
        if not image_prompt and not slide_title:
            return None

        output_dir = Path(output_dir) if output_dir else self._session_dir()
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1) AI 图像优先（按布局请求匹配比例）
        path = self._generate_ai(image_prompt, output_dir, filename_prefix, layout)
        if path:
            return path

        # 2) 本地示意图兜底（画布比例同样匹配版面）
        return self._generate_fallback(slide_title, output_dir, filename_prefix, theme, layout)

    # ------------------------------------------------------------------
    _IMAGES_ROOT = None

    @classmethod
    def _images_root(cls) -> Path:
        """本应用的插图根目录（%TEMP%/AutoSlide/images）。"""
        if cls._IMAGES_ROOT is None:
            cls._IMAGES_ROOT = Path(
                os.environ.get("TEMP") or os.environ.get("TMP") or Path.home()
            ) / "AutoSlide" / "images"
        return cls._IMAGES_ROOT

    @classmethod
    def _session_dir(cls) -> Path:
        """创建本次生成的会话目录，并触发旧会话清理。"""
        root = cls._images_root()
        root.mkdir(parents=True, exist_ok=True)
        name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        d = root / name
        d.mkdir(parents=True, exist_ok=True)
        cls._cleanup_old_sessions(root)
        return d

    @classmethod
    def _cleanup_old_sessions(cls, root: Path, max_age_days: int = 7):
        """清理超过 max_age_days 的旧会话目录。

        仅清理本应用创建的命名目录（YYYYMMDD_HHMMSS_xxxxxxxx），
        不触碰用户文件。失败静默，避免影响主流程。
        """
        pattern = re.compile(r"^\d{8}_\d{6}_[0-9a-f]{8}$")
        try:
            now = time.time()
            for child in root.iterdir():
                if not child.is_dir() or not pattern.match(child.name):
                    continue
                age = now - child.stat().st_mtime
                if age > max_age_days * 86400:
                    shutil.rmtree(child, ignore_errors=True)
                    logger.info("已清理旧插图会话: %s", child.name)
        except Exception as e:
            logger.debug("旧会话清理异常，已忽略: %s", e)

    # ------------------------------------------------------------------
    # 布局→图片比例映射：生成图比例精确匹配版面显示框，实现零裁剪
    # （每张图都以原始比例完整显示，不做 cover-fit 裁切）。
    # - right/left：版面框随图片比例自适应（本就无裁剪），取 4:5 竖版观感最佳
    # - top/bottom：镜像 pptx_builder.BANNER_FRAME_RATIO = (13.333-1.4)/2.4 ≈ 4.97:1，
    #   1536x309 → 4.971（偏差 0.03%，远小于插入端 1% 裁剪容忍阈值）
    # - fullscreen：背景铺满，16:9 精确匹配幻灯片比例
    LAYOUT_IMAGE_SIZES = {
        "right": "1024x1280",
        "left": "1024x1280",
        "top": "1536x309",
        "bottom": "1536x309",
        "fullscreen": "1024x576",
    }
    # API 拒绝精确比例尺寸时的次级回退（近似比例 + 插入端横幅高度自适应 → 仅少量裁切）。
    # 注意：回退尺寸由 API 约束决定，比例与目标框仍有偏差时插入端会触发
    # cover-fit 裁剪（如 1536x512 → 约 5% 垂直裁切），属已知妥协而非 bug。
    LAYOUT_FALLBACK_SIZES = {
        "right": [],
        "left": [],
        "top": ["1536x512"],
        "bottom": ["1536x512"],
        "fullscreen": [],
    }
    LAYOUT_FALLBACK_CANVAS = {
        "right": (1024, 1280),
        "left": (1024, 1280),
        "top": (1536, 309),
        "bottom": (1536, 309),
        "fullscreen": (1024, 576),
    }

    def _generate_ai(self, image_prompt, output_dir, filename_prefix, layout="right") -> Optional[str]:
        if not self.client or not image_prompt:
            return None
        try:
            ppt_cfg = self.settings.get_ppt_config()
            model = ppt_cfg.get("image_model", "agnes-image-2.1-flash")
            provider = ppt_cfg.get("image_provider", "agnes")
            # P1-A：旧配置可能残留非法 provider 值（如 "dall-e-3"），归一化到合法集合
            if provider not in VALID_PROVIDERS:
                logger.warning("未知 image_provider '%s'，回退 'agnes'", provider)
                provider = "agnes"
            # P2-A：校验 image_size 格式（必须为 宽x高），非法值回退默认
            configured_size = ppt_cfg.get("image_size", DEFAULT_IMAGE_SIZE)
            if not re.fullmatch(r"\d+x\d+", str(configured_size)):
                logger.warning("image_size '%s' 格式非法，回退默认 '%s'", configured_size, DEFAULT_IMAGE_SIZE)
                configured_size = DEFAULT_IMAGE_SIZE
            # 按布局请求精确匹配比例；被拒时沿"精确比例→近似比例→用户配置尺寸"
            # 回退链重试（去重保序），配合插入端横幅高度自适应实现最小裁切
            size = self.LAYOUT_IMAGE_SIZES.get(layout, configured_size)
            chain = []
            for sz in (size, *self.LAYOUT_FALLBACK_SIZES.get(layout, []), configured_size):
                if sz not in chain:
                    chain.append(sz)
            for attempt, sz in enumerate(chain):
                result = self._request_image(image_prompt, model, provider, sz)
                if result:
                    saved = self._save_image_result(result, output_dir, filename_prefix)
                    if saved:
                        if attempt > 0:
                            logger.info("布局比例尺寸 %s 被拒绝，已回退 %s", chain[0], sz)
                        return saved
        except Exception as e:
            logger.warning("AI 插图生成失败，回退本地示意图: %s", e)
        return None

    def _save_image_result(self, raw, output_dir, filename_prefix):
        """将 AI 返回的 b64 或 URL 结果落盘，返回本地路径；失败返回 None。"""
        path = output_dir / f"{filename_prefix}.png"
        if isinstance(raw, str) and raw.startswith(("http://", "https://")):
            import requests
            r = requests.get(raw, timeout=60)
            r.raise_for_status()
            path.write_bytes(r.content)
            logger.info("AI 插图下载成功: %s", path.name)
        else:
            path.write_bytes(base64.b64decode(raw))
            logger.info("AI 插图生成成功(b64): %s", path.name)
        return str(path)

    def _request_image(self, image_prompt, model, provider, size):
        """单次图像请求：成功返回本地路径，失败返回 None。"""
        kwargs = {"model": model, "prompt": image_prompt, "size": size, "n": 1}
        if provider == "agnes":
            # Agnes 明确返回 URL（对象存储，有时效，需尽快下载）
            kwargs["extra_body"] = {"response_format": "url"}
        resp = self.client.images.generate(**kwargs)
        data = resp.data[0] if getattr(resp, "data", None) else None
        if not data:
            return None
        raw = getattr(data, "b64_json", None)
        if raw:
            return raw  # 返回 b64，由调用方落盘
        return getattr(data, "url", None)

    # ------------------------------------------------------------------
    def _generate_fallback(self, slide_title, output_dir, filename_prefix, theme, layout="right") -> Optional[str]:
        """用 Pillow 绘制一张有设计感的示意图：渐变 + 网格 + 几何装饰 + 圆角卡片 + 标题。

        画布比例随目标布局变化（右/左竖版、上/下宽幅、全屏16:9），
        保证兜底图同样与版面协调。
        """
        output_dir = Path(output_dir)
        try:
            from PIL import Image, ImageDraw, ImageFont
        except Exception as e:
            logger.warning("Pillow 不可用，跳过本地示意图: %s", e)
            return None

        primary, accent, light = _THEME_COLORS.get(
            theme, _THEME_COLORS["business"]
        )
        width, height = self.LAYOUT_FALLBACK_CANVAS.get(layout, (1024, 1024))
        # 画布宽高比系数：横幅（4.97:1）下 1px 线宽太细，需放大；竖版则保持
        aspect = width / height
        line_scale = max(1.0, min(3.0, aspect / 2.0))  # 2:1→1x, 4.97:1→~2.5x

        img = Image.new("RGB", (width, height), light)
        draw = ImageDraw.Draw(img)

        # 渐变背景（自上而下：主色 → 浅色）
        for y in range(height):
            ratio = y / height
            r = int(primary[0] + (light[0] - primary[0]) * ratio)
            g = int(primary[1] + (light[1] - primary[1]) * ratio)
            b = int(primary[2] + (light[2] - primary[2]) * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # 装饰性半透明圆形 + 细网格线（合并到同一 RGBA overlay，alpha 才能生效）
        # 注意：之前网格画在 RGB 图上，alpha=18 被忽略导致线条发黑；移到 overlay 修复
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        # 细网格线（增加设计感；线宽按画布比例缩放）
        grid_w = max(1, int(1.5 * line_scale))
        for x in range(0, width, 64):
            od.line([(x, 0), (x, height)], fill=(*primary, 22), width=grid_w)
        for y in range(0, height, 64):
            od.line([(0, y), (width, y)], fill=(*primary, 22), width=grid_w)
        # 装饰圆（按画布比例缩放）
        od.ellipse((width * 0.55, -height * 0.2, width * 1.15, height * 0.4), fill=(*accent, 80))
        od.ellipse((-width * 0.25, height * 0.6, width * 0.35, height * 1.2), fill=(*accent, 55))
        od.ellipse((width * 0.72, height * 0.62, width * 1.05, height * 0.95), fill=(*primary, 70))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 中心圆角卡片（视觉焦点；圆角随画布高度缩放，横幅下不过大）
        card = [int(width * 0.12), int(height * 0.26), int(width * 0.88), int(height * 0.74)]
        card_radius = max(8, min(32, int(height * 0.03)))
        draw.rounded_rectangle(card, radius=card_radius, fill=(255, 255, 255), outline=accent,
                               width=max(2, int(3 * line_scale)))

        # 卡片顶部主题色装饰条（有标题时显示；高度按画布比例缩放，横幅下不再显粗）
        if slide_title:
            bar_h = max(3, int(height * 0.012 * line_scale))
            draw.rectangle([card[0], card[1], card[2], card[1] + bar_h], fill=accent)
        else:
            # 无标题时改为水平居中细线，避免贴顶视觉失衡
            mid_y = (card[1] + card[3]) // 2
            draw.line([(card[0] + int(width * 0.15), mid_y),
                       (card[2] - int(width * 0.15), mid_y)],
                      fill=accent, width=max(2, int(2 * line_scale)))

        font_path = _find_cjk_font()
        if font_path and slide_title:
            text = slide_title
            font_size = min(84, int(height * 0.082))
            font = ImageFont.truetype(font_path, font_size)
            # 按字符宽度折行，避免超宽
            max_chars_per_line = max(1, int((card[2] - card[0]) * 0.92 / (font_size * 1.1)))
            lines = []
            for i in range(0, len(text), max_chars_per_line):
                lines.append(text[i:i + max_chars_per_line])
            lines = lines[:4]
            line_height = int(font_size * 1.45)
            total_h = line_height * len(lines)
            y_start = card[1] + (card[3] - card[1]) // 2 - total_h // 2 + 20
            for k, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                w = bbox[2] - bbox[0]
                x = (width - w) // 2
                draw.text((x, y_start + k * line_height), line, font=font, fill=primary)

            # 卡片底部装饰性分隔线 + 副标签
            mid_y = card[3] - 70
            draw.line([(card[0] + 40, mid_y), (card[2] - 40, mid_y)], fill=accent, width=2)
            tag = "AutoSlide"
            tag_font = ImageFont.truetype(font_path, 28)
            tbbox = draw.textbbox((0, 0), tag, font=tag_font)
            tw = tbbox[2] - tbbox[0]
            draw.text(((width - tw) // 2, mid_y + 16), tag, font=tag_font, fill=accent)

        path = output_dir / f"{filename_prefix}.png"
        img.save(str(path))
        logger.info("本地示意图生成成功: %s (%dx%d)", path.name, width, height)
        return str(path)
