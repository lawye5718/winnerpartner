#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区域选择模块
负责在屏幕上选择和定义监控区域
"""

import cv2
import numpy as np
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt5.QtGui import QCursor, QPixmap, QColor, QPainter, QPen, QRegion
from PyQt5.QtCore import Qt, QRect, QPoint
import sys


class RegionSelector(QWidget):
    """区域选择器类"""

    def __init__(self, color="red"):
        """
        初始化区域选择器
        :param color: 矩形颜色 ("red" 或 "green")
        """
        super().__init__()
        self.color = color
        self.rectangle = None  # (x1, y1, x2, y2)
        self.dragging = False
        self.resizing = False
        self.drag_start = None
        self.screen_width = 0
        self.screen_height = 0
        self.border_tolerance = 10
        self.selected_callback = None

        # 设置窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)

    def select_region(self, callback=None):
        """
        选择区域
        :param callback: 选择完成后回调函数
        :return: 选择的区域坐标 (x1, y1, x2, y2)
        """
        # 获取屏幕尺寸
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
            
        screen = app.primaryScreen()
        screen_geometry = screen.geometry()
        self.screen_width = screen_geometry.width()
        self.screen_height = screen_geometry.height()
        
        # 设置窗口大小为全屏
        self.setGeometry(screen_geometry)
        
        # 设置回调函数
        self.selected_callback = callback
        
        # 显示窗口
        self.show()
        self.raise_()
        self.activateWindow()
        
        return self.rectangle

    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制半透明遮罩
        overlay_color = QColor(0, 0, 0, 100)  # 半透明黑色
        painter.fillRect(self.rect(), overlay_color)
        
        if self.rectangle:
            x1, y1, x2, y2 = self.rectangle
            # 清除矩形区域的遮罩
            clear_region = QRegion(QRect(x1, y1, x2-x1, y2-y1))
            painter.setClipRegion(clear_region, Qt.NoClip)
            painter.fillRect(x1, y1, x2-x1, y2-y1, QColor(0, 0, 0, 0))  # 透明
            
            # 绘制矩形边框
            pen = QPen()
            if self.color == "red":
                pen.setColor(QColor(255, 0, 0))
            else:
                pen.setColor(QColor(0, 255, 0))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setClipRegion(QRegion(self.rect()), Qt.ReplaceClip)
            painter.drawRect(x1, y1, x2-x1, y2-y1)
            
            # 绘制角标
            self._draw_corner_handles(painter, x1, y1, x2, y2)

    def _draw_corner_handles(self, painter, x1, y1, x2, y2):
        """绘制角标"""
        handle_size = 10
        pen = QPen()
        if self.color == "red":
            pen.setColor(QColor(255, 0, 0))
        else:
            pen.setColor(QColor(0, 255, 0))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # 绘制四个角的小矩形
        painter.drawRect(x1 - handle_size//2, y1 - handle_size//2, handle_size, handle_size)
        painter.drawRect(x2 - handle_size//2, y1 - handle_size//2, handle_size, handle_size)
        painter.drawRect(x1 - handle_size//2, y2 - handle_size//2, handle_size, handle_size)
        painter.drawRect(x2 - handle_size//2, y2 - handle_size//2, handle_size, handle_size)

    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            x, y = event.x(), event.y()
            
            if self.rectangle:
                x1, y1, x2, y2 = self.rectangle
                # 检查是否在边框上
                if self.is_on_border(x, y, x1, y1, x2, y2):
                    self.resizing = True
                    self.drag_start = (x, y)
                    return
                    
                # 检查是否在矩形内部
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.dragging = True
                    self.drag_start = (x, y)
                    return
            
            # 创建新的矩形
            self.rectangle = (x, y, x, y)
            self.drag_start = (x, y)
            self.update()

    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        x, y = event.x(), event.y()
        
        if self.drag_start and (self.dragging or self.resizing):
            start_x, start_y = self.drag_start
            
            if self.resizing and self.rectangle:
                # 调整矩形大小
                x1, y1, x2, y2 = self.rectangle
                # 简化处理，只支持右下角调整大小
                self.rectangle = (x1, y1, max(x1+10, x), max(y1+10, y))
            elif self.dragging and self.rectangle:
                # 移动矩形
                dx = x - start_x
                dy = y - start_y
                x1, y1, x2, y2 = self.rectangle
                width = x2 - x1
                height = y2 - y1
                self.rectangle = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
                self.drag_start = (x, y)
                
            self.update()
        elif self.rectangle:
            # 更新鼠标光标样式
            x1, y1, x2, y2 = self.rectangle
            if self.is_on_border(x, y, x1, y1, x2, y2):
                self.setCursor(Qt.SizeFDiagCursor)
            elif x1 <= x <= x2 and y1 <= y <= y2:
                self.setCursor(Qt.SizeAllCursor)
            else:
                self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.resizing = False
            self.drag_start = None

    def keyPressEvent(self, event):
        """键盘按键事件"""
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.rectangle:
                # 完成选择
                self.close()
                if self.selected_callback:
                    self.selected_callback(self.rectangle)

    def closeEvent(self, event):
        """窗口关闭事件"""
        # 如果没有设置回调函数，直接接受关闭事件
        event.accept()

    def draw_rectangle(self, image, x1, y1, x2, y2):
        """
        在图像上绘制矩形
        :param image: 图像
        :param x1: 左上角x坐标
        :param y1: 左上角y坐标
        :param x2: 右下角x坐标
        :param y2: 右下角y坐标
        :return: 绘制后的图像
        """
        # 创建图像副本
        img = image.copy()
        
        # 根据颜色设置绘制参数
        if self.color == "red":
            color = (0, 0, 255)  # BGR格式的红色
            thickness = 3
        else:  # green
            color = (0, 255, 0)  # BGR格式的绿色
            thickness = 3
            
        # 绘制矩形
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)
        
        return img

    def is_on_border(self, x, y, x1, y1, x2, y2, tolerance=10):
        """
        检查点是否在矩形边框上
        :param x: 点的x坐标
        :param y: 点的y坐标
        :param x1: 矩形左上角x坐标
        :param y1: 矩形左上角y坐标
        :param x2: 矩形右下角x坐标
        :param y2: 矩形右下角y坐标
        :param tolerance: 容差范围
        :return: 是否在边框上
        """
        # 检查是否在右边和下边的垂直线和水平线上（简化处理）
        on_vertical = abs(x - x2) <= tolerance and y1 - tolerance <= y <= y2 + tolerance
        on_horizontal = abs(y - y2) <= tolerance and x1 - tolerance <= x <= x2 + tolerance
        
        return on_vertical or on_horizontal