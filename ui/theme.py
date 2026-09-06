# -*- coding: utf-8 -*-
"""AutoSlide 全局视觉主题（QSS）。

支持浅色/深色两种模式切换。
"""
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication, QStyleFactory
from typing import Optional

# 全局 QApplication 引用
_app_instance: Optional[QApplication] = None


def set_app(app: QApplication):
    """设置全局应用实例（由 main.py 调用）"""
    global _app_instance
    _app_instance = app


def get_app() -> Optional[QApplication]:
    """获取全局应用实例"""
    return _app_instance

PRIMARY = "#2f6fed"
PRIMARY_LIGHT = "#4a8aff"
PRIMARY_HOVER = "#255bd1"
PRIMARY_PRESSED = "#1f4cb0"
DANGER = "#e05252"
TITLE_BG_TOP = "#1a2744"
TITLE_BG_BOT = "#2a3f6e"
SUCCESS = "#1e9e5a"

# 浅色主题常量
BG_LIGHT = "#f0f4f8"
BG_CARD = "#ffffff"
BORDER = "#dce3ee"
BORDER_LIGHT = "#e8edf5"
TEXT_MAIN = "#1e2a38"
TEXT_SUB = "#6b7c93"
TEXT_MUTED = "#94a3b8"

# 深色主题常量
BG_DARK = "#1a1d23"
BG_CARD_DARK = "#252830"
BORDER_DARK = "#3d4250"
BORDER_LIGHT_DARK = "#3d4250"
TEXT_MAIN_DARK = "#e2e8f0"
TEXT_SUB_DARK = "#94a3b8"
TEXT_MUTED_DARK = "#64748b"

APP_QSS_LIGHT = f"""
* {{
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    color: {TEXT_MAIN};
    outline: none;
}}
QMainWindow, QDialog {{ background: {BG_LIGHT}; }}

/* ── 渐变标题栏 ───────────────────────────────────── */
QWidget#titleBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {TITLE_BG_TOP}, stop:1 {TITLE_BG_BOT});
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
QWidget#titleBar QLabel {{
    color: #ffffff;
    font-size: 15px;
    font-weight: 600;
    background: transparent;
    letter-spacing: 0.3px;
}}
QWidget#titleBar QPushButton {{
    color: #d0ddf5;
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
}}
QWidget#titleBar QPushButton:hover {{
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.28);
}}
QWidget#titleBar QPushButton:pressed {{
    background: rgba(0, 0, 0, 0.3);
}}

/* ── 标签 ─────────────────────────────────────────── */
QLabel {{ background: transparent; }}
QLabel#fieldLabel {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_SUB};
    letter-spacing: 0.4px;
    margin-top: 6px;
}}
QLabel#progressLabel {{
    font-size: 13px;
    color: {TEXT_MAIN};
    padding: 4px 2px;
}}
QLabel#timeLabel {{
    font-size: 11px;
    color: {TEXT_MUTED};
}}
QLabel#doneLabel {{
    color: {SUCCESS};
    font-weight: 700;
    font-size: 13px;
    padding: 4px 2px;
}}

/* ── 输入框 ───────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_CARD};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY};
    selection-color: #ffffff;
}}
QLineEdit:hover, QTextEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {PRIMARY_LIGHT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {PRIMARY};
    padding: 7px 11px;
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
    border-left: 1px solid {BORDER};
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 5px solid {TEXT_SUB};
    margin-right: 4px;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {PRIMARY};
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}}

/* ── 按钮 ─────────────────────────────────────────── */
QPushButton {{
    background: {BG_CARD};
    border: 1.5px solid {BORDER};
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 500;
    color: {TEXT_MAIN};
}}
QPushButton:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY};
    background: rgba(47, 111, 237, 0.04);
}}
QPushButton:pressed {{
    background: rgba(47, 111, 237, 0.1);
}}
QPushButton:disabled {{
    background: #f0f3f8;
    border-color: {BORDER_LIGHT};
    color: {TEXT_MUTED};
}}

QPushButton#primaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY}, stop:1 {PRIMARY_LIGHT});
    color: #ffffff;
    border: none;
    font-size: 14px;
    font-weight: 700;
    padding: 11px 24px;
    border-radius: 10px;
    letter-spacing: 0.3px;
}}
QPushButton#primaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY_HOVER}, stop:1 {PRIMARY});
}}
QPushButton#primaryBtn:pressed {{
    background: {PRIMARY_PRESSED};
}}
QPushButton#primaryBtn:disabled {{
    background: #c8d6ef;
    color: #8fa4cc;
}}

/* ── 进度条 ───────────────────────────────────────── */
QProgressBar {{
    background: #e2e8f0;
    border: none;
    border-radius: 8px;
    height: 12px;
    text-align: center;
    font-size: 11px;
    color: #ffffff;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY_HOVER}, stop:1 {PRIMARY_LIGHT});
    border-radius: 8px;
}}

/* ── 分组框 ───────────────────────────────────────── */
QGroupBox {{
    font-weight: 600;
    border: 1.5px solid {BORDER};
    border-radius: 14px;
    margin-top: 16px;
    padding: 16px 14px 12px 14px;
    background: {BG_CARD};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    top: -10px;
    padding: 0 10px;
    color: {PRIMARY};
    font-size: 14px;
}}

/* ── 预览浏览器 ───────────────────────────────────── */
QTextBrowser {{
    background: {BG_CARD};
    border: 1.5px solid {BORDER};
    border-radius: 14px;
    padding: 12px;
}}

/* ── 状态栏 ───────────────────────────────────────── */
QStatusBar {{
    background: {BG_CARD};
    border-top: 1px solid {BORDER};
    color: {TEXT_SUB};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ── 滚动条 ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: #b0bec5;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #b0bec5;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── 消息框 / 提示 ───────────────────────────────── */
QMessageBox {{
    background: {BG_CARD};
}}
QToolTip {{
    background: {TITLE_BG_TOP};
    color: #ffffff;
    border: none;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 12px;
}}
"""

APP_QSS_DARK = f"""
* {{
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    color: {TEXT_MAIN_DARK};
    outline: none;
}}
QMainWindow, QDialog {{ background: {BG_DARK}; }}

/* ── 渐变标题栏 ───────────────────────────────────── */
QWidget#titleBar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #0f1218, stop:1 #1e2535);
    border-bottom: 1px solid rgba(255,255,255,0.05);
}}
QWidget#titleBar QLabel {{
    color: #e2e8f0;
    font-size: 15px;
    font-weight: 600;
    background: transparent;
    letter-spacing: 0.3px;
}}
QWidget#titleBar QPushButton {{
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 7px 16px;
    font-size: 13px;
}}
QWidget#titleBar QPushButton:hover {{
    background: rgba(255, 255, 255, 0.12);
    color: #e2e8f0;
    border-color: rgba(255, 255, 255, 0.2);
}}
QWidget#titleBar QPushButton:pressed {{
    background: rgba(0, 0, 0, 0.4);
}}

/* ── 标签 ─────────────────────────────────────────── */
QLabel {{ background: transparent; }}
QLabel#fieldLabel {{
    font-size: 12px;
    font-weight: 600;
    color: {TEXT_SUB_DARK};
    letter-spacing: 0.4px;
    margin-top: 6px;
}}
QLabel#progressLabel {{
    font-size: 13px;
    color: {TEXT_MAIN_DARK};
    padding: 4px 2px;
}}
QLabel#timeLabel {{
    font-size: 11px;
    color: {TEXT_MUTED_DARK};
}}
QLabel#doneLabel {{
    color: {SUCCESS};
    font-weight: 700;
    font-size: 13px;
    padding: 4px 2px;
}}

/* ── 输入框 ───────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {BG_CARD_DARK};
    border: 1.5px solid {BORDER_DARK};
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {PRIMARY};
    selection-color: #ffffff;
}}
QLineEdit:hover, QTextEdit:hover, QSpinBox:hover, QComboBox:hover {{
    border-color: {PRIMARY_LIGHT};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 2px solid {PRIMARY};
    padding: 7px 11px;
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
    border-left: 1px solid {BORDER_DARK};
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 5px solid {TEXT_SUB_DARK};
    margin-right: 4px;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD_DARK};
    border: 1px solid {BORDER_DARK};
    border-radius: 8px;
    selection-background-color: {PRIMARY};
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}}

/* ── 按钮 ─────────────────────────────────────────── */
QPushButton {{
    background: {BG_CARD_DARK};
    border: 1.5px solid {BORDER_DARK};
    border-radius: 10px;
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 500;
    color: {TEXT_MAIN_DARK};
}}
QPushButton:hover {{
    border-color: {PRIMARY};
    color: {PRIMARY_LIGHT};
    background: rgba(47, 111, 237, 0.08);
}}
QPushButton:pressed {{
    background: rgba(47, 111, 237, 0.15);
}}
QPushButton:disabled {{
    background: #1e2228;
    border-color: {BORDER_DARK};
    color: {TEXT_MUTED_DARK};
}}

QPushButton#primaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY}, stop:1 {PRIMARY_LIGHT});
    color: #ffffff;
    border: none;
    font-size: 14px;
    font-weight: 700;
    padding: 11px 24px;
    border-radius: 10px;
    letter-spacing: 0.3px;
}}
QPushButton#primaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY_HOVER}, stop:1 {PRIMARY});
}}
QPushButton#primaryBtn:pressed {{
    background: {PRIMARY_PRESSED};
}}
QPushButton#primaryBtn:disabled {{
    background: #2a3040;
    color: #5a6a8a;
}}

/* ── 进度条 ───────────────────────────────────────── */
QProgressBar {{
    background: #2a2f38;
    border: none;
    border-radius: 8px;
    height: 12px;
    text-align: center;
    font-size: 11px;
    color: #ffffff;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {PRIMARY_HOVER}, stop:1 {PRIMARY_LIGHT});
    border-radius: 8px;
}}

/* ── 分组框 ───────────────────────────────────────── */
QGroupBox {{
    font-weight: 600;
    border: 1.5px solid {BORDER_DARK};
    border-radius: 14px;
    margin-top: 16px;
    padding: 16px 14px 12px 14px;
    background: {BG_CARD_DARK};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    top: -10px;
    padding: 0 10px;
    color: {PRIMARY_LIGHT};
    font-size: 14px;
}}

/* ── 预览浏览器 ───────────────────────────────────── */
QTextBrowser {{
    background: {BG_CARD_DARK};
    border: 1.5px solid {BORDER_DARK};
    border-radius: 14px;
    padding: 12px;
}}

/* ── 状态栏 ───────────────────────────────────────── */
QStatusBar {{
    background: {BG_CARD_DARK};
    border-top: 1px solid {BORDER_DARK};
    color: {TEXT_SUB_DARK};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ── 滚动条 ───────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER_DARK};
    border-radius: 4px;
    min-height: 36px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4a5568;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER_DARK};
    border-radius: 4px;
    min-width: 36px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #4a5568;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── 消息框 / 提示 ───────────────────────────────── */
QMessageBox {{
    background: {BG_CARD_DARK};
}}
QToolTip {{
    background: #1e2535;
    color: #e2e8f0;
    border: none;
    padding: 5px 10px;
    border-radius: 6px;
    font-size: 12px;
}}
"""


def apply_theme(app, theme_mode="light"):
    """应用全局主题：QSS + Fusion 调色板兜底。
    
    参数:
        app: QApplication 实例
        theme_mode: "light" 或 "dark"
    """
    fusion_style = QStyleFactory.create("Fusion")
    if fusion_style:
        app.setStyle(fusion_style)
    palette = app.palette()
    
    if theme_mode == "dark":
        bg = BG_DARK
        card = BG_CARD_DARK
        text = TEXT_MAIN_DARK
        sub = TEXT_SUB_DARK
        muted = TEXT_MUTED_DARK
        border = BORDER_DARK
    else:
        bg = BG_LIGHT
        card = BG_CARD
        text = TEXT_MAIN
        sub = TEXT_SUB
        muted = TEXT_MUTED
        border = BORDER
    
    palette.setColor(QPalette.ColorRole.Window, QColor(bg))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(text))
    palette.setColor(QPalette.ColorRole.Base, QColor(card))
    palette.setColor(QPalette.ColorRole.Text, QColor(text))
    palette.setColor(QPalette.ColorRole.Button, QColor(card))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)
    
    qss = APP_QSS_DARK if theme_mode == "dark" else APP_QSS_LIGHT
    app.setStyleSheet(qss)
