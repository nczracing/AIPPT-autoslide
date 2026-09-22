# -*- coding: utf-8 -*-
"""
幻灯片预览组件 - 左侧缩略图导航 + 右侧大图预览
模仿PPT演示效果，每张幻灯片独立展示
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTextBrowser, QListWidget, QListWidgetItem,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor, QBrush, QPalette
from settings_module import Presentation
import os
import base64


class SlideThumbnail(QListWidgetItem):
    """幻灯片缩略图项"""
    # 布局图标映射
    LAYOUT_ICONS = {
        "right": "🖼️ 右侧",
        "left": "🖼️ 左侧",
        "top": "🖼️ 上方",
        "bottom": "🖼️ 下方",
        "fullscreen": "🖼️ 全屏",
        "references": "📋 参考",
    }

    def __init__(self, slide, theme="business"):
        self.slide = slide
        self.theme = theme
        # 生成缩略图HTML作为item的文本
        thumb_html = self._generate_thumbnail_html(slide, theme)
        super().__init__(thumb_html)
        self.setData(Qt.ItemDataRole.UserRole, slide)
        self.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)

    def _generate_thumbnail_html(self, slide, theme="business"):
        """生成缩略图HTML"""
        is_dark = False  # 缩略图统一浅色背景以便识别
        layout_hint = slide.image_layout or "right"
        layout_label = self.LAYOUT_ICONS.get(layout_hint, "🖼️")

        theme_colors = PreviewWidget.THEME_COLORS.get(theme, PreviewWidget.THEME_COLORS["business"])

        # 截取前3个要点
        points_preview = " ".join(slide.points[:3])[:30] if slide.points else ""

        html = f'''
        <div style="background:white;border-radius:6px;padding:8px;margin:4px 0;
                   border:2px solid transparent;font-size:11px;">
            <div style="font-weight:bold;color:{theme_colors['accent']};font-size:12px;
                       margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
                第{slide.page}页: {slide.title}
            </div>
            <div style="color:#666;font-size:10px;margin-bottom:4px;">
                {points_preview}
            </div>
            <div style="color:#999;font-size:9px;">{layout_label}</div>
        </div>
        '''
        return html


class PreviewWidget(QWidget):
    """幻灯片预览组件 - 左侧缩略图导航 + 右侧大图预览"""

    LAYOUT_ICONS = {
        "right": ("🖼️ 右侧", "#4A90D9"),
        "left": ("🖼️ 左侧", "#50C878"),
        "top": ("🖼️ 上方", "#FF8C42"),
        "bottom": ("🖼️ 下方", "#9B59B6"),
        "fullscreen": ("🖼️ 全屏", "#E74C3C"),
        "references": ("📋 参考", "#6C757D"),
    }

    THEME_COLORS = {
        "business": {"primary": "#1a5490", "accent": "#2f6fed", "bg": "#f8fafc"},
        "academic": {"primary": "#5a3e1b", "accent": "#8b5e3c", "bg": "#faf8f5"},
        "creative": {"primary": "#6b1d5e", "accent": "#9b59b6", "bg": "#faf5ff"},
        "tech": {"primary": "#0a3d62", "accent": "#0ea5e9", "bg": "#f0f9ff"},
        "vibrant": {"primary": "#9a2b0f", "accent": "#f97316", "bg": "#fff7ed"},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_presentation = None
        self.init_ui()

    def init_ui(self):
        """初始化UI - 左右分栏布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 顶部标题栏
        header = QFrame()
        header.setObjectName("previewHeader")
        header.setFixedHeight(44)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 8, 16, 8)
        hl.setSpacing(8)
        hl.addWidget(QLabel('<b>📊 预览 (Preview)</b>'))
        hl.addStretch()
        self.page_label = QLabel('')
        self.page_label.setObjectName('pageInfo')
        hl.addWidget(self.page_label)
        layout.addWidget(header)

        # 主体内容 - 左右分栏
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        # 左侧缩略图列表
        self.thumbnail_list = QListWidget()
        self.thumbnail_list.setObjectName('thumbnailList')
        self.thumbnail_list.setIconSize(QSize(80, 45))
        self.thumbnail_list.setMaximumWidth(160)
        self.thumbnail_list.setEditTriggers(QListWidget.EditTrigger.NoEditTriggers)
        self.thumbnail_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.thumbnail_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.thumbnail_list.currentRowChanged.connect(self._on_thumbnail_selected)
        body.addWidget(self.thumbnail_list)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setObjectName('previewSeparator')
        body.addWidget(separator)

        # 右侧主预览区
        self.main_preview = QTextBrowser()
        self.main_preview.setObjectName('mainPreview')
        self.main_preview.setOpenLinks(False)
        self.main_preview.setReadOnly(True)
        self.main_preview.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
            }
        """)
        body.addWidget(self.main_preview, stretch=1)

        layout.addLayout(body)

        # 初始提示
        self._show_empty_state()

    def _show_empty_state(self):
        """显示空状态提示"""
        is_dark = self._is_dark()
        if is_dark:
            bg = "#1e2130"
            text = "#64748b"
        else:
            bg = "#f8fafc"
            text = "#94a3b8"

        html = f'''
        <div style="display:flex;align-items:center;justify-content:center;
                    height:100%;min-height:400px;background:{bg};">
            <div style="text-align:center;color:{text};">
                <div style="font-size:48px;margin-bottom:16px;">📑</div>
                <div style="font-size:16px;font-weight:500;">生成 PPT 后在此预览</div>
                <div style="font-size:13px;margin-top:8px;opacity:0.7;">
                    左侧将显示幻灯片缩略图<br>
                    右侧显示详细内容
                </div>
            </div>
        </div>
        '''
        self.main_preview.setHtml(html)
        self.thumbnail_list.clear()
        self.page_label.setText('')

    def _is_dark(self):
        """判断当前是否处于深色模式"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is None:
                return False
            palette = app.palette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            return bg_color.lightness() < 128
        except Exception:
            return False

    def update_preview(self, presentation: Presentation):
        """更新预览内容"""
        self.current_presentation = presentation
        is_dark = self._is_dark()
        theme_colors = self.THEME_COLORS.get(presentation.theme, self.THEME_COLORS["business"])

        # 清空并重建缩略图列表
        self.thumbnail_list.clear()
        for slide in presentation.slides:
            item = SlideThumbnail(slide, presentation.theme)
            self.thumbnail_list.addItem(item)

        # 默认选中第一页
        if self.thumbnail_list.count() > 0:
            self.thumbnail_list.setCurrentRow(0)

        # 更新页码信息
        self.page_label.setText(f'共 {len(presentation.slides)} 页')

        # 显示第一页详情
        self._show_slide_detail(presentation.slides[0], is_dark, theme_colors)

    def _on_thumbnail_selected(self, row):
        """缩略图选择回调"""
        if self.current_presentation and 0 <= row < len(self.current_presentation.slides):
            is_dark = self._is_dark()
            theme_colors = self.THEME_COLORS.get(self.current_presentation.theme,
                                                 self.THEME_COLORS["business"])
            self._show_slide_detail(
                self.current_presentation.slides[row],
                is_dark,
                theme_colors
            )

    def _show_slide_detail(self, slide, is_dark, theme_colors):
        """显示单个幻灯片的详细预览"""
        layout_hint = slide.image_layout or "right"
        layout_label, layout_color = self.LAYOUT_ICONS.get(layout_hint, ("• 未知", "#999"))

        if is_dark:
            bg = "#1e2130"
            card_bg = "#252838"
            border = "#3d4258"
            title_color = "#7ea8ff"
            text_color = "#c8d0e0"
            muted_color = "#64748b"
            point_color = "#b0bac8"
        else:
            bg = "#f8fafc"
            card_bg = "#ffffff"
            border = "#e2e8f0"
            title_color = theme_colors["accent"]
            text_color = "#1e293b"
            muted_color = "#64748b"
            point_color = "#334155"

        # 构建幻灯片预览HTML
        html_parts = [
            f'<div style="font-family:\"Microsoft YaHei UI\",\"Segoe UI\",sans-serif;'
            f'background:{bg};padding:20px;min-height:100%;">',
            # 幻灯片标题区
            f'<div style="background:{card_bg};border-radius:12px;padding:20px 24px;'
            f'margin-bottom:16px;border:1px solid {border};'
            f'box-shadow:0 2px 8px rgba(0,0,0,0.06);">',
            # 标题
            f'<h2 style="margin:0 0 12px 0;color:{title_color};font-size:22px;'
            f'font-weight:700;">{slide.title}</h2>',
            # 元信息行
            f'<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">',
            f'<span style="background:{theme_colors["accent"]};color:white;'
            f'font-size:12px;font-weight:600;padding:3px 10px;border-radius:12px;">'
            f'第 {slide.page} 页</span>',
            f'<span style="background:{layout_color}20;color:{layout_color};'
            f'font-size:12px;padding:3px 10px;border-radius:12px;">'
            f'{layout_label}</span>',
            f'</div></div>',  # 关闭元信息行和标题区

            # 内容区
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">',

            # 左侧：要点列表
            f'<div style="background:{card_bg};border-radius:12px;padding:20px;'
            f'border:1px solid {border};box-shadow:0 1px 4px rgba(0,0,0,0.04);">',
            f'<div style="font-size:14px;font-weight:600;color:{muted_color};'
            f'margin-bottom:12px;">📋 要点</div>',
        ]

        # 要点列表
        if slide.points:
            html_parts.append('<ul style="margin:0;padding-left:18px;">')
            for point in slide.points:
                html_parts.append(
                    f'<li style="margin:6px 0;color:{point_color};font-size:14px;'
                    f'line-height:1.6;">{point}</li>'
                )
            html_parts.append('</ul>')
        else:
            html_parts.append(
                f'<p style="color:{muted_color};font-size:13px;font-style:italic;">'
                f'（无要点）</p>'
            )
        html_parts.append('</div>')  # 关闭左侧卡片

        # 右侧：详情+插图
        html_parts.append(
            f'<div style="background:{card_bg};border-radius:12px;padding:20px;'
            f'border:1px solid {border};box-shadow:0 1px 4px rgba(0,0,0,0.04);">'
        )

        # 详细正文
        if slide.detail:
            html_parts.append(
                f'<div style="font-size:14px;line-height:1.7;color:{text_color};'
                f'margin-bottom:12px;">{slide.detail}</div>'
            )
        else:
            html_parts.append(
                f'<p style="color:{muted_color};font-size:13px;font-style:italic;'
                f'margin-bottom:12px;">（无详细内容）</p>'
            )

        # 备注
        if slide.notes:
            html_parts.append(
                f'<div style="border-top:1px solid {border};padding-top:12px;margin-top:12px;">'
                f'<div style="font-size:12px;font-weight:600;color:{muted_color};'
                f'margin-bottom:6px;">💬 备注</div>'
                f'<div style="font-size:13px;color:{muted_color};font-style:italic;">'
                f'{slide.notes}</div></div>'
            )

        # 插图
        img_b64 = self._image_to_base64(slide.image_path)
        if img_b64:
            html_parts.append(
                f'<div style="margin-top:16px;text-align:center;">'
                f'<div style="font-size:12px;font-weight:600;color:{muted_color};'
                f'margin-bottom:8px;">🖼️ 插图</div>'
                f'<img src="data:image/png;base64,{img_b64}" '
                f'style="max-width:100%;max-height:280px;border-radius:8px;'
                f'border:1px solid {border};box-shadow:0 2px 8px rgba(0,0,0,0.1);"/>'
                f'</div>'
            )

        html_parts.append('</div>')  # 关闭右侧卡片
        html_parts.append('</div>')  # 关闭grid
        html_parts.append('</div>')  # 关闭主容器

        self.main_preview.setHtml(''.join(html_parts))

    def _image_to_base64(self, image_path):
        """将图片转换为base64编码"""
        if not image_path or not os.path.exists(image_path):
            return None
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        except Exception:
            return None
