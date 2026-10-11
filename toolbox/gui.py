"""Native image workbench with bounded history and background processing."""
import argparse
import logging
import os
import sys
import time
from pathlib import Path

import cv2
from PyQt5.QtCore import Qt, QSettings, QThread, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QAction, QApplication, QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog,
    QFrame, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabWidget, QTextBrowser, QVBoxLayout, QWidget,
)
from . import __version__
from .history import History
from .image_io import IMAGE_FILTER, read_image, save_image
from .processing import CATEGORIES, OPERATIONS, OPERATION_MAP, process
from .theme import STYLE

REPOSITORY = "https://github.com/LotusXanderYang/pyqt-image-toolbox"


def resource(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1])) / name


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.PlainText)
    return widget


def button(text, callback, primary=False, tooltip=""):
    widget = QPushButton(text)
    if primary:
        widget.setObjectName("primary")
    widget.setMinimumHeight(42)
    widget.setCursor(Qt.PointingHandCursor)
    widget.setToolTip(tooltip)
    widget.setAccessibleName(text)
    widget.clicked.connect(callback)
    return widget


class ImageView(QGraphicsView):
    zoom_changed = pyqtSignal(float)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = None
        self.auto_fit = True
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMinimumSize(180, 160)
        self.setAccessibleName("图像预览，滚轮缩放，拖动平移")
        self.setToolTip("滚轮缩放 · 拖动平移 · 双击适应窗口")

    def set_image(self, image):
        self.scene().clear()
        self.item = None
        if image is not None:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w = rgb.shape[:2]
            qimage = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format_RGB888).copy()
            self.item = self.scene().addPixmap(QPixmap.fromImage(qimage))
            self.scene().setSceneRect(self.item.boundingRect())
            self.fit_image()

    def fit_image(self):
        self.auto_fit = True
        if self.item:
            self.fitInView(self.item, Qt.KeepAspectRatio)

    def set_zoom(self, factor):
        if self.item:
            self.auto_fit = False
            self.resetTransform()
            self.scale(factor, factor)

    def wheelEvent(self, event):
        if self.item:
            factor = self.transform().m11() * (1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
            factor = min(8, max(.05, factor))
            self.set_zoom(factor)
            self.zoom_changed.emit(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.fit_image()
        self.zoom_changed.emit(0)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.auto_fit:
            self.fit_image()


class Preview(QFrame):
    def __init__(self, title, badge):
        super().__init__()
        self.setObjectName("panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QHBoxLayout()
        header.setContentsMargins(16, 14, 16, 14)
        header.addWidget(label(title, "section"))
        header.addStretch()
        self.badge = label(badge, "badge")
        header.addWidget(self.badge)
        layout.addLayout(header)
        self.view = ImageView()
        layout.addWidget(self.view, 1)
        self.info = label("尚未打开图像", "muted")
        self.info.setContentsMargins(16, 10, 16, 10)
        layout.addWidget(self.info)

    def set_image(self, image):
        self.view.set_image(image)
        if image is not None:
            h, w = image.shape[:2]
            self.info.setText(f"{w:,} × {h:,} px · RGB / 8 位")


class Worker(QThread):
    succeeded = pyqtSignal(object, str, float)
    failed = pyqtSignal(str)

    def __init__(self, key, image, parameters, second=None, channels=None, parent=None):
        super().__init__(parent)
        self.key, self.image, self.parameters = key, image, parameters
        self.second, self.channels = second, channels

    def run(self):
        start = time.perf_counter()
        try:
            result = process(self.key, self.image, self.parameters, second=self.second, channels=self.channels)
            self.succeeded.emit(result, OPERATION_MAP[self.key].name, time.perf_counter() - start)
        except Exception as error:
            logging.exception("Image operation failed: %s", self.key)
            self.failed.emit(str(error))


class ImageProcessingApp(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings or QSettings("LotusXanderYang", "ImageToolbox")
        self.history = History()
        self.original_image = self.path = self.saved_revision = None
        self.second_image = self.channels = self.file_channels = None
        self.worker = None
        self.busy = False
        self.selected_key = "equalize"
        self.controls, self.parameter_values = {}, {}
        self.setWindowIcon(QIcon(str(resource("assets/icon.svg"))))
        self.setMinimumSize(1000, 640)
        self.resize(1380, 860)
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._build_menu()
        self._filter_tools()
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.update_actions()

    @property
    def current_image(self):
        return self.history.current.image if self.history.current else None

    @property
    def dirty(self):
        return bool(self.history.current and self.history.current.revision != self.saved_revision)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame()
        header.setObjectName("header")
        row = QHBoxLayout(header)
        row.setContentsMargins(24, 16, 24, 16)
        row.setSpacing(12)
        icon = QLabel()
        icon.setPixmap(self.windowIcon().pixmap(32, 32))
        row.addWidget(icon)
        brand = QVBoxLayout()
        brand.setSpacing(2)
        brand.addWidget(label("图像工具箱", "brand"))
        brand.addWidget(label("调整 · 对照 · 导出", "muted"))
        row.addLayout(brand)
        row.addSpacing(16)
        self.open_button = button("打开图像", self.open_image, tooltip="Ctrl+O · 支持拖放图像到窗口")
        self.undo_button = button("撤销", self.undo, tooltip="Ctrl+Z")
        self.redo_button = button("重做", self.redo, tooltip="Ctrl+Shift+Z")
        self.reset_button = button("恢复原图", self.reset_image, tooltip="恢复刚打开的图像，仍可撤销")
        for widget in (self.open_button, self.undo_button, self.redo_button, self.reset_button):
            row.addWidget(widget)
        row.addStretch()
        row.addWidget(label(f"v{__version__}", "badge"))
        self.save_button = button("保存图像", self.save_result, True, "Ctrl+S · 导出当前结果")
        row.addWidget(self.save_button)
        layout.addWidget(header)
        body = QHBoxLayout()
        body.setContentsMargins(16, 16, 16, 16)
        body.setSpacing(12)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("panel")
        self.sidebar.setMinimumWidth(192)
        self.sidebar.setMaximumWidth(240)
        left = QVBoxLayout(self.sidebar)
        left.setContentsMargins(16, 16, 16, 16)
        left.setSpacing(12)
        left.addWidget(label("处理工具", "section"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索功能…")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("搜索图像处理功能")
        self.search.textChanged.connect(self._filter_tools)
        left.addWidget(self.search)
        self.category = QComboBox()
        self.category.addItems(["全部分类", *CATEGORIES])
        self.category.setAccessibleName("功能分类")
        self.category.currentTextChanged.connect(self._filter_tools)
        left.addWidget(self.category)
        self.tools = QListWidget()
        self.tools.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tools.setAccessibleName("可用处理工具")
        self.tools.currentItemChanged.connect(self._select_tool)
        left.addWidget(self.tools, 1)
        self.tool_count = label("", "muted")
        left.addWidget(self.tool_count)
        left.addWidget(button("试用示例图像", self.load_demo, tooltip="内置 NASA 照片，可离线试用"))
        body.addWidget(self.sidebar)

        center = QWidget()
        workspace = QVBoxLayout(center)
        workspace.setContentsMargins(0, 0, 0, 0)
        workspace.setSpacing(12)
        bar = QHBoxLayout()
        bar.addWidget(label("图像工作台", "section"))
        bar.addStretch()
        self.compare = QCheckBox("对照原图")
        self.compare.setChecked(True)
        self.compare.toggled.connect(self._toggle_compare)
        bar.addWidget(self.compare)
        self.zoom = QComboBox()
        self.zoom.addItems(["适应窗口", "25%", "50%", "100%", "200%", "400%"])
        self.zoom.setMinimumWidth(112)
        self.zoom.setAccessibleName("图像显示比例")
        self.zoom.currentTextChanged.connect(self._set_zoom)
        bar.addWidget(self.zoom)
        workspace.addLayout(bar)
        self.notice = label("", "notice", True)
        self.notice.hide()
        workspace.addWidget(self.notice)
        self.empty = QFrame()
        self.empty.setObjectName("panel")
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.setContentsMargins(32, 32, 32, 32)
        empty_layout.addStretch()
        for text, name in (("从一张图像开始", "brand"), ("拖放图像到这里，或点击“打开图像”\n支持 PNG、JPEG、BMP、TIFF 与 WebP", "muted")):
            text_label = label(text, name, True)
            text_label.setAlignment(Qt.AlignCenter)
            empty_layout.addWidget(text_label)
        empty_layout.addSpacing(16)
        open_row = QHBoxLayout()
        open_row.addStretch()
        open_row.addWidget(button("打开图像", self.open_image, True))
        open_row.addStretch()
        empty_layout.addLayout(open_row)
        empty_layout.addStretch()
        hint = label("1  打开图像   →   2  选择工具并应用   →   3  保存结果", "muted", True)
        hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(hint)
        workspace.addWidget(self.empty, 1)
        self.previews = QSplitter(Qt.Horizontal)
        self.previews.setChildrenCollapsible(False)
        self.original_preview = Preview("原始图像", "只读")
        self.result_preview = Preview("当前结果", "待处理")
        self.previews.addWidget(self.original_preview)
        self.previews.addWidget(self.result_preview)
        self.previews.setSizes([400, 400])
        self.original_preview.view.zoom_changed.connect(self._sync_zoom)
        self.result_preview.view.zoom_changed.connect(self._sync_zoom)
        self.previews.hide()
        workspace.addWidget(self.previews, 1)
        self.file_label = label("图像在本机处理，无需联网或 API Key。", "muted")
        self.file_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        workspace.addWidget(self.file_label)
        body.addWidget(center, 1)

        self.inspector = QFrame()
        self.inspector.setObjectName("panel")
        self.inspector.setFixedWidth(280)
        right = QVBoxLayout(self.inspector)
        right.setContentsMargins(16, 16, 16, 16)
        right.setSpacing(12)
        right.addWidget(label("工具参数", "section"))
        self.operation_title = label("", "section", True)
        right.addWidget(self.operation_title)
        self.description = label("", "muted", True)
        right.addWidget(self.description)
        self.parameters_scroll = QScrollArea()
        self.parameters_scroll.setWidgetResizable(True)
        right.addWidget(self.parameters_scroll, 1)
        self.defaults_button = button("重置参数", self.reset_parameters)
        right.addWidget(self.defaults_button)
        right.addWidget(label("处理输入", "muted"))
        self.input_source = QComboBox()
        self.input_source.addItems(["当前结果（连续处理）", "原始图像（独立处理）"])
        self.input_source.setAccessibleName("图像处理输入来源")
        self.input_source.currentIndexChanged.connect(self._source_changed)
        right.addWidget(self.input_source)
        self.apply_button = button("应用处理", self.apply_current_function, True, "Ctrl+Enter")
        right.addWidget(self.apply_button)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 0)
        self.progress.hide()
        right.addWidget(self.progress)
        right.addWidget(label("可连续应用多个工具；撤销不会修改原文件。", "muted", True))
        body.addWidget(self.inspector)
        layout.addLayout(body, 1)
        self.statusBar().showMessage("打开图像，或点击左下角示例图像开始试用。")

    def _build_menu(self):
        self.actions = {}
        menus = (
            ("文件", (("open", "打开图像…", "Ctrl+O", self.open_image), ("save", "保存图像…", "Ctrl+S", self.save_result), ("demo", "打开示例图像", "", self.load_demo), ("quit", "退出", "Ctrl+Q", self.close))),
            ("编辑", (("undo", "撤销", "Ctrl+Z", self.undo), ("redo", "重做", "Ctrl+Shift+Z", self.redo), ("reset", "恢复原图", "", self.reset_image), ("apply", "应用当前处理", "Ctrl+Return", self.apply_current_function))),
            ("帮助", (("guide", "快速使用指南", "F1", self.show_help), ("github", "访问 GitHub 项目", "", lambda: QDesktopServices.openUrl(QUrl(REPOSITORY))), ("licenses", "许可证与对应源码", "", self.show_licenses), ("about", "关于图像工具箱", "", self.show_about))),
        )
        for menu_name, items in menus:
            menu = self.menuBar().addMenu(menu_name)
            for key, text, shortcut, callback in items:
                action = QAction(text, self)
                if shortcut:
                    action.setShortcut(QKeySequence(shortcut))
                action.triggered.connect(callback)
                menu.addAction(action)
                self.actions[key] = action

    def _remember_parameters(self):
        if self.controls:
            self.parameter_values[self.selected_key] = self.get_parameters()

    def get_parameters(self):
        values = {}
        for key, widget in self.controls.items():
            if isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                values[key] = widget.text()
            else:
                values[key] = widget.value()
        return values

    def _filter_tools(self, *_):
        self.tools.blockSignals(True)
        self.tools.clear()
        needle = self.search.text().strip().casefold()
        category = self.category.currentText()
        for op in OPERATIONS:
            if category != "全部分类" and op.category != category:
                continue
            if needle and needle not in f"{op.name} {op.category} {op.key} {op.description}".casefold():
                continue
            item = QListWidgetItem(op.name)
            item.setData(Qt.UserRole, op.key)
            item.setToolTip(f"{op.category} · {op.description}")
            self.tools.addItem(item)
            if op.key == self.selected_key:
                self.tools.setCurrentItem(item)
        if not self.tools.currentItem() and self.tools.count():
            self.tools.setCurrentRow(0)
        self.tools.blockSignals(False)
        self.tool_count.setText(f"{self.tools.count()} 个工具" if self.tools.count() else "没有匹配的功能，请换个关键词")
        self._select_tool(self.tools.currentItem())

    def select_operation(self, key):
        self.search.clear()
        self.category.setCurrentIndex(0)
        for i in range(self.tools.count()):
            if self.tools.item(i).data(Qt.UserRole) == key:
                self.tools.setCurrentRow(i)
                return

    def _select_tool(self, item, *_):
        self._remember_parameters()
        if item is None:
            self.operation_title.setText("没有匹配的工具")
            self.description.setText("调整搜索关键词或功能分类即可继续。")
            self.update_actions()
            return
        self.selected_key = item.data(Qt.UserRole)
        op = OPERATION_MAP[self.selected_key]
        self.operation_title.setText(op.name)
        self.description.setText(op.description)
        self._build_parameters()
        self.update_actions()

    def _build_parameters(self):
        self.controls = {}
        page = QWidget()
        page.setObjectName("parameterPage")
        form = QVBoxLayout(page)
        form.setContentsMargins(0, 8, 8, 0)
        form.setSpacing(12)
        op = OPERATION_MAP[self.selected_key]
        saved = self.parameter_values.get(op.key, {})
        for field in op.parameters:
            value = saved.get(field.key, field.default)
            if field.choices:
                widget = QComboBox()
                widget.addItems(field.choices)
                widget.setCurrentText(value)
            elif isinstance(field.default, bool):
                widget = QCheckBox(field.label)
                widget.setChecked(value)
            elif isinstance(field.default, int):
                widget = QSpinBox()
                widget.setRange(int(field.minimum), int(field.maximum))
                widget.setSingleStep(int(field.step))
                widget.setValue(value)
            elif isinstance(field.default, float):
                widget = QDoubleSpinBox()
                widget.setDecimals(3 if field.minimum == .001 else 2)
                widget.setRange(field.minimum, field.maximum)
                widget.setSingleStep(field.step)
                widget.setValue(value)
            else:
                widget = QLineEdit(value)
                widget.setToolTip(value)
            widget.setAccessibleName(field.label)
            if not isinstance(widget, QCheckBox):
                caption = label(field.label)
                caption.setBuddy(widget)
                form.addWidget(caption)
            form.addWidget(widget)
            self.controls[field.key] = widget
        if not op.parameters:
            form.addWidget(label("此工具无需调整参数。", "muted", True))
        if op.key == "mixup":
            form.addWidget(button("加载第二张图像…", self.load_second))
            self.second_label = label("已加载第二张图像" if self.second_image is not None else "尚未加载第二张图像", "muted", True)
            form.addWidget(self.second_label)
        if op.key == "merge":
            form.addWidget(button("选择 B / G / R 通道…", self.load_channels))
            self.channels_label = label("已加载三个通道" if self.file_channels else "按 B、G、R 顺序逐个选择", "muted", True)
            form.addWidget(self.channels_label)
        form.addStretch()
        old = self.parameters_scroll.takeWidget()
        if old:
            old.deleteLater()
        self.parameters_scroll.setWidget(page)

    def reset_parameters(self):
        self.parameter_values.pop(self.selected_key, None)
        self._build_parameters()
        self._image_defaults()

    def _image_defaults(self):
        image = self.input_image()
        if image is None:
            return
        h, w = image.shape[:2]
        if "crop" not in self.parameter_values:
            self.parameter_values["crop"] = {"x": 0, "y": 0, "width": min(400, w), "height": min(300, h)}
        if "perspective" not in self.parameter_values:
            self.parameter_values["perspective"] = {"points": f"0,0 {w-1},0 {w-1},{h-1} 0,{h-1}", "width": min(w, 8192), "height": min(h, 8192)}
        if self.selected_key in {"crop", "perspective"}:
            self._build_parameters()

    def _source_changed(self):
        self._remember_parameters()
        self.parameter_values.pop("crop", None)
        self.parameter_values.pop("perspective", None)
        self._image_defaults()

    def input_image(self):
        return self.original_image if self.input_source.currentIndex() == 1 else self.current_image

    def show_notice(self, text, error=False):
        self.notice.setText(text)
        self.notice.setProperty("error", error)
        self.notice.style().unpolish(self.notice)
        self.notice.style().polish(self.notice)
        self.notice.show()
        self.statusBar().showMessage(text)

    def confirm_discard(self):
        if not self.dirty:
            return True
        answer = QMessageBox.question(self, "结果尚未保存", "是否先保存当前处理结果？", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if answer == QMessageBox.Save:
            return self.save_result()
        return answer == QMessageBox.Discard

    def open_image(self, *_):
        if self.busy:
            return
        path, _ = QFileDialog.getOpenFileName(self, "打开图像", self.settings.value("last_dir", ""), IMAGE_FILTER)
        if path:
            self.load_path(path)

    def load_path(self, path, confirm=True):
        if self.busy:
            return False
        try:
            image = read_image(path)
            if confirm and not self.confirm_discard():
                return False
            self.set_document(image, Path(path))
            self.settings.setValue("last_dir", str(Path(path).parent))
            return True
        except Exception as error:
            self.show_notice(str(error), True)
            return False

    def set_document(self, image, path=None):
        self.original_image = image.copy()
        self.path = path
        self.saved_revision = self.history.reset(image).revision
        self.channels = self.file_channels = self.second_image = None
        self.parameter_values.clear()
        self.input_source.blockSignals(True)
        self.input_source.setCurrentIndex(0)
        self.input_source.blockSignals(False)
        self._build_parameters()
        self._image_defaults()
        self.original_preview.set_image(image)
        self.empty.hide()
        self.previews.show()
        self.original_preview.setVisible(self.compare.isChecked())
        self.notice.hide()
        self.refresh_result()
        name = str(path) if path else "内置示例 · NASA / Eileen Collins"
        self.file_label.setText(name)
        self.file_label.setToolTip(name)
        self.statusBar().showMessage("图像已打开。选择工具，调整参数后点击“应用处理”。")

    def load_demo(self, *_):
        if not self.busy and self.confirm_discard():
            try:
                self.set_document(read_image(resource("assets/demo.png")))
            except Exception as error:
                self.show_notice(str(error), True)

    def load_second(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载第二张图像", self.settings.value("last_dir", ""), IMAGE_FILTER)
        if path:
            try:
                self.second_image = read_image(path)
                self.second_label.setText(Path(path).name)
                self.second_label.setToolTip(path)
            except Exception as error:
                self.show_notice(str(error), True)

    def load_channels(self):
        parts = []
        for channel in ("B（蓝）", "G（绿）", "R（红）"):
            path, _ = QFileDialog.getOpenFileName(self, f"选择 {channel} 通道图像", self.settings.value("last_dir", ""), IMAGE_FILTER)
            if not path:
                return
            try:
                parts.append(cv2.cvtColor(read_image(path), cv2.COLOR_BGR2GRAY))
            except Exception as error:
                self.show_notice(str(error), True)
                return
        if any(part.shape != parts[0].shape for part in parts):
            self.show_notice("三个通道尺寸不同，请选择同尺寸的图像。", True)
            return
        self.file_channels = tuple(parts)
        self.controls["source"].setCurrentText("从三张图像加载")
        self.channels_label.setText("已加载三个通道（B / G / R）")

    def apply_current_function(self, *_):
        if self.busy or self.input_image() is None or not self.tools.currentItem():
            return
        values = self.get_parameters()
        self.parameter_values[self.selected_key] = values
        channels = self.file_channels if values.get("source") == "从三张图像加载" else self.channels
        self.worker = Worker(self.selected_key, self.input_image(), values, self.second_image, channels, self)
        self.worker.succeeded.connect(self._processed)
        self.worker.failed.connect(lambda message: self.show_notice(message, True))
        self.worker.finished.connect(self._worker_finished)
        self.busy = True
        self.notice.hide()
        self.progress.show()
        self.apply_button.setText("正在处理…")
        self.statusBar().showMessage(f"正在应用：{OPERATION_MAP[self.selected_key].name}…")
        self.update_actions()
        self.worker.start()

    def _processed(self, result, name, elapsed):
        self.history.push(result.image, name)
        if result.channels is not None:
            self.channels = result.channels
        self.refresh_result()
        self.show_notice(f"已应用{name} · {elapsed:.2f} 秒" + ("。" + result.detail if result.detail else ""))

    def _worker_finished(self):
        worker = self.worker
        self.busy = False
        self.worker = None
        self.apply_button.setText("应用处理")
        self.progress.hide()
        self.update_actions()
        if worker:
            worker.deleteLater()

    def refresh_result(self):
        if self.history.current:
            self.result_preview.set_image(self.current_image)
            self.result_preview.badge.setText(self.history.current.label)
        self.zoom.blockSignals(True)
        self.zoom.setCurrentIndex(0)
        self.zoom.blockSignals(False)
        self.original_preview.view.fit_image()
        self.update_actions()

    def update_actions(self):
        loaded, enabled = self.current_image is not None, not self.busy
        can_apply = loaded and enabled and bool(self.tools.currentItem())
        states = {"open": enabled, "demo": enabled, "apply": can_apply, "save": loaded and enabled, "undo": enabled and self.history.can_undo, "redo": enabled and self.history.can_redo, "reset": loaded and enabled}
        for name in ("open", "apply", "save", "undo", "redo", "reset"):
            getattr(self, name + "_button").setEnabled(states[name])
        self.sidebar.setEnabled(enabled)
        self.parameters_scroll.setEnabled(enabled)
        self.defaults_button.setEnabled(enabled and bool(self.tools.currentItem()))
        self.input_source.setEnabled(enabled)
        self.compare.setEnabled(loaded)
        self.zoom.setEnabled(loaded)
        if hasattr(self, "actions"):
            for key, state in states.items():
                self.actions[key].setEnabled(state)
        name = self.path.name if self.path else "示例图像" if loaded else "未打开图像"
        self.setWindowTitle(f"{'* ' if self.dirty else ''}{name} — 图像工具箱 {__version__}")

    def undo(self, *_):
        if not self.busy and self.history.can_undo:
            self.history.undo()
            self.refresh_result()
            self.show_notice("已撤销上一步处理。")

    def redo(self, *_):
        if not self.busy and self.history.can_redo:
            self.history.redo()
            self.refresh_result()
            self.show_notice("已重做处理。")

    def reset_image(self, *_):
        if not self.busy and self.original_image is not None:
            self.history.push(self.original_image, "恢复原图")
            self.refresh_result()
            self.show_notice("已恢复原图，可撤销此操作。")

    def save_result(self, *_):
        if self.busy or self.current_image is None:
            return False
        folder = str(self.path.parent) if self.path else self.settings.value("last_dir", "")
        stem = self.path.stem if self.path else "示例图像"
        path, selected = QFileDialog.getSaveFileName(self, "保存当前图像", str(Path(folder) / f"{stem}_处理结果.png"), "PNG (*.png);;JPEG (*.jpg);;WebP (*.webp);;TIFF (*.tif);;BMP (*.bmp)")
        if not path:
            return False
        if not Path(path).suffix:
            path += {"JPEG": ".jpg", "WebP": ".webp", "TIFF": ".tif", "BMP": ".bmp"}.get(selected.split()[0], ".png")
        try:
            save_image(path, self.current_image)
            self.saved_revision = self.history.current.revision
            self.settings.setValue("last_dir", str(Path(path).parent))
            self.update_actions()
            self.show_notice(f"已保存：{path}")
            return True
        except Exception as error:
            self.show_notice(f"保存失败：{error}", True)
            return False

    def _toggle_compare(self, checked):
        self.original_preview.setVisible(checked)
        self._set_zoom(self.zoom.currentText())

    def _set_zoom(self, text):
        for preview in (self.original_preview, self.result_preview):
            if text == "适应窗口":
                preview.view.fit_image()
            elif text.endswith("%"):
                preview.view.set_zoom(float(text[:-1]) / 100)

    def _sync_zoom(self, factor):
        self.zoom.blockSignals(True)
        if factor == 0:
            self.zoom.setCurrentIndex(0)
        else:
            text = f"{round(factor * 100)}%"
            if self.zoom.findText(text) < 0:
                if self.zoom.count() > 6:
                    self.zoom.removeItem(6)
                self.zoom.addItem(text)
            self.zoom.setCurrentText(text)
        self.zoom.blockSignals(False)
        for preview in (self.original_preview, self.result_preview):
            preview.view.fit_image() if factor == 0 else preview.view.set_zoom(factor)

    def dragEnterEvent(self, event):
        if not self.busy and event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if url.isLocalFile():
                self.load_path(url.toLocalFile())
                break
        event.acceptProposedAction()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "previews"):
            # Stack only when enough vertical space exists for both full panels.
            vertical = self.width() < 1200 and self.height() >= 860
            self.previews.setOrientation(Qt.Vertical if vertical else Qt.Horizontal)

    def show_help(self):
        QMessageBox.information(self, "快速使用指南", "1. 打开或拖入图像，也可试用内置示例。\n2. 在左侧选择工具，在右侧调整参数。\n3. 点击“应用处理”，对照原图与结果。\n4. 默认基于当前结果连续处理，可切换到原始图像。\n5. 使用撤销 / 重做回退，点击“保存图像”导出。\n\n预览：滚轮缩放，拖动平移，双击适应窗口。\n快捷键：Ctrl+O 打开，Ctrl+S 保存，Ctrl+Z 撤销，\nCtrl+Shift+Z 重做，Ctrl+Enter 应用，F1 帮助。\n\n透明通道和高位深图像会转换为 8 位 RGB 工作图。")

    def show_about(self):
        QMessageBox.about(self, "关于图像工具箱", f"图像工具箱 {__version__}\n\n28 个图像处理工具 · 全部在本机处理\n\n初始版本代码由 DeepSeek 4.0 API 生成。\n后续版本经过 GUI、工程化和打包改进。\n运行无需 API Key。\n\nGPL-3.0-or-later · PyQt5 / OpenCV / scikit-image\n示例照片：NASA / Eileen Collins（公有领域）\n应用图标：Lucide image（ISC 许可证）\n\n{REPOSITORY}")

    def show_licenses(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("许可证与对应源码")
        dialog.resize(800, 600)
        layout = QVBoxLayout(dialog)
        tabs = QTabWidget()
        for title, name in (("软件 GPL", "COPYING"), ("应用源码 MIT", "LICENSE"), ("第三方声明", "THIRD_PARTY_NOTICES.md"), ("对应源码", "DEPENDENCY_SOURCES.md"), ("字体许可", "assets/fonts/OFL.txt")):
            browser = QTextBrowser()
            browser.setOpenExternalLinks(True)
            source = resource(name)
            text = source.read_text(encoding="utf-8") if source.exists() else "请访问 GitHub 仓库查看此文件。"
            browser.setMarkdown(text) if name.endswith(".md") else browser.setPlainText(text)
            tabs.addTab(browser, title)
        layout.addWidget(tabs)
        layout.addWidget(button("关闭", dialog.accept))
        dialog.exec_()

    def closeEvent(self, event):
        if self.busy:
            self.show_notice("正在处理图像，请等待完成后再关闭窗口。")
            event.ignore()
        elif self.confirm_discard():
            self.settings.setValue("geometry", self.saveGeometry())
            event.accept()
        else:
            event.ignore()


def main(argv=None):
    parser = argparse.ArgumentParser(description="图像工具箱")
    parser.add_argument("image", nargs="?", help="启动时打开的图像路径")
    parser.add_argument("--demo", action="store_true", help="启动时加载内置示例")
    parser.add_argument("--self-test", metavar="DIRECTORY", help="离线打包自检，写入指定目录后退出")
    args = parser.parse_args(argv)
    if args.self_test:
        output = Path(args.self_test).resolve()
        output.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        logging.basicConfig(filename=output / "self-test.log", level=logging.INFO, encoding="utf-8")
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication([sys.argv[0]])
    app.setStyle("Fusion")
    family = "Microsoft YaHei UI" if sys.platform == "win32" else "sans-serif"
    for font_path in sorted(resource("assets/fonts").glob("*.otf")):
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families:
            family = families[0]
    app.setFont(QFont(family, 10))
    settings = QSettings(str(output / "test-settings.ini"), QSettings.IniFormat) if args.self_test else None
    window = ImageProcessingApp(settings)
    window.show()
    if args.self_test:
        from .self_test import run_self_test
        QTimer.singleShot(100, lambda: run_self_test(app, window, output))
    elif args.image:
        QTimer.singleShot(0, lambda: window.load_path(args.image))
    elif args.demo:
        QTimer.singleShot(0, window.load_demo)
    return app.exec_()
