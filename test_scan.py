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


def verify_pixel_point(img_array, start_x, start_y):
    """
    二次验证：向上逐个像素检测
    :param img_array: 图像数组 (BGR格式)
    :param start_x: 起始x坐标
    :param start_y: 起始y坐标
    :return: True表示验证通过，False表示验证失败
    """
    height = img_array.shape[0]
    
    # 向上遍历（y递减），最多向上检查50个像素
    for y in range(start_y, max(-1, start_y - 50), -1):
        if y >= height or y < 0:
            break
            
        pixel = img_array[y, start_x]
        # OpenCV 默认读取的是 BGR 格式
        b, g, r = int(pixel[0]), int(pixel[1]), int(pixel[2])
        
        # 判断颜色（根据实际棋子颜色调整阈值）
        is_green = g > 100 and b < 80 and r < 80
        is_white = b > 200 and g > 200 and r > 200
        is_black = b < 50 and g < 50 and r < 50
        
        if is_green or is_black:
            continue  # 遇到绿色或黑色，继续向上寻找不同颜色
        elif is_white:
            return True  # 遇到白色像素点，标记正确
        else:
            return False  # 出现其他颜色，标记错误
            
    return False


def short_scan(img_array, x, y, scan_range=10, rect_width=None):
    """
    短扫检查
    :param img_array: 图像数组
    :param x: 中心点x坐标
    :param y: 中心点y坐标
    :param scan_range: 扫描范围（如果未提供rect_width则使用此值）
    :param rect_width: 红色矩形宽度（用于动态计算阈值）
    :return: "skip"表示跳过，"valid"表示有效，None表示继续检查
    """
    height, width = img_array.shape[:2]
    
    # 动态计算扫描范围和阈值
    if rect_width:
        cell_width = rect_width / 18.0
        dynamic_scan_radius = max(3, int(cell_width * 0.4))  # 动态半径，不超过格子一半
        scan_area = (2 * dynamic_scan_radius + 1) ** 2
        green_threshold = int(scan_area * 0.6)  # 动态阈值（面积的60%）
        white_black_threshold = int(scan_area * 0.7)  # 动态阈值（面积的70%）
    else:
        dynamic_scan_radius = scan_range
        scan_area = (2 * scan_range + 1) ** 2
        green_threshold = 300
        white_black_threshold = 300
    
    # 计算短扫矩形框的边界
    left = max(0, x - dynamic_scan_radius)
    right = min(width - 1, x + dynamic_scan_radius)
    top = max(0, y - dynamic_scan_radius)
    bottom = min(height - 1, y + dynamic_scan_radius)
    
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
    
    # 判断逻辑
    if white_count + black_count > white_black_threshold:
        # 超过阈值的白色或黑色像素点，标记为下次不再扫描
        return "skip"
    elif green_count > green_threshold:
        # 超过阈值的深绿色像素点，进行二次验证
        if verify_pixel_point(img_array, x, y):
            return "valid"
        else:
            return None  # 二次验证失败，继续检查
    
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
        # 执行短扫检查（传入rect_width以启用动态阈值）
        scan_result = short_scan(img, x, y, rect_width=width)
        
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