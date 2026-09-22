# -*- coding: utf-8 -*-
import logging
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox, QApplication
from PyQt6.QtCore import Qt, QEvent
from settings_module import get_settings
from ui.settings_dialog import SettingsDialog
from ui.generator_widget import GeneratorWidget
from ui.preview_widget import PreviewWidget
from ui.theme import apply_theme, BG_LIGHT, TEXT_MAIN, PRIMARY
import sys


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = get_settings()
        self.setWindowTitle('AutoSlide - AI PPT 生成器')
        self.setMinimumSize(1200, 800)
        self.init_ui()
        self.apply_theme()

    def apply_theme(self):
        """应用当前主题（浅色/深色）"""
        ui_config = self.settings.get_ui_config()
        theme_mode = ui_config.get('theme', 'light')

        # 保存当前主题到内存，供其他组件使用
        self.current_theme = theme_mode

        # 更新按钮文字
        self.theme_btn.setText('☀️ 浅色' if theme_mode == 'dark' else '🌙 深色')

        # 重新应用主题（apply_theme 已处理调色板和QSS）
        apply_theme(QApplication.instance(), theme_mode)

    def closeEvent(self, event: QEvent):
        """窗口关闭时清理后台线程"""
        try:
            if hasattr(self, 'generator'):
                thread = self.generator.thread
                if thread is not None and thread.isRunning():
                    logger = logging.getLogger('autoslide')
                    logger.info("关闭窗口，等待生成线程结束...")
                    thread.wait(5000)  # 等待线程自然结束
                    if thread.isRunning():
                        logger.warning("生成线程未能在5秒内退出，强制终止")
                        thread.terminate()
                        thread.wait()
        except Exception as e:
            logging.getLogger('autoslide').warning(f"关闭时清理线程异常: {e}")
        event.accept()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        title_bar = QWidget()
        title_bar.setObjectName('titleBar')
        title_bar.setFixedHeight(54)
        tl = QHBoxLayout(title_bar)
        tl.setContentsMargins(18, 6, 18, 6)
        tl.setSpacing(10)
        logo = QLabel('◈')
        logo.setStyleSheet(
            'font-size: 24px; '
            'color: #6ea0ff; '
            'background: transparent; '
            'font-weight: bold;'
        )
        tl.addWidget(logo)
        tl.addWidget(QLabel('AutoSlide · AI PPT 生成器'))
        tl.addStretch()
        # 主题切换按钮
        self.theme_btn = QPushButton('🌙 深色')
        self.theme_btn.setCursor(self.theme_btn.cursor())
        self.theme_btn.clicked.connect(self.toggle_theme)
        tl.addWidget(self.theme_btn)
        settings_btn = QPushButton('设置 (Settings)')
        settings_btn.setCursor(settings_btn.cursor())
        settings_btn.clicked.connect(self.open_settings)
        tl.addWidget(settings_btn)
        about_btn = QPushButton('关于 (About)')
        about_btn.clicked.connect(self.show_about)
        tl.addWidget(about_btn)
        layout.addWidget(title_bar)
        content = QHBoxLayout()
        content.setContentsMargins(10, 10, 10, 10)
        content.setSpacing(10)
        self.generator = GeneratorWidget(self)
        self.preview = PreviewWidget(self)
        # 连接预览信号（替代依赖 parent() 层级的脆弱方式）
        self.generator.preview_requested.connect(self.preview.update_preview)
        content.addWidget(self.generator, stretch=1)
        content.addWidget(self.preview, stretch=2)
        layout.addLayout(content)
        self.statusBar().showMessage('就绪 - 请先配置 AI 设置')

    def toggle_theme(self):
        """切换浅色/深色主题"""
        ui_config = self.settings.get_ui_config()
        current = ui_config.get('theme', 'light')
        new_theme = 'dark' if current == 'light' else 'light'
        self.settings.save_ui_config({'theme': new_theme})
        self.current_theme = new_theme
        # 更新按钮文字
        self.theme_btn.setText('☀️ 浅色' if new_theme == 'dark' else '🌙 深色')
        # 重新应用主题
        apply_theme(QApplication.instance(), new_theme)
        self.statusBar().showMessage(f'已切换到{"深色" if new_theme == "dark" else "浅色"}模式')
        logging.getLogger('autoslide').info(f"主题切换: {new_theme}")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings = get_settings()

    def show_about(self):
        QMessageBox.about(self, '关于 AutoSlide', 'AutoSlide v1.1\nAI 驱动的 PPT 生成器')

    def update_preview(self, presentation):
        """更新预览面板"""
        self.preview.update_preview(presentation)
