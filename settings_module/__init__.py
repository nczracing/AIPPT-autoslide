# -*- coding: utf-8 -*-
"""
配置管理模块入口
"""
from settings_module.settings import Settings, get_settings
from settings_module.models import Slide, Presentation

__all__ = ["Settings", "get_settings", "Slide", "Presentation"]
