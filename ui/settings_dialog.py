# -*- coding: utf-8 -*-
"""
设置对话框
负责AI配置、PPT配置的查看和修改
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QGroupBox, QFormLayout,
    QSlider, QSpinBox, QMessageBox, QFrame, QCheckBox
)
from PyQt6.QtCore import Qt
from settings_module import get_settings


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = get_settings()
        self.setWindowTitle('设置 - AutoSlide')
        self.setMinimumWidth(520)
        self._loading = False  # 加载配置时抑制信号回填，避免覆盖已保存的自定义值
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # === AI配置区域 ===
        ai_group = QGroupBox('AI 配置')
        ai_layout = QFormLayout()
        ai_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(['OpenAI', 'Azure', 'DeepSeek', '自定义 (Custom)'])
        ai_layout.addRow('接口供应商:', self.provider_combo)

        self.model_input = QLineEdit()
        self.model_input.setPlaceholderText('例: gpt-4o, claude-3-opus')
        ai_layout.addRow('模型:', self.model_input)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText('https://api.openai.com/v1')
        ai_layout.addRow('接口地址 (Base URL):', self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText('请输入 API Key')
        ai_layout.addRow('API 密钥 (API Key):', self.api_key_input)

        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 16384)
        self.max_tokens_spin.setValue(4096)
        ai_layout.addRow('最大 Token 数:', self.max_tokens_spin)

        temp_layout = QHBoxLayout()
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(70)
        self.temp_label = QLabel('0.70')
        self.temp_slider.valueChanged.connect(lambda v: self.temp_label.setText(f'{v/100:.2f}'))
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(self.temp_label)
        ai_layout.addRow('温度 (Temperature):', temp_layout)

        ai_group.setLayout(ai_layout)
        layout.addWidget(ai_group)

        # === PPT配置区域 ===
        ppt_group = QGroupBox('PPT 配置')
        ppt_layout = QFormLayout()

        self.ppt_lang_combo = QComboBox()
        self.ppt_lang_combo.addItems(['中文 (Chinese)', '英文 (English)'])
        ppt_layout.addRow('语言:', self.ppt_lang_combo)

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(5, 50)
        self.pages_spin.setValue(10)
        ppt_layout.addRow('默认页数:', self.pages_spin)

        self.enable_images_check = QCheckBox('自动生成插图（AI 配图，失败自动跳过）')
        ppt_layout.addRow('插图:', self.enable_images_check)

        # === 图像生成服务配置（默认推荐 Agnes AI） ===
        self.image_provider_combo = QComboBox()
        self.image_provider_combo.addItems(['Agnes AI（推荐，免费高清）', 'OpenAI', '自定义'])
        self.image_provider_combo.currentIndexChanged.connect(self.on_image_provider_changed)
        ppt_layout.addRow('图像服务:', self.image_provider_combo)

        self.image_model_input = QLineEdit()
        self.image_model_input.setPlaceholderText('agnes-image-2.1-flash')
        ppt_layout.addRow('图像模型:', self.image_model_input)

        self.image_base_url_input = QLineEdit()
        self.image_base_url_input.setPlaceholderText('https://apihub.agnes-ai.com/v1')
        ppt_layout.addRow('图像接口地址 (Base URL):', self.image_base_url_input)

        self.image_api_key_input = QLineEdit()
        self.image_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.image_api_key_input.setPlaceholderText('留空则复用上方 AI Key 或环境变量 AGNES_API_KEY')
        ppt_layout.addRow('图像 API 密钥 (API Key):', self.image_api_key_input)

        self.image_size_combo = QComboBox()
        self.image_size_combo.addItems(['1024x768（横版，推荐）', '1024x1024（方形）'])
        ppt_layout.addRow('图像尺寸:', self.image_size_combo)

        self.agnes_hint = QLabel(
            '推荐 Agnes AI：完全免费、约 10 秒出图、高信息密度与复杂版式表现强。\n'
            '注册入口：https://agnes-ai.com/\n'
            'API 平台（OpenAI 兼容）：https://apihub.agnes-ai.com'
        )
        self.agnes_hint.setWordWrap(True)
        self.agnes_hint.setStyleSheet('color: #1e9e5a; font-size: 12px;')
        ppt_layout.addRow('', self.agnes_hint)

        ppt_group.setLayout(ppt_layout)
        layout.addWidget(ppt_group)

        # === 配置位置提示 ===
        config_frame = QFrame()
        config_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        config_frame.setStyleSheet(
            'QFrame { background: #f0f7ff; border: 1.5px solid #d0e3ff; '
            'border-radius: 10px; padding: 10px; }'
            'QFrame QLabel { color: #4a6fa5; font-size: 12px; }'
        )
        config_layout = QHBoxLayout(config_frame)
        self.config_path_label = QLabel('')
        self.config_path_label.setWordWrap(True)
        config_layout.addWidget(self.config_path_label)
        layout.addWidget(config_frame)

        # === 按钮区域 ===
        btn_layout = QHBoxLayout()

        test_btn = QPushButton('测试连接')
        test_btn.clicked.connect(self.test_connection)
        btn_layout.addWidget(test_btn)

        reset_btn = QPushButton('恢复默认')
        reset_btn.clicked.connect(self.reset_to_default)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton('取消')
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        self.save_btn = QPushButton('保存')
        self.save_btn.setObjectName('primaryBtn')
        self.save_btn.clicked.connect(self.save_settings)
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(btn_layout)

        self.load_settings()
        self.update_config_path_label()

    def on_image_provider_changed(self, idx):
        """图像服务切换时自动填充对应预设（model + base_url）。"""
        if self._loading:
            return
        presets = {
            0: ("agnes-image-2.1-flash", "https://apihub.agnes-ai.com/v1"),
            1: ("gpt-image-1", "https://api.openai.com/v1"),
        }
        if idx in presets:
            model, base = presets[idx]
            self.image_model_input.setText(model)
            self.image_base_url_input.setText(base)

    def load_settings(self):
        """加载当前配置到界面"""
        ai = self.settings.get_ai_config()
        ppt = self.settings.get_ppt_config()

        self._loading = True
        try:
            self.model_input.setText(ai.get('model', 'gpt-4o'))
            self.base_url_input.setText(ai.get('base_url', 'https://api.openai.com/v1'))
            self.api_key_input.setText(ai.get('api_key', ''))
            self.max_tokens_spin.setValue(ai.get('max_tokens', 4096))
            self.temp_slider.setValue(int(ai.get('temperature', 0.7) * 100))

            lang_val = ppt.get('language', 'zh')
            idx = 0 if lang_val == 'zh' else 1
            self.ppt_lang_combo.setCurrentIndex(idx)
            self.pages_spin.setValue(ppt.get('default_pages', 10))
            self.enable_images_check.setChecked(ppt.get('enable_images', True))

            provider = ppt.get('image_provider', 'agnes')
            # P1-B：归一化 provider，旧非法值（如 "dall-e-3"）回退 Agnes，避免界面显示与配置不一致
            if provider not in ('agnes', 'openai', 'custom'):
                provider = 'agnes'
            provider_idx = {'agnes': 0, 'openai': 1, 'custom': 2}.get(provider, 0)
            self.image_provider_combo.setCurrentIndex(provider_idx)
            self.image_model_input.setText(ppt.get('image_model', 'agnes-image-2.1-flash'))
            self.image_base_url_input.setText(ppt.get('image_base_url', 'https://apihub.agnes-ai.com/v1'))
            self.image_api_key_input.setText(ppt.get('image_api_key', ''))
            size = ppt.get('image_size', '1024x768')
            size_idx = 1 if size == '1024x1024' else 0
            self.image_size_combo.setCurrentIndex(size_idx)
        finally:
            self._loading = False

    def update_config_path_label(self):
        """更新配置路径显示"""
        self.config_path_label.setText(f'配置文件路径:\n{self.settings.get_config_path()}')

    def save_settings(self):
        """保存设置"""
        ai_config = {
            'model': self.model_input.text().strip(),
            'base_url': self.base_url_input.text().strip(),
            'api_key': self.api_key_input.text(),
            'max_tokens': self.max_tokens_spin.value(),
            'temperature': self.temp_slider.value() / 100,
        }
        success = self.settings.save_ai_config(ai_config)

        provider_map = {0: 'agnes', 1: 'openai', 2: 'custom'}
        ppt_config = {
            'language': 'zh' if self.ppt_lang_combo.currentIndex() == 0 else 'en',
            'default_pages': self.pages_spin.value(),
            'enable_images': self.enable_images_check.isChecked(),
            'image_provider': provider_map.get(self.image_provider_combo.currentIndex(), 'agnes'),
            'image_model': self.image_model_input.text().strip() or 'agnes-image-2.1-flash',
            'image_base_url': self.image_base_url_input.text().strip() or 'https://apihub.agnes-ai.com/v1',
            'image_api_key': self.image_api_key_input.text(),
            'image_size': '1024x1024' if self.image_size_combo.currentIndex() == 1 else '1024x768',
        }
        self.settings.save_ppt_config(ppt_config)

        if success:
            QMessageBox.information(
                self,
                '保存成功',
                f'✅ 配置已保存！\n\n下次启动时会自动加载。\n\n配置文件位置：\n{self.settings.get_config_path()}'
            )
            self.accept()
        else:
            QMessageBox.critical(self, '保存失败', '配置保存失败，请检查权限！')

    def reset_to_default(self):
        """恢复默认配置"""
        reply = QMessageBox.question(
            self,
            '确认重置',
            '确定要恢复所有设置为默认值吗？\n当前配置将被覆盖。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings.reset_to_default()
            self.load_settings()
            self.update_config_path_label()
            QMessageBox.information(self, '重置成功', '已恢复默认配置！')

    def test_connection(self):
        """测试API连接"""
        from core.ai_client import AIClient
        try:
            client = AIClient()
            resp = client.chat([{'role': 'user', 'content': 'Hi'}], max_tokens=10)
            QMessageBox.information(self, '连接成功', f'✅ API连接正常！\n\n响应摘要:\n{resp[:100]}')
        except Exception as e:
            QMessageBox.critical(self, '连接失败', f'❌ API连接异常：\n{str(e)}')
