import sys
import cv2
import numpy as np
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QFileDialog,
                             QSlider, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QGroupBox, QMessageBox, QListWidget, QListWidgetItem,
                             QStackedWidget, QComboBox, QGridLayout, QLineEdit,
                             QSplitter, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor
from skimage.restoration import wiener, unsupervised_wiener
from skimage import exposure

class ImageProcessingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("全能图像处理工具箱 - PyQt5")
        self.setGeometry(100, 100, 1400, 800)

        # 存储图像
        self.original_image = None      # 原始图像 (BGR)
        self.processed_image = None     # 处理后图像 (BGR)
        self.mixup_second_image = None  # mixup 第二张图像

        # 几何校正的点存储
        self.src_points = []
        self.dst_points = [(0,0), (200,0), (200,200), (0,200)]  # 目标矩形

        # 颜色通道分离存储
        self.separated_channels = None  # 列表 [B,G,R] 每个为单通道图像

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ========== 左侧功能区 ==========
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5,5,5,5)

        # 打开图像按钮
        self.btn_open = QPushButton("打开图像")
        self.btn_open.clicked.connect(self.open_image)
        left_layout.addWidget(self.btn_open)

        # 功能分类列表 (两层级：大类 -> 子功能)
        self.func_tree = QListWidget()
        self.func_tree.setMinimumWidth(200)
        self.func_tree.setMaximumWidth(250)
        self.populate_function_tree()
        self.func_tree.itemClicked.connect(self.on_function_selected)
        left_layout.addWidget(self.func_tree)

        # 参数区域 (动态显示)
        self.param_stack = QStackedWidget()
        left_layout.addWidget(self.param_stack)

        # 应用按钮
        self.btn_apply = QPushButton("应用当前功能")
        self.btn_apply.clicked.connect(self.apply_current_function)
        self.btn_apply.setEnabled(False)
        left_layout.addWidget(self.btn_apply)

        # 保存按钮
        self.btn_save = QPushButton("保存处理结果")
        self.btn_save.clicked.connect(self.save_result)
        self.btn_save.setEnabled(False)
        left_layout.addWidget(self.btn_save)

        # ========== 右侧图像显示 ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        self.original_label = QLabel("原始图像")
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        self.original_label.setMinimumSize(500, 400)

        self.result_label = QLabel("处理结果")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("border: 1px solid black; background-color: #f0f0f0;")
        self.result_label.setMinimumSize(500, 400)

        right_layout.addWidget(self.original_label)
        right_layout.addWidget(self.result_label)

        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter)

        # 初始化参数页面
        self.init_param_pages()

    def populate_function_tree(self):
        """构建功能树（两级菜单）"""
        categories = {
            "像素值调整": ["二值化", "灰度化", "归一化", "对比度增强(直方均衡)"],
            "几何变换": ["调整大小", "翻转", "旋转", "裁剪", "几何校正(逆透视)"],
            "噪声处理": ["高斯滤波", "均值滤波", "去模糊(维纳滤波)", "双边滤波"],
            "形态学操作": ["腐蚀", "膨胀", "开运算", "闭运算", "梯度运算", "顶帽运算"],
            "通道与色彩": ["白平衡", "色彩空间变换", "通道分离", "通道合成"],
            "数据增强": ["随机裁剪", "随机旋转", "随机翻转", "随机亮度/对比度", "Mixup混合增强"]
        }
        for cat, items in categories.items():
            cat_item = QListWidgetItem(cat)
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemIsSelectable)  # 不可选
            cat_item.setForeground(QColor(0,0,255))
            self.func_tree.addItem(cat_item)
            for item in items:
                child = QListWidgetItem(f"    {item}")
                child.setData(Qt.UserRole, (cat, item))
                self.func_tree.addItem(child)

    def init_param_pages(self):
        """为每个功能创建参数控件页面"""
        self.param_pages = {}
        self.current_func = None

        # 二值化
        page = QWidget()
        layout = QVBoxLayout()
        self.thresh_slider = QSlider(Qt.Horizontal)
        self.thresh_slider.setRange(0, 255)
        self.thresh_slider.setValue(127)
        layout.addWidget(QLabel("阈值:"))
        layout.addWidget(self.thresh_slider)
        self.thresh_label = QLabel("127")
        layout.addWidget(self.thresh_label)
        self.thresh_slider.valueChanged.connect(lambda v: self.thresh_label.setText(str(v)))
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["二值化"] = page

        # 灰度化：无需参数
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("直接转换为灰度图像"))
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["灰度化"] = page

        # 归一化
        page = QWidget()
        layout = QVBoxLayout()
        self.norm_min = QSlider(Qt.Horizontal); self.norm_min.setRange(0,255); self.norm_min.setValue(0)
        self.norm_max = QSlider(Qt.Horizontal); self.norm_max.setRange(0,255); self.norm_max.setValue(255)
        layout.addWidget(QLabel("归一化最小值:")); layout.addWidget(self.norm_min)
        layout.addWidget(QLabel("归一化最大值:")); layout.addWidget(self.norm_max)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["归一化"] = page

        # 对比度增强（直方图均衡化）
        page = QWidget()
        layout = QVBoxLayout()
        self.clahe_check = QCheckBox("自适应直方图均衡 (CLAHE)")
        self.clahe_clip = QSlider(Qt.Horizontal); self.clahe_clip.setRange(1,10); self.clahe_clip.setValue(2)
        layout.addWidget(self.clahe_check)
        layout.addWidget(QLabel("Clip limit:")); layout.addWidget(self.clahe_clip)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["对比度增强(直方均衡)"] = page

        # 调整大小
        page = QWidget()
        layout = QGridLayout()
        self.resize_w = QSpinBox(); self.resize_w.setRange(1, 3000); self.resize_w.setValue(400)
        self.resize_h = QSpinBox(); self.resize_h.setRange(1, 3000); self.resize_h.setValue(400)
        self.keep_ratio = QCheckBox("保持宽高比")
        layout.addWidget(QLabel("宽度:"),0,0); layout.addWidget(self.resize_w,0,1)
        layout.addWidget(QLabel("高度:"),1,0); layout.addWidget(self.resize_h,1,1)
        layout.addWidget(self.keep_ratio,2,0,1,2)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["调整大小"] = page

        # 翻转
        page = QWidget()
        layout = QVBoxLayout()
        self.flip_code = QComboBox()
        self.flip_code.addItems(["水平翻转", "垂直翻转", "水平+垂直"])
        layout.addWidget(self.flip_code)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["翻转"] = page

        # 旋转
        page = QWidget()
        layout = QVBoxLayout()
        self.rotate_angle = QSlider(Qt.Horizontal); self.rotate_angle.setRange(-180,180); self.rotate_angle.setValue(0)
        self.rotate_label = QLabel("0°")
        self.rotate_angle.valueChanged.connect(lambda v: self.rotate_label.setText(f"{v}°"))
        layout.addWidget(QLabel("旋转角度:")); layout.addWidget(self.rotate_angle); layout.addWidget(self.rotate_label)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["旋转"] = page

        # 裁剪
        page = QWidget()
        layout = QGridLayout()
        self.crop_x = QSpinBox(); self.crop_y = QSpinBox(); self.crop_w = QSpinBox(); self.crop_h = QSpinBox()
        self.crop_w.setRange(1,3000); self.crop_h.setRange(1,3000)
        layout.addWidget(QLabel("x:"),0,0); layout.addWidget(self.crop_x,0,1)
        layout.addWidget(QLabel("y:"),0,2); layout.addWidget(self.crop_y,0,3)
        layout.addWidget(QLabel("宽:"),1,0); layout.addWidget(self.crop_w,1,1)
        layout.addWidget(QLabel("高:"),1,2); layout.addWidget(self.crop_h,1,3)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["裁剪"] = page

        # 几何校正（逆透视）
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("源点坐标 (x,y) 四个点，用空格分隔，例如: 0,0 200,0 200,200 0,200"))
        self.src_points_edit = QLineEdit("0,0 300,0 300,300 0,300")
        layout.addWidget(self.src_points_edit)
        layout.addWidget(QLabel("目标矩形宽高:"))
        self.dst_w = QSpinBox(); self.dst_w.setValue(300)
        self.dst_h = QSpinBox(); self.dst_h.setValue(300)
        layout.addWidget(self.dst_w); layout.addWidget(self.dst_h)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["几何校正(逆透视)"] = page

        # 高斯滤波
        page = QWidget()
        layout = QVBoxLayout()
        self.gauss_k = QSlider(Qt.Horizontal); self.gauss_k.setRange(1,21); self.gauss_k.setSingleStep(2); self.gauss_k.setValue(3)
        self.gauss_sigma = QDoubleSpinBox(); self.gauss_sigma.setRange(0.1,5.0); self.gauss_sigma.setValue(1.0)
        layout.addWidget(QLabel("核大小(奇数):")); layout.addWidget(self.gauss_k)
        layout.addWidget(QLabel("Sigma:")); layout.addWidget(self.gauss_sigma)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["高斯滤波"] = page

        # 均值滤波
        page = QWidget()
        layout = QVBoxLayout()
        self.mean_k = QSlider(Qt.Horizontal); self.mean_k.setRange(1,21); self.mean_k.setSingleStep(2); self.mean_k.setValue(3)
        layout.addWidget(QLabel("核大小(奇数):")); layout.addWidget(self.mean_k)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["均值滤波"] = page

        # 去模糊（维纳滤波）
        page = QWidget()
        layout = QVBoxLayout()
        self.wiener_psf = QDoubleSpinBox(); self.wiener_psf.setRange(0.1,10.0); self.wiener_psf.setValue(1.0)
        self.wiener_balance = QDoubleSpinBox(); self.wiener_balance.setRange(0.001,1.0); self.wiener_balance.setValue(0.1)
        layout.addWidget(QLabel("PSF模糊核大小(模拟):")); layout.addWidget(self.wiener_psf)
        layout.addWidget(QLabel("平衡参数(越大越去噪):")); layout.addWidget(self.wiener_balance)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["去模糊(维纳滤波)"] = page

        # 双边滤波
        page = QWidget()
        layout = QVBoxLayout()
        self.bil_d = QSlider(Qt.Horizontal); self.bil_d.setRange(1,15); self.bil_d.setValue(9)
        self.bil_sigma_color = QDoubleSpinBox(); self.bil_sigma_color.setRange(1,200); self.bil_sigma_color.setValue(75)
        self.bil_sigma_space = QDoubleSpinBox(); self.bil_sigma_space.setRange(1,200); self.bil_sigma_space.setValue(75)
        layout.addWidget(QLabel("直径:")); layout.addWidget(self.bil_d)
        layout.addWidget(QLabel("颜色标准差:")); layout.addWidget(self.bil_sigma_color)
        layout.addWidget(QLabel("空间标准差:")); layout.addWidget(self.bil_sigma_space)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["双边滤波"] = page

        # 形态学操作（通用参数）
        morph_funcs = ["腐蚀", "膨胀", "开运算", "闭运算", "梯度运算", "顶帽运算"]
        for func in morph_funcs:
            page = QWidget()
            layout = QVBoxLayout()
            ks = QSlider(Qt.Horizontal); ks.setRange(1,21); ks.setSingleStep(2); ks.setValue(3)
            iter_s = QSlider(Qt.Horizontal); iter_s.setRange(1,10); iter_s.setValue(1)
            layout.addWidget(QLabel("核大小(奇数):")); layout.addWidget(ks)
            layout.addWidget(QLabel("迭代次数:")); layout.addWidget(iter_s)
            page.setLayout(layout)
            self.param_stack.addWidget(page)
            self.param_pages[func] = (page, ks, iter_s)

        # 白平衡 (简单灰度世界)
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("自动白平衡 (灰度世界假设)"))
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["白平衡"] = page

        # 色彩空间变换
        page = QWidget()
        layout = QVBoxLayout()
        self.color_space = QComboBox()
        self.color_space.addItems(["BGR->HSV", "BGR->YUV", "BGR->Lab", "BGR->灰度"])
        layout.addWidget(self.color_space)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["色彩空间变换"] = page

        # 通道分离
        page = QWidget()
        layout = QVBoxLayout()
        self.ch_show = QComboBox()
        self.ch_show.addItems(["蓝色通道(B)", "绿色通道(G)", "红色通道(R)"])
        layout.addWidget(QLabel("分离后显示通道:")); layout.addWidget(self.ch_show)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["通道分离"] = page

        # 通道合成 (需选择三个通道来源)
        page = QWidget()
        layout = QVBoxLayout()
        self.ch_source = QComboBox()
        self.ch_source.addItems(["使用当前分离的通道", "从文件加载通道", "手动指定灰度图像"])
        layout.addWidget(self.ch_source)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["通道合成"] = page

        # 数据增强类
        # 随机裁剪
        page = QWidget()
        layout = QVBoxLayout()
        self.crop_ratio = QDoubleSpinBox(); self.crop_ratio.setRange(0.1,1.0); self.crop_ratio.setValue(0.8)
        layout.addWidget(QLabel("裁剪比例(相对于原图):")); layout.addWidget(self.crop_ratio)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["随机裁剪"] = page

        # 随机旋转
        page = QWidget()
        layout = QVBoxLayout()
        self.rand_angle_range = QSpinBox(); self.rand_angle_range.setRange(0,180); self.rand_angle_range.setValue(30)
        layout.addWidget(QLabel("最大旋转角度(0~180):")); layout.addWidget(self.rand_angle_range)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["随机旋转"] = page

        # 随机翻转
        page = QWidget()
        layout = QVBoxLayout()
        self.flip_prob = QDoubleSpinBox(); self.flip_prob.setRange(0,1); self.flip_prob.setSingleStep(0.1); self.flip_prob.setValue(0.5)
        layout.addWidget(QLabel("翻转概率:")); layout.addWidget(self.flip_prob)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["随机翻转"] = page

        # 随机亮度/对比度
        page = QWidget()
        layout = QVBoxLayout()
        self.bright_range = QSpinBox(); self.bright_range.setRange(0,100); self.bright_range.setValue(30)
        self.contrast_range = QDoubleSpinBox(); self.contrast_range.setRange(0.5,1.5); self.contrast_range.setValue(0.2)
        layout.addWidget(QLabel("亮度变化范围(-value,+value):")); layout.addWidget(self.bright_range)
        layout.addWidget(QLabel("对比度变化系数(0.5~1.5):")); layout.addWidget(self.contrast_range)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["随机亮度/对比度"] = page

        # Mixup混合增强
        page = QWidget()
        layout = QVBoxLayout()
        self.mixup_alpha = QDoubleSpinBox(); self.mixup_alpha.setRange(0.1,2.0); self.mixup_alpha.setValue(0.5)
        self.btn_load_mix = QPushButton("加载第二张图像")
        self.btn_load_mix.clicked.connect(self.load_mixup_image)
        layout.addWidget(QLabel("混合系数 α (Beta分布参数):")); layout.addWidget(self.mixup_alpha)
        layout.addWidget(self.btn_load_mix)
        self.mixup_label = QLabel("未加载第二张图像")
        layout.addWidget(self.mixup_label)
        page.setLayout(layout)
        self.param_stack.addWidget(page)
        self.param_pages["Mixup混合增强"] = page

    def load_mixup_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, "选择第二张图像", "", "图像文件 (*.png *.jpg *.bmp)")
        if fname:
            img = cv2.imread(fname)
            if img is not None:
                self.mixup_second_image = img
                self.mixup_label.setText("已加载第二张图像")
            else:
                QMessageBox.warning(self, "错误", "无法读取图像")

    def on_function_selected(self, item):
        if not item.data(Qt.UserRole):
            return
        cat, func_name = item.data(Qt.UserRole)
        self.current_func = func_name
        # 切换参数页
        if func_name in self.param_pages:
            if isinstance(self.param_pages[func_name], tuple):
                self.param_stack.setCurrentWidget(self.param_pages[func_name][0])
            else:
                self.param_stack.setCurrentWidget(self.param_pages[func_name])
            self.btn_apply.setEnabled(self.original_image is not None)
        else:
            self.btn_apply.setEnabled(False)

    def apply_current_function(self):
        if self.original_image is None:
            QMessageBox.warning(self, "警告", "请先打开一张图像")
            return
        if self.current_func is None:
            return

        func = self.current_func
        try:
            if func == "二值化":
                self.apply_binarization()
            elif func == "灰度化":
                self.apply_grayscale()
            elif func == "归一化":
                self.apply_normalize()
            elif func == "对比度增强(直方均衡)":
                self.apply_hist_eq()
            elif func == "调整大小":
                self.apply_resize()
            elif func == "翻转":
                self.apply_flip()
            elif func == "旋转":
                self.apply_rotate()
            elif func == "裁剪":
                self.apply_crop()
            elif func == "几何校正(逆透视)":
                self.apply_perspective()
            elif func == "高斯滤波":
                self.apply_gaussian()
            elif func == "均值滤波":
                self.apply_mean()
            elif func == "去模糊(维纳滤波)":
                self.apply_wiener()
            elif func == "双边滤波":
                self.apply_bilateral()
            elif func in ["腐蚀", "膨胀", "开运算", "闭运算", "梯度运算", "顶帽运算"]:
                self.apply_morphology()
            elif func == "白平衡":
                self.apply_white_balance()
            elif func == "色彩空间变换":
                self.apply_color_space()
            elif func == "通道分离":
                self.apply_channel_separate()
            elif func == "通道合成":
                self.apply_channel_merge()
            elif func == "随机裁剪":
                self.apply_random_crop()
            elif func == "随机旋转":
                self.apply_random_rotate()
            elif func == "随机翻转":
                self.apply_random_flip()
            elif func == "随机亮度/对比度":
                self.apply_random_brightness_contrast()
            elif func == "Mixup混合增强":
                self.apply_mixup()
            else:
                QMessageBox.warning(self, "未实现", f"功能 '{func}' 尚未实现")
            self.display_image(self.processed_image, self.result_label)
            self.btn_save.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理失败: {str(e)}")

    # ------------------- 功能实现 -------------------
    def apply_binarization(self):
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        thresh = self.thresh_slider.value()
        _, binary = cv2.threshold(gray, thresh, 255, cv2.THRESH_BINARY)
        self.processed_image = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def apply_grayscale(self):
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
        self.processed_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def apply_normalize(self):
        min_val = self.norm_min.value()
        max_val = self.norm_max.value()
        norm = cv2.normalize(self.original_image, None, min_val, max_val, cv2.NORM_MINMAX)
        self.processed_image = norm

    def apply_hist_eq(self):
        if self.clahe_check.isChecked():
            lab = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=self.clahe_clip.value(), tileGridSize=(8,8))
            l = clahe.apply(l)
            lab = cv2.merge([l,a,b])
            self.processed_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            if len(self.original_image.shape) == 3:
                ycrcb = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2YCrCb)
                y, cr, cb = cv2.split(ycrcb)
                y_eq = cv2.equalizeHist(y)
                ycrcb_eq = cv2.merge([y_eq, cr, cb])
                self.processed_image = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)
            else:
                self.processed_image = cv2.equalizeHist(self.original_image)

    def apply_resize(self):
        w = self.resize_w.value()
        h = self.resize_h.value()
        if self.keep_ratio.isChecked():
            h_orig, w_orig = self.original_image.shape[:2]
            ratio = min(w/w_orig, h/h_orig)
            new_w = int(w_orig * ratio)
            new_h = int(h_orig * ratio)
            self.processed_image = cv2.resize(self.original_image, (new_w, new_h))
        else:
            self.processed_image = cv2.resize(self.original_image, (w, h))

    def apply_flip(self):
        code = self.flip_code.currentIndex()
        flip_codes = [1, 0, -1]
        self.processed_image = cv2.flip(self.original_image, flip_codes[code])

    def apply_rotate(self):
        angle = self.rotate_angle.value()
        h, w = self.original_image.shape[:2]
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        self.processed_image = cv2.warpAffine(self.original_image, M, (w, h))

    def apply_crop(self):
        x = self.crop_x.value()
        y = self.crop_y.value()
        w = self.crop_w.value()
        h = self.crop_h.value()
        self.processed_image = self.original_image[y:y+h, x:x+w].copy()

    def apply_perspective(self):
        src_str = self.src_points_edit.text()
        points = []
        for pair in src_str.split():
            x,y = map(int, pair.split(','))
            points.append((x,y))
        if len(points) != 4:
            QMessageBox.warning(self, "错误", "需要四个源点")
            return
        src = np.float32(points)
        dst = np.float32([[0,0], [self.dst_w.value(),0], [self.dst_w.value(),self.dst_h.value()], [0,self.dst_h.value()]])
        M = cv2.getPerspectiveTransform(src, dst)
        self.processed_image = cv2.warpPerspective(self.original_image, M, (self.dst_w.value(), self.dst_h.value()))

    def apply_gaussian(self):
        ksize = self.gauss_k.value()
        if ksize%2==0: ksize+=1
        self.processed_image = cv2.GaussianBlur(self.original_image, (ksize,ksize), self.gauss_sigma.value())

    def apply_mean(self):
        ksize = self.mean_k.value()
        if ksize%2==0: ksize+=1
        self.processed_image = cv2.blur(self.original_image, (ksize,ksize))

    def apply_wiener(self):
        # 使用 skimage 的维纳滤波，需要转换为 float 且灰度图处理简单
        img_gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY).astype(np.float64)/255.0
        # 模拟 PSF (高斯模糊核)
        psf_size = int(self.wiener_psf.value()) if self.wiener_psf.value()>=1 else 1
        if psf_size%2==0: psf_size+=1
        psf = cv2.getGaussianKernel(psf_size, -1)
        psf = psf @ psf.T
        try:
            restored = wiener(img_gray, psf, balance=self.wiener_balance.value())
            restored = (restored * 255).clip(0,255).astype(np.uint8)
            self.processed_image = cv2.cvtColor(restored, cv2.COLOR_GRAY2BGR)
        except:
            # 备用简单逆滤波
            QMessageBox.warning(self, "警告", "维纳滤波失败，使用简单逆滤波")
            self.processed_image = self.original_image

    def apply_bilateral(self):
        d = self.bil_d.value()
        sigma_c = self.bil_sigma_color.value()
        sigma_s = self.bil_sigma_space.value()
        self.processed_image = cv2.bilateralFilter(self.original_image, d, sigma_c, sigma_s)

    def apply_morphology(self):
        func_name = self.current_func
        page, ks_slider, iter_slider = self.param_pages[func_name]
        kernel = np.ones((ks_slider.value(), ks_slider.value()), np.uint8)
        iters = iter_slider.value()
        if func_name == "腐蚀":
            res = cv2.erode(self.original_image, kernel, iterations=iters)
        elif func_name == "膨胀":
            res = cv2.dilate(self.original_image, kernel, iterations=iters)
        elif func_name == "开运算":
            res = cv2.morphologyEx(self.original_image, cv2.MORPH_OPEN, kernel, iterations=iters)
        elif func_name == "闭运算":
            res = cv2.morphologyEx(self.original_image, cv2.MORPH_CLOSE, kernel, iterations=iters)
        elif func_name == "梯度运算":
            res = cv2.morphologyEx(self.original_image, cv2.MORPH_GRADIENT, kernel, iterations=iters)
        elif func_name == "顶帽运算":
            res = cv2.morphologyEx(self.original_image, cv2.MORPH_TOPHAT, kernel, iterations=iters)
        else:
            res = self.original_image
        self.processed_image = res

    def apply_white_balance(self):
        # 灰度世界算法
        img = self.original_image.astype(np.float32)
        avg_b = np.mean(img[:,:,0])
        avg_g = np.mean(img[:,:,1])
        avg_r = np.mean(img[:,:,2])
        avg_gray = (avg_b+avg_g+avg_r)/3
        img[:,:,0] = np.clip(img[:,:,0] * (avg_gray/avg_b), 0, 255)
        img[:,:,1] = np.clip(img[:,:,1] * (avg_gray/avg_g), 0, 255)
        img[:,:,2] = np.clip(img[:,:,2] * (avg_gray/avg_r), 0, 255)
        self.processed_image = img.astype(np.uint8)

    def apply_color_space(self):
        code = self.color_space.currentText()
        if code == "BGR->HSV":
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2HSV)
        elif code == "BGR->YUV":
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2YUV)
        elif code == "BGR->Lab":
            self.processed_image = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2Lab)
        elif code == "BGR->灰度":
            gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)
            self.processed_image = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

    def apply_channel_separate(self):
        b,g,r = cv2.split(self.original_image)
        self.separated_channels = (b,g,r)
        show_idx = self.ch_show.currentIndex()
        if show_idx == 0:
            self.processed_image = cv2.cvtColor(b, cv2.COLOR_GRAY2BGR)
        elif show_idx == 1:
            self.processed_image = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
        else:
            self.processed_image = cv2.cvtColor(r, cv2.COLOR_GRAY2BGR)

    def apply_channel_merge(self):
        if self.separated_channels is None:
            QMessageBox.warning(self, "错误", "请先执行通道分离")
            return
        b,g,r = self.separated_channels
        merged = cv2.merge([b,g,r])
        self.processed_image = merged

    def apply_random_crop(self):
        h,w = self.original_image.shape[:2]
        ratio = self.crop_ratio.value()
        new_h, new_w = int(h*ratio), int(w*ratio)
        y = random.randint(0, h-new_h)
        x = random.randint(0, w-new_w)
        self.processed_image = self.original_image[y:y+new_h, x:x+new_w].copy()

    def apply_random_rotate(self):
        angle = random.uniform(-self.rand_angle_range.value(), self.rand_angle_range.value())
        h,w = self.original_image.shape[:2]
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        self.processed_image = cv2.warpAffine(self.original_image, M, (w, h))

    def apply_random_flip(self):
        if random.random() < self.flip_prob.value():
            self.processed_image = cv2.flip(self.original_image, 1)  # 水平翻转
        else:
            self.processed_image = self.original_image.copy()

    def apply_random_brightness_contrast(self):
        img = self.original_image.astype(np.float32)
        bright = random.randint(-self.bright_range.value(), self.bright_range.value())
        contrast = 1 + random.uniform(-self.contrast_range.value(), self.contrast_range.value())
        img = contrast * img + bright
        self.processed_image = np.clip(img, 0, 255).astype(np.uint8)

    def apply_mixup(self):
        if self.mixup_second_image is None:
            QMessageBox.warning(self, "错误", "请先加载第二张图像")
            return
        # 调整第二张图像大小与第一张一致
        img1 = self.original_image.astype(np.float32)
        img2 = cv2.resize(self.mixup_second_image, (img1.shape[1], img1.shape[0])).astype(np.float32)
        alpha = self.mixup_alpha.value()
        lam = np.random.beta(alpha, alpha)
        mixed = lam * img1 + (1-lam) * img2
        self.processed_image = np.clip(mixed, 0, 255).astype(np.uint8)

    # ------------------- 辅助函数 -------------------
    def open_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, "打开图像", "", "图像文件 (*.png *.jpg *.bmp *.tif)")
        if fname:
            img = cv2.imread(fname)
            if img is not None:
                self.original_image = img
                self.processed_image = None
                self.display_image(self.original_image, self.original_label)
                self.result_label.clear()
                self.result_label.setText("处理结果")
                self.btn_apply.setEnabled(True)
                self.btn_save.setEnabled(False)
            else:
                QMessageBox.warning(self, "错误", "无法读取图像")

    def save_result(self):
        if self.processed_image is None:
            QMessageBox.warning(self, "警告", "没有处理结果可保存")
            return
        fname, _ = QFileDialog.getSaveFileName(self, "保存图像", "", "PNG (*.png);;JPEG (*.jpg)")
        if fname:
            cv2.imwrite(fname, self.processed_image)
            QMessageBox.information(self, "成功", "图像已保存")

    def display_image(self, img, label):
        if img is None:
            return
        if len(img.shape) == 3:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h,w,ch = rgb.shape
            bytes_per_line = ch * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        else:
            h,w = img.shape
            qimg = QImage(img.data, w, h, w, QImage.Format_Grayscale8)
        pix = QPixmap.fromImage(qimg)
        scaled = pix.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(scaled)

    def resizeEvent(self, event):
        if self.original_image is not None:
            self.display_image(self.original_image, self.original_label)
        if self.processed_image is not None:
            self.display_image(self.processed_image, self.result_label)
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageProcessingApp()
    window.show()
    sys.exit(app.exec_())