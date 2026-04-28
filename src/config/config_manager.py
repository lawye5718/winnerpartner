#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
负责系统配置的读取和保存
"""

import json
import os


class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_file="config.json"):
        """初始化配置管理器"""
        self.config_file = config_file
        self.config = {}
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                self.config = {
                    "system": {
                        "ui": {
                            "theme": "light",
                            "window_topmost": True
                        },
                        "monitor": {
                            "red_rectangle": None,
                            "interval": 20
                        },
                        "log": {
                            "counter": 1,
                            "last_source": None
                        }
                    }
                }
                self.save_config()
        except Exception as e:
            print(f"加载配置文件出错: {e}")
            self.config = {}

    def save_config(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件出错: {e}")

    def get_system_setting(self, key, default=None):
        """获取系统设置"""
        try:
            keys = key.split('.')
            value = self.config.get("system", {})
            for k in keys:
                value = value.get(k, {})
            return value if value != {} else default
        except Exception:
            return default

    def set_system_setting(self, key, value):
        """设置系统配置"""
        try:
            keys = key.split('.')
            if "system" not in self.config:
                self.config["system"] = {}
            
            # 逐层创建嵌套字典
            current = self.config["system"]
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # 设置最终值
            current[keys[-1]] = value
            
            # 保存配置
            self.save_config()
        except Exception as e:
            print(f"设置配置出错: {e}")

    def get_all_config(self):
        """获取所有配置"""
        return self.config

    def set_all_config(self, config):
        """设置所有配置"""
        self.config = config
        self.save_config()