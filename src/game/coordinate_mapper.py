#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标映射模块
处理围棋坐标与屏幕坐标的转换
"""

class CoordinateMapper:
    """坐标映射器类"""

    def __init__(self):
        """初始化坐标映射器"""
        self.red_rectangle = None
        # 围棋列坐标（没有i）
        self.cols = 'abcdefghjklmnopqrst'
        
    def set_red_rectangle(self, x1, y1, x2, y2):
        """设置红色矩形区域"""
        self.red_rectangle = (x1, y1, x2, y2)
        
    def screen_to_board(self, x, y):
        """屏幕坐标转换为围棋坐标"""
        if not self.red_rectangle:
            return None
            
        x1, y1, x2, y2 = self.red_rectangle
        
        # 确保坐标顺序正确
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        
        # 检查坐标是否在红色矩形区域内
        if not (left <= x <= right and top <= y <= bottom):
            return None
            
        # 计算每个格子的宽度和高度
        rect_width = right - left
        rect_height = bottom - top
        cell_width = rect_width / 18.0  # 19个点，18个间隔
        cell_height = rect_height / 18.0
        
        # 防止除零错误
        if cell_width == 0 or cell_height == 0:
            return None
            
        # 转换为围棋坐标 (列, 行)
        # 列: a-t (从左到右)
        col_index = int(round((x - left) / cell_width))
        if col_index < 0:
            col_index = 0
        elif col_index > 18:
            col_index = 18
        col = self.cols[col_index]
        
        # 行: 1-19 (从上到下，即从低y到高y)
        row_index = int(round((y - top) / cell_height))
        if row_index < 0:
            row_index = 0
        elif row_index > 18:
            row_index = 18
        row = 19 - row_index  # 围棋行数从上到下是1-19
            
        return f"{col}{row}"
        
    def board_to_screen(self, coordinate):
        """围棋坐标转换为屏幕坐标"""
        if not self.red_rectangle or not coordinate:
            return None
            
        coordinate = coordinate.strip().lower()
        if len(coordinate) < 2:
            return None
            
        col_char = coordinate[0]
        row_str = coordinate[1:]
        
        # 验证列坐标
        if col_char not in self.cols:
            return None
            
        # 验证行坐标
        try:
            row = int(row_str)
            if row < 1 or row > 19:
                return None
        except ValueError:
            return None
            
        x1, y1, x2, y2 = self.red_rectangle
        
        # 确保坐标顺序正确
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        
        # 计算每个格子的宽度和高度
        rect_width = right - left
        rect_height = bottom - top
        cell_width = rect_width / 18.0
        cell_height = rect_height / 18.0
        
        # 计算围棋坐标在屏幕上的位置
        # 列: a-t 对应 0-18
        col_index = self.cols.index(col_char)
        x = left + col_index * cell_width
        
        # 行: 1-19 对应 0-18 (从上到下)
        y = top + (19 - row) * cell_height
        
        return (int(x), int(y))