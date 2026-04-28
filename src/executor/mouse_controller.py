#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鼠标控制模块
负责模拟鼠标操作
"""

import pyautogui
import time


class MouseController:
    """鼠标控制器类"""

    def __init__(self):
        """初始化鼠标控制器"""
        # 设置pyautogui的延迟
        pyautogui.PAUSE = 0.1
        pyautogui.FAILSAFE = True

    def double_click_at_coordinate(self, coordinate, coordinate_mapper):
        """
        在指定坐标处双击
        :param coordinate: 围棋坐标 (如 "a15")
        :param coordinate_mapper: 坐标映射器
        :return: 操作结果字典
        """
        try:
            # 将围棋坐标转换为屏幕坐标
            screen_pos = coordinate_mapper.board_to_screen(coordinate)
            if not screen_pos:
                return {
                    "success": False,
                    "message": "坐标转换失败"
                }
                
            x, y = screen_pos
            
            # 移动鼠标到指定位置
            pyautogui.moveTo(x, y)
            
            # 双击操作
            pyautogui.doubleClick()
            
            return {
                "success": True,
                "message": f"已在坐标{coordinate}({x}, {y})处双击"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"鼠标操作失败: {str(e)}"
            }

    def click_at_coordinate(self, coordinate, coordinate_mapper):
        """
        在指定坐标处单击
        :param coordinate: 围棋坐标 (如 "a15")
        :param coordinate_mapper: 坐标映射器
        :return: 操作结果字典
        """
        try:
            # 将围棋坐标转换为屏幕坐标
            screen_pos = coordinate_mapper.board_to_screen(coordinate)
            if not screen_pos:
                return {
                    "success": False,
                    "message": "坐标转换失败"
                }
                
            x, y = screen_pos
            
            # 移动鼠标到指定位置
            pyautogui.moveTo(x, y)
            
            # 单击操作
            pyautogui.click()
            
            return {
                "success": True,
                "message": f"已在坐标{coordinate}({x}, {y})处单击"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"鼠标操作失败: {str(e)}"
            }