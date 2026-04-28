#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试winnerpartner的扫描模块
直接扫描图片上的深绿色像素点以及二次验证情况
"""

import sys
import os
import cv2
import numpy as np

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/src')

from game.coordinate_mapper import CoordinateMapper


def generate_board_coordinates(width, height):
    """
    生成361个围棋坐标点的屏幕坐标
    :param width: 图片宽度
    :param height: 图片高度
    :return: 字典，键为坐标标识，值为(x, y)屏幕坐标
    """
    coordinates = {}
    
    # 计算每个格子的宽度和高度
    cell_width = width / 18.0
    cell_height = height / 18.0
    
    # 围棋列坐标（没有i）
    cols = 'abcdefghjklmnopqrst'
    
    # 生成所有361个点的坐标
    for row in range(19):
        for col in range(19):
            # 计算屏幕坐标
            x = int(col * cell_width)
            y = int(row * cell_height)
            coord_key = f"{cols[col]}{19-row}"  # 围棋坐标
            coordinates[coord_key] = (x, y)
            
    return coordinates


def short_scan(img_array, x, y, scan_range=10):
    """
    短扫检查
    :param img_array: 图像数组
    :param x: 中心点x坐标
    :param y: 中心点y坐标
    :param scan_range: 扫描范围
    :return: "skip"表示跳过，"valid"表示有效，None表示继续检查
    """
    height, width = img_array.shape[:2]
    
    # 计算短扫矩形框的边界
    left = max(0, x - scan_range)
    right = min(width - 1, x + scan_range)
    top = max(0, y - scan_range)
    bottom = min(height - 1, y + scan_range)
    
    # 提取短扫区域
    region = img_array[top:bottom+1, left:right+1]
    
    # 定义颜色范围
    # 白色或黑色范围
    lower_white = np.array([200, 200, 200])
    upper_white = np.array([255, 255, 255])
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([50, 50, 50])
    
    # 深绿色范围
    lower_green = np.array([0, 100, 0])
    upper_green = np.array([50, 255, 50])
    
    # 创建掩码
    white_mask = cv2.inRange(region, lower_white, upper_white)
    black_mask = cv2.inRange(region, lower_black, upper_black)
    green_mask = cv2.inRange(region, lower_green, upper_green)
    
    # 计算像素点数量
    white_count = np.count_nonzero(white_mask)
    black_count = np.count_nonzero(black_mask)
    green_count = np.count_nonzero(green_mask)
    
    WHITE_BLACK_THRESHOLD = 300
    GREEN_THRESHOLD = 300
    
    # 判断逻辑
    if white_count + black_count > WHITE_BLACK_THRESHOLD:
        # 超过300个白色或黑色像素点，标记为下次不再扫描
        return "skip"
    elif green_count > GREEN_THRESHOLD:
        # 超过300个深绿色像素点，确认并输出该坐标
        return "valid"
    
    return None  # 继续检查


def test_scan_image(image_path):
    """测试扫描单张图片"""
    print(f"正在测试扫描图片: {image_path}")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        print(f"错误: 文件 {image_path} 不存在")
        return
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"错误: 无法读取图片 {image_path}")
        return
    
    height, width = img.shape[:2]
    print(f"图片尺寸: {width}x{height}")
    
    # 创建坐标映射器
    coordinate_mapper = CoordinateMapper()
    
    # 设置一个假的红色矩形区域（整个图片）
    coordinate_mapper.set_red_rectangle(0, 0, width, height)
    
    # 生成361个围棋坐标点的屏幕坐标
    coordinates = generate_board_coordinates(width, height)
    
    # 存储所有检测到的有效坐标
    valid_coordinates = []
    skip_count = 0
    
    # 对每个坐标点进行短扫检查
    for coord_key, (x, y) in coordinates.items():
        # 执行短扫检查
        scan_result = short_scan(img, x, y)
        
        if scan_result == "skip":
            # 标记为跳过
            skip_count += 1
        elif scan_result == "valid":
            # 确认并输出该坐标
            coordinate = coordinate_mapper.screen_to_board(x, y)
            if coordinate:
                valid_coordinates.append(coordinate)
    
    print(f"跳过的坐标点数量: {skip_count}")
    print(f"检测到的有效坐标数量: {len(valid_coordinates)}")
    if valid_coordinates:
        print(f"有效坐标: {', '.join(valid_coordinates)}")
    else:
        print("未检测到有效坐标")


def main():
    """主函数"""
    print("Winner Partner 图片扫描测试 (新逻辑)")
    print("=" * 50)
    
    # 测试图片路径
    image1_path = os.path.join(os.path.dirname(__file__), "1.jpeg")
    image2_path = os.path.join(os.path.dirname(__file__), "2.jpeg")
    
    # 测试第一张图片
    test_scan_image(image1_path)
    
    print("\n" + "=" * 50)
    
    # 测试第二张图片
    test_scan_image(image2_path)
    
    print("\n测试完成")


if __name__ == "__main__":
    main()