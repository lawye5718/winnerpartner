#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口界面
提供图形化操作界面
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTextEdit, QGroupBox, 
    QCheckBox, QRadioButton, QComboBox, QSpinBox,
    QLineEdit, QMessageBox, QSystemTrayIcon, QAction, QMenu, QInputDialog
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QIcon
import sys
import os
import numpy as np
import cv2
import json
import subprocess

# 【权限修复】：安全导入 keyboard，防止 Mac 缺少 sudo 权限导致程序崩溃
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config_manager import ConfigManager
from game.coordinate_mapper import CoordinateMapper
from executor.mouse_controller import MouseController
import json


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # 初始化配置管理器
        self.config_manager = ConfigManager()
        
        # 初始化坐标映射器
        self.coordinate_mapper = CoordinateMapper()
        
        # 初始化鼠标控制器
        self.mouse_controller = MouseController()
        
        # 初始化区域选择器
        self.red_selector = None
        
        # 扫描相关参数
        self.GREEN_THRESHOLD = 300  # 绿色像素阈值（全局算法使用）
        
        # 自动扫描定时器
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self.auto_scan_task)
        self.is_auto_scanning = False
        
        # 日志记录相关
        self.log_counter = 1
        self.last_logged_source = None  # 上次记录来源（"text_display" 或 "coordinate_input"）
        
        # 初始化界面
        self.init_ui()
        
        # 加载配置
        self.load_settings()

    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("Winner Partner")
        self.setGeometry(100, 100, 800, 600)
        
        # 设置窗口始终置顶
        if self.config_manager.get_system_setting("ui.window_topmost", True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建顶部控制区域
        self.create_top_control_area(main_layout)
        
        # 创建日志区域
        self.create_log_area(main_layout)
        
        # 创建状态栏
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("就绪")
        
        # 设置系统托盘图标
        self.setup_system_tray()
        
        # 注册全局快捷键 (加入安全判断)
        if HAS_KEYBOARD:
            try:
                keyboard.add_hotkey('f9', self.force_manual_scan)
                keyboard.add_hotkey('f10', self.toggle_auto_scan)
            except Exception as e:
                print(f"⚠️ 无法注册全局快捷键 (Mac 环境通常需要 sudo 权限): {e}")

    def create_top_control_area(self, parent_layout):
        """创建顶部控制区域"""
        control_group = QGroupBox("控制面板")
        control_layout = QVBoxLayout(control_group)
        
        # 第一行：坐标显示和控制按钮
        row1_layout = QHBoxLayout()
        
        # 红色矩形坐标显示
        self.red_rect_label = QLabel("红色矩形坐标: 未设置")
        row1_layout.addWidget(self.red_rect_label)
        
        # 确定按钮
        self.confirm_button = QPushButton("确定")
        self.confirm_button.clicked.connect(self.confirm_rectangle)
        row1_layout.addWidget(self.confirm_button)
        
        # 重新确定按钮
        self.redefine_button = QPushButton("重新确定位置")
        self.redefine_button.clicked.connect(self.redefine_positions)
        row1_layout.addWidget(self.redefine_button)
        
        control_layout.addLayout(row1_layout)
        
        # 第二行：颜色选择和扫描按钮
        row2_layout = QHBoxLayout()
        
        # 颜色选择
        row2_layout.addWidget(QLabel("你的选择:"))
        self.color_white_radio = QRadioButton("白色")
        self.color_black_radio = QRadioButton("黑色")
        self.color_white_radio.setChecked(True)
        row2_layout.addWidget(self.color_white_radio)
        row2_layout.addWidget(self.color_black_radio)
        
        # 扫描按钮
        self.scan_button = QPushButton("扫描")
        self.scan_button.clicked.connect(self.check_green_pixels)
        row2_layout.addWidget(self.scan_button)
        
        # 文字显示框
        row2_layout.addWidget(QLabel("文字显示:"))
        self.text_display = QLineEdit()
        self.text_display.setReadOnly(True)
        row2_layout.addWidget(self.text_display)
        
        control_layout.addLayout(row2_layout)
        
        # 第三行：结束按钮和坐标输入
        row3_layout = QHBoxLayout()
        
        # 结束按钮
        self.stop_button = QPushButton("结束")
        self.stop_button.clicked.connect(self.stop_program)
        row3_layout.addWidget(self.stop_button)
        
        # 自动监控按钮
        self.auto_scan_btn = QPushButton("开启自动监控 (F10)")
        self.auto_scan_btn.setCheckable(True)
        self.auto_scan_btn.clicked.connect(self.toggle_auto_scan)
        row3_layout.addWidget(self.auto_scan_btn)
        
        # 强制扫描按钮
        self.force_scan_btn = QPushButton("强制扫码 Override (F9)")
        self.force_scan_btn.clicked.connect(self.force_manual_scan)
        row3_layout.addWidget(self.force_scan_btn)
        
        # 坐标输入
        row3_layout.addWidget(QLabel("输入坐标:"))
        self.coordinate_input = QLineEdit()
        self.coordinate_input.setPlaceholderText("例如: a15")
        row3_layout.addWidget(self.coordinate_input)
        
        # 下棋按钮
        self.move_button = QPushButton("下棋")
        self.move_button.clicked.connect(self.make_move)
        row3_layout.addWidget(self.move_button)
        
        # 主题选择
        row3_layout.addWidget(QLabel("主题:"))
        self.theme_light = QRadioButton("浅色")
        self.theme_dark = QRadioButton("深色")
        self.theme_light.setChecked(True)
        self.theme_light.toggled.connect(self.change_theme)
        self.theme_dark.toggled.connect(self.change_theme)
        row3_layout.addWidget(self.theme_light)
        row3_layout.addWidget(self.theme_dark)
        
        control_layout.addLayout(row3_layout)
        
        parent_layout.addWidget(control_group)

    def create_log_area(self, parent_layout):
        """创建日志区域"""
        log_group = QGroupBox("操作日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        parent_layout.addWidget(log_group)

    def confirm_rectangle(self):
        """确认矩形区域"""
        # 先检查是否已经设置了矩形区域
        red_rect = self.config_manager.get_system_setting("monitor.red_rectangle")
        
        if not red_rect:
            QMessageBox.information(self, "提示", "请先确定红色矩形区域")
            return
            
        # 更新坐标标签显示
        self.red_rect_label.setText(f"红色矩形坐标: ({red_rect[0]}, {red_rect[1]}, {red_rect[2]}, {red_rect[3]})")
        
        # 设置坐标映射器的红色矩形区域
        self.coordinate_mapper.set_red_rectangle(*red_rect)
        
        self.status_bar.showMessage("矩形区域已确认，请点击扫描按钮检测深绿色像素")
        
        self.log_message("确认矩形区域")

    def redefine_positions(self):
        """重新确定位置"""
        self.log_message("重新确定矩形位置")
        self.red_rect_label.setText("红色矩形坐标: 未设置")
        
        # 选择红色矩形区域
        self.select_red_rectangle()

    def select_red_rectangle(self):
        """选择红色矩形区域"""
        self.status_bar.showMessage("请选择红色矩形区域")
        # 使用与Winner 1.0相同的区域选择器
        from monitor.region_selector import RegionSelector
        self.red_selector = RegionSelector("red")
        self.red_selector.select_region(self.on_red_rectangle_selected)

    def on_red_rectangle_selected(self, rectangle):
        """红色矩形选择完成回调"""
        if rectangle:
            # 保存红色矩形区域到配置
            self.config_manager.set_system_setting("monitor.red_rectangle", list(rectangle))
            self.red_rect_label.setText(f"红色矩形坐标: ({rectangle[0]}, {rectangle[1]}, {rectangle[2]}, {rectangle[3]})")
            self.status_bar.showMessage("红色矩形区域已设置，点击确定开始监控")
        else:
            self.status_bar.showMessage("未选择红色矩形区域")

    def check_green_pixels(self):
        """
        架构优化后的极速扫描算法
        使用全局遮罩+轮廓检测，避免重心偏移问题
        :return: 检测到的坐标字符串，未检测到返回 None
        """
        try:
            # 获取红色矩形区域
            red_rect = self.config_manager.get_system_setting("monitor.red_rectangle")
            if not red_rect:
                self.status_bar.showMessage("未设置红色矩形区域")
                return None
            
            # 使用mss截取屏幕区域
            import mss
            with mss.mss() as sct:
                monitor = {
                    "top": red_rect[1],
                    "left": red_rect[0],
                    "width": red_rect[2] - red_rect[0],
                    "height": red_rect[3] - red_rect[1]
                }
                screenshot = sct.grab(monitor)
                
                # 转换为numpy数组 (BGR格式)
                img_array = np.array(screenshot)
                height, width = img_array.shape[:2]
                
                # 定义深绿色范围
                lower_green = np.array([0, 100, 0])
                upper_green = np.array([50, 255, 50])
                
                # 1. 一次性全局过滤，提取整张图的深绿色掩码
                green_mask = cv2.inRange(img_array, lower_green, upper_green)
                
                # 2. 动态计算阈值（基于棋盘大小）
                rect_width = abs(red_rect[2] - red_rect[0])
                cell_width = rect_width / 18.0
                scan_radius = max(3, int(cell_width * 0.4))
                scan_area = (2 * scan_radius + 1) ** 2
                dynamic_green_threshold = int(scan_area * 0.6)
                
                # 3. 查找绿色像素的轮廓
                contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # 4. 遍历每个轮廓，找到面积最大的有效团块
                for contour in contours:
                    area = cv2.contourArea(contour)
                    
                    # 如果面积小于动态阈值，跳过小噪点
                    if area < dynamic_green_threshold:
                        continue
                    
                    # 计算轮廓的重心
                    M = cv2.moments(contour)
                    if M["m00"] == 0:
                        continue
                    
                    center_x = int(M["m10"] / M["m00"]) + red_rect[0]
                    center_y = int(M["m01"] / M["m00"]) + red_rect[1]
                    
                    # 5. 二次验证：向上检测像素颜色
                    if self.verify_pixel_point(img_array, center_x, center_y):
                        # 6. 将屏幕坐标映射回围棋坐标
                        coordinate = self.coordinate_mapper.screen_to_board(center_x, center_y)
                        
                        if coordinate:
                            self.text_display.setText(coordinate)
                            self.log_entry(coordinate, "auto_scan")
                            self.status_bar.showMessage(f"瞬时捕获对手落子: {coordinate}")
                            return coordinate
                        
                self.status_bar.showMessage("扫描完成，未检测到有效坐标")
                return None
                    
        except Exception as e:
            self.status_bar.showMessage(f"检查像素出错: {e}")
            return None

    def generate_board_coordinates(self, red_rect):
        """
        生成361个围棋坐标点的屏幕坐标
        :param red_rect: 红色矩形区域 (x1, y1, x2, y2)
        :return: 字典，键为坐标标识，值为(x, y)屏幕坐标
        """
        coordinates = {}
        x1, y1, x2, y2 = red_rect
        
        # 确保坐标顺序正确
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)
        
        # 计算每个格子的宽度和高度
        rect_width = right - left
        rect_height = bottom - top
        cell_width = rect_width / 18.0
        cell_height = rect_height / 18.0
        
        # 围棋列坐标（没有i）
        cols = 'abcdefghjklmnopqrst'
        
        # 生成所有361个点的坐标
        for row in range(19):
            for col in range(19):
                # 计算屏幕坐标
                x = int(left + col * cell_width)
                y = int(top + row * cell_height)
                coord_key = f"{cols[col]}{19-row}"  # 围棋坐标
                coordinates[coord_key] = (x, y)
                
        return coordinates

    def verify_pixel_point(self, img_array, start_x, start_y):
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
        
        return False  # 超出范围，验证失败

    def short_scan(self, img_array, x, y):
        """
        短扫检查
        :param img_array: 图像数组
        :param x: 中心点x坐标
        :param y: 中心点y坐标
        :return: "skip"表示跳过，"valid"表示有效，None表示继续检查
        """
        height, width = img_array.shape[:2]
        
        # 获取红色矩形区域以计算动态阈值
        red_rect = self.config_manager.get_system_setting("monitor.red_rectangle")
        if not red_rect:
            return None
            
        x1, y1, x2, y2 = red_rect
        rect_width = abs(x2 - x1)
        cell_width = rect_width / 18.0
        
        # 动态计算扫描范围和阈值
        scan_radius = max(3, int(cell_width * 0.4))  # 动态半径，不超过格子一半
        scan_area = (2 * scan_radius + 1) ** 2
        green_threshold = int(scan_area * 0.6)  # 动态阈值（面积的60%）
        white_black_threshold = int(scan_area * 0.6)
        
        # 计算短扫矩形框的边界
        left = max(0, x - scan_radius)
        right = min(width - 1, x + scan_radius)
        top = max(0, y - scan_radius)
        bottom = min(height - 1, y + scan_radius)
        
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
            if self.verify_pixel_point(img_array, x, y):
                return "valid"
            else:
                return None  # 二次验证失败，继续检查
        
        return None  # 继续检查

    def toggle_auto_scan(self):
        """
        切换自动扫描状态
        每 300 毫秒高频扫描一次 (配合优化后的算法毫无性能压力)
        """
        self.is_auto_scanning = not self.is_auto_scanning
        if self.is_auto_scanning:
            self.scan_timer.start(300)  # 300ms 间隔
            self.auto_scan_btn.setText("停止自动监控 (F10)")
            self.auto_scan_btn.setChecked(True)
            self.status_bar.showMessage("自动监控已开启...")
        else:
            self.scan_timer.stop()
            self.auto_scan_btn.setText("开启自动监控 (F10)")
            self.auto_scan_btn.setChecked(False)
            self.status_bar.showMessage("自动监控已暂停")

    def auto_scan_task(self):
        """
        定时器任务：自动扫描
        调用优化后的极速扫描方法
        """
        coord = self.check_green_pixels()
        if coord:
            # 扫描到结果后，可根据需求决定是否暂停定时器，防重复记录
            # 等待自己下棋后再重新开启
            pass

    def force_manual_scan(self):
        """
        手动覆写机制 (Override)
        如果自动扫描正在运行，不需要打断，直接额外触发一次即可
        """
        self.status_bar.showMessage("触发 Override: 执行强制扫描")
        self.check_green_pixels()

    def stop_program(self):
        """结束程序"""
        self.log_message("程序结束，保存日志到mygame.txt")
        self.save_log_to_file()
        self.status_bar.showMessage("程序已结束，日志已保存")
        self.close()

    def make_move(self):
        """执行下棋操作"""
        coordinate = self.coordinate_input.text().strip().lower()
        if not coordinate:
            QMessageBox.warning(self, "警告", "请输入坐标")
            return
            
        if len(coordinate) < 2:
            QMessageBox.warning(self, "警告", "坐标格式不正确")
            return
            
        # 验证坐标格式（没有i）
        col_char = coordinate[0]
        row_str = coordinate[1:]
        
        # 围棋列坐标（没有i）
        cols = 'abcdefghjklmnopqrst'
        if col_char not in cols:
            QMessageBox.warning(self, "警告", "列坐标必须是a-t之间的字母（不包括i）")
            return
            
        try:
            row_num = int(row_str)
            if row_num < 1 or row_num > 19:
                QMessageBox.warning(self, "警告", "行坐标必须是1-19之间的数字")
                return
        except ValueError:
            QMessageBox.warning(self, "警告", "行坐标必须是数字")
            return
            
        # 执行鼠标双击
        result = self.mouse_controller.double_click_at_coordinate(coordinate, self.coordinate_mapper)
        if result["success"]:
            self.log_from_coordinate_input()
            self.coordinate_input.clear()  # 清空输入框，方便下次输入
            self.status_bar.showMessage(f"已在 {coordinate} 位置双击")
        else:
            QMessageBox.critical(self, "错误", f"下棋操作失败: {result['message']}")

    def change_theme(self):
        """切换主题"""
        if self.theme_light.isChecked():
            self.apply_theme("light")
            self.config_manager.set_system_setting("ui.theme", "light")
        else:
            self.apply_theme("dark")
            self.config_manager.set_system_setting("ui.theme", "dark")

    def apply_theme(self, theme_name):
        """应用主题"""
        if theme_name == "light":
            self.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    color: #000000;
                }
                QGroupBox {
                    border: 1px solid #cccccc;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #e1e1e1;
                    border: 1px solid #cccccc;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
                QTextEdit {
                    background-color: #f0f0f0;
                    border: 1px solid #cccccc;
                }
                QLineEdit {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #2e2e2e;
                    color: #ffffff;
                }
                QGroupBox {
                    border: 1px solid #555555;
                    margin-top: 1ex;
                    font-weight: bold;
                }
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #666666;
                    padding: 5px;
                    color: #ffffff;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
                QTextEdit {
                    background-color: #3e3e3e;
                    border: 1px solid #555555;
                    color: #ffffff;
                }
                QLineEdit {
                    background-color: #3e3e3e;
                    border: 1px solid #555555;
                    color: #ffffff;
                }
            """)

    def load_settings(self):
        """加载设置"""
        # 加载主题设置
        theme = self.config_manager.get_system_setting("ui.theme", "light")
        if theme == "light":
            self.theme_light.setChecked(True)
        else:
            self.theme_dark.setChecked(True)
        self.apply_theme(theme)
        
        # 加载矩形区域设置
        red_rect = self.config_manager.get_system_setting("monitor.red_rectangle")
        if red_rect:
            self.red_rect_label.setText(f"红色矩形坐标: ({red_rect[0]}, {red_rect[1]}, {red_rect[2]}, {red_rect[3]})")
            # 设置坐标映射器的红色矩形区域
            self.coordinate_mapper.set_red_rectangle(*red_rect)
            
        # 加载日志计数器
        self.log_counter = self.config_manager.get_system_setting("log.counter", 1)
        self.last_logged_source = self.config_manager.get_system_setting("log.last_source", None)

    def log_message(self, message):
        """记录日志消息"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insertPlainText(log_entry)
        self.log_text.ensureCursorVisible()

    def log_from_coordinate_input(self):
        """从坐标输入框记录日志"""
        text = self.coordinate_input.text().strip().lower()
        if text:
            self.log_entry(text, "coordinate_input")

    def log_entry(self, text, source):
        """
        记录日志条目
        实时写入文件，防止数据丢失
        """
        # 检查是否需要轮换记录源
        if self.last_logged_source is None or self.last_logged_source != source:
            log_text = f"{self.log_counter}, {text}\n"
            self.log_text.insertPlainText(log_text)
            self.log_text.ensureCursorVisible()
            
            # 实时追加写入文件，防止程序崩溃导致数据丢失
            try:
                with open("mygame.txt", "a", encoding="utf-8") as f:
                    f.write(log_text)
            except Exception as e:
                # 静默失败，不影响主流程
                pass
            
            self.log_counter += 1
            self.last_logged_source = source
            
            # 保存到配置以便恢复
            self.config_manager.set_system_setting("log.counter", self.log_counter)
            self.config_manager.set_system_setting("log.last_source", self.last_logged_source)

    def save_log_to_file(self):
        """保存日志到文件"""
        try:
            from datetime import datetime
            filename = f"mygame_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.log_text.toPlainText())
            self.status_bar.showMessage(f"日志已保存到 {filename}")
        except Exception as e:
            self.status_bar.showMessage(f"保存日志失败: {e}")

    def setup_system_tray(self):
        """设置系统托盘"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(":/icons/app_icon.png"))  # 需要添加图标文件
            
            # 创建托盘菜单
            tray_menu = QMenu()
            restore_action = QAction("还原", self)
            restore_action.triggered.connect(self.showNormal)
            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self.stop_program)
            
            tray_menu.addAction(restore_action)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()

    def closeEvent(self, event):
        """
        窗口关闭时必须注销全局快捷键，防止内存泄漏
        """
        # 停止自动扫描定时器
        if self.is_auto_scanning:
            self.scan_timer.stop()
        
        if HAS_KEYBOARD:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
                
        # 接受关闭事件
        event.accept()