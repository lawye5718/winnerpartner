#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Winner 2.0 主程序入口
"""

import sys
import os

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from PyQt5.QtWidgets import QApplication


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()