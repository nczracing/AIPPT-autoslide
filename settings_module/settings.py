# -*- coding: utf-8 -*-
"""
配置管理模块
负责用户设置、AI接口配置、数据存储
"""
import json
import os
import platform
from pathlib import Path
from typing import Optional


class Settings:
    """应用设置管理器"""

    def __init__(self):
        # 优先使用用户主目录下的配置，确保跨平台和重启后保留
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings = self._load()

    def _get_config_dir(self) -> Path:
        """获取配置目录，确保跨平台兼容"""
        if getattr(__import__('sys'), 'frozen', False):
            # exe模式：使用用户目录，避免重装后丢失配置
            system = platform.system()
            if system == 'Windows':
                app_data = os.environ.get('APPDATA', '')
                return Path(app_data) / 'AutoSlide'
            elif system == 'Darwin':  # macOS
                return Path.home() / 'Library' / 'Application Support' / 'AutoSlide'
            else:  # Linux
                return Path.home() / '.config' / 'AutoSlide'
        else:
            # 源码模式：项目目录下
            return Path(__file__).parent.parent / "configs"

    def _load(self) -> dict:
        """加载配置，带默认值兜底"""
        default = self._default_settings()
        if not self.config_file.exists():
            return default
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # 合并默认值，避免旧配置缺少新字段
            for section in default:
                if section not in loaded:
                    loaded[section] = default[section]
                else:
                    for key in default[section]:
                        if key not in loaded[section]:
                            loaded[section][key] = default[section][key]
            return loaded
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_file}: {e}")
            return default

    def _default_settings(self) -> dict:
        """默认配置"""
        return {
            "ai": {
                "provider": "openai",
                "model": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "max_tokens": 4096,
                "temperature": 0.7,
            },
            "ppt": {
                "language": "zh",
                "theme": "business",
                "default_pages": 10,
                "font_family": "Microsoft YaHei",
                "enable_images": True,
                # 图像生成服务：agnes（推荐，免费高清）/ openai / custom
                "image_provider": "agnes",
                "image_model": "agnes-image-2.1-flash",
                "image_base_url": "https://apihub.agnes-ai.com/v1",
                # 图像独立 API Key（留空则复用 ai.api_key，再兜底环境变量 AGNES_API_KEY）
                "image_api_key": "",
                "image_size": "1024x768",
            },
            "ui": {
                "window_width": 1200,
                "window_height": 800,
                "last_export_dir": "",
                "auto_save": True,
            },
        }

    def get_ai_config(self) -> dict:
        """获取AI配置"""
        return self.settings.get("ai", {}).copy()

    def get_ppt_config(self) -> dict:
        """获取PPT配置"""
        return self.settings.get("ppt", {}).copy()

    def save_ai_config(self, config: dict) -> bool:
        """保存AI配置"""
        self.settings["ai"] = {**self.get_ai_config(), **config}
        return self._save()

    def save_ppt_config(self, config: dict) -> bool:
        """保存PPT配置"""
        self.settings["ppt"] = {**self.get_ppt_config(), **config}
        return self._save()

    def _save(self) -> bool:
        """安全保存配置到文件（原子写入）"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.config_file.with_suffix('.json.tmp')
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.config_file)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def export_config(self, output_path: str) -> bool:
        """导出配置到指定文件"""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting config: {e}")
            return False

    def import_config(self, input_path: str) -> bool:
        """从文件导入配置（覆盖当前配置）"""
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                imported = json.load(f)
            # 验证基本结构
            if "ai" in imported and "ppt" in imported:
                self.settings = imported
                return self._save()
            return False
        except Exception as e:
            print(f"Error importing config: {e}")
            return False

    def get_ui_config(self) -> dict:
        """获取UI配置"""
        return self.settings.get("ui", {}).copy()

    def save_ui_config(self, config: dict) -> bool:
        """保存UI配置"""
        self.settings["ui"] = {**self.get_ui_config(), **config}
        return self._save()

    def get_config_path(self) -> str:
        """获取配置文件路径"""
        return str(self.config_file)

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        self.settings = self._default_settings()
        return self._save()


# 全局配置实例（单例）
_settings_instance: Optional[Settings] = None


def get_settings() -> Settings:
    """获取全局设置实例（单例模式）"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


def reset_settings():
    """重置全局配置实例（用于测试或配置失效时）"""
    global _settings_instance
    _settings_instance = None
