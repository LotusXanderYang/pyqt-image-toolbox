"""Pure image operations; no widgets or filesystem side effects."""

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from skimage.restoration import wiener

MAX_PIXELS = 40_000_000


@dataclass(frozen=True)
class Parameter:
    key: str
    label: str
    default: Any
    minimum: float = 0
    maximum: float = 255
    step: float = 1
    choices: tuple = ()


@dataclass(frozen=True)
class Operation:
    key: str
    name: str
    category: str
    description: str
    parameters: tuple = ()


def p(key, label, default, minimum=0, maximum=255, step=1, choices=()):
    return Parameter(key, label, default, minimum, maximum, step, choices)


KERNEL = p("kernel", "核大小（奇数）", 3, 1, 31, 2)
ITERATIONS = p("iterations", "迭代次数", 1, 1, 10)
OPERATIONS = (
    Operation("threshold", "二值化", "基础调整", "按阈值将图像转换为黑白两种像素。", (p("threshold", "阈值", 127),)),
    Operation("gray", "灰度化", "基础调整", "保留明暗信息，去除颜色。"),
    Operation("normalize", "归一化", "基础调整", "将像素值映射到指定的最小值和最大值。", (p("minimum", "最小值", 0), p("maximum", "最大值", 255))),
    Operation("equalize", "对比度增强", "基础调整", "在亮度通道上增强对比度，保留图像颜色。", (p("adaptive", "自适应均衡（CLAHE）", True), p("clip", "对比度限制", 2.0, 1, 10, .5))),
    Operation("resize", "调整大小", "几何变换", "输入目标尺寸；保持比例时，图像将完整放入目标范围。", (p("width", "目标宽度（像素）", 800, 1, 8192), p("height", "目标高度（像素）", 600, 1, 8192), p("keep_ratio", "保持宽高比", True))),
    Operation("flip", "翻转", "几何变换", "改变图像的水平或垂直方向。", (p("direction", "方向", "水平", choices=("水平", "垂直", "水平和垂直")),)),
    Operation("rotate", "旋转", "几何变换", "正数逆时针旋转；可扩大画布以保留完整图像。", (p("angle", "角度（度）", 15, -180, 180), p("expand", "扩大画布，避免裁切", True))),
    Operation("crop", "裁剪", "几何变换", "从左上角坐标开始，裁剪指定宽高。坐标以处理输入图像为准。", (p("x", "左上角 X", 0, 0, 8192), p("y", "左上角 Y", 0, 0, 8192), p("width", "宽度（像素）", 400, 1, 8192), p("height", "高度（像素）", 300, 1, 8192))),
    Operation("perspective", "透视校正", "几何变换", "按左上、右上、右下、左下输入四个点，例如：0,0 300,0 300,300 0,300。", (p("points", "四个源点坐标", "0,0 300,0 300,300 0,300"), p("width", "输出宽度", 400, 1, 8192), p("height", "输出高度", 400, 1, 8192))),
    Operation("gaussian", "高斯滤波", "滤波去噪", "平滑细小噪声；核越大，模糊越明显。", (KERNEL, p("sigma", "标准差 Sigma", 1.0, .1, 10, .1))),
    Operation("mean", "均值滤波", "滤波去噪", "以邻域平均值平滑图像。", (KERNEL,)),
    Operation("wiener", "维纳去模糊", "滤波去噪", "使用模拟高斯模糊核恢复灰度图。效果取决于核与实际模糊是否匹配。", (p("kernel", "模拟模糊核（奇数）", 5, 1, 21, 2), p("balance", "去噪平衡", .1, .001, 1, .01))),
    Operation("bilateral", "双边滤波", "滤波去噪", "平滑噪声，同时尽量保留边缘。", (p("diameter", "邻域直径", 9, 1, 31), p("sigma_color", "颜色标准差", 75.0, 1, 200, 1), p("sigma_space", "空间标准差", 75.0, 1, 200, 1))),
    *(Operation(key, name, "形态学", description, (KERNEL, ITERATIONS)) for key, name, description in (
        ("erode", "腐蚀", "收缩亮色区域，消除细小亮点。"),
        ("dilate", "膨胀", "扩展亮色区域，连接相邻结构。"),
        ("open", "开运算", "先腐蚀再膨胀，去除细小亮色噪点。"),
        ("close", "闭运算", "先膨胀再腐蚀，填补细小暗色孔洞。"),
        ("gradient", "形态学梯度", "提取膨胀与腐蚀结果之差，突出轮廓。"),
        ("tophat", "顶帽运算", "提取比周围更亮的细小结构。"),
    )),
    Operation("white_balance", "自动白平衡", "色彩与通道", "使用灰度世界算法校正整体偏色。"),
    Operation("color_space", "色彩空间观察", "色彩与通道", "将三个色彩空间通道并排显示为灰度图，避免错误的彩色预览。导出内容也是通道拼图。", (p("space", "色彩空间", "HSV", choices=("HSV", "YUV", "Lab", "灰度")),)),
    Operation("split", "通道分离", "色彩与通道", "查看 B、G 或 R 通道，并缓存本次分离的三个通道供合成使用。", (p("channel", "查看通道", "B（蓝）", choices=("B（蓝）", "G（绿）", "R（红）")),)),
    Operation("merge", "通道合成", "色彩与通道", "合成最近一次分离的通道，或按 B、G、R 顺序选择三张同尺寸图像。", (p("source", "通道来源", "最近分离的通道", choices=("最近分离的通道", "从三张图像加载")),)),
    Operation("random_crop", "随机裁剪", "数据增强", "按比例随机截取图像，始终保留至少一个像素。", (p("ratio", "保留比例", .8, .1, 1, .05),)),
    Operation("random_rotate", "随机旋转", "数据增强", "在给定范围内随机旋转，保持原始画布尺寸。", (p("angle", "最大角度（度）", 30, 0, 180),)),
    Operation("random_flip", "随机翻转", "数据增强", "以指定概率水平翻转图像。", (p("probability", "翻转概率", .5, 0, 1, .05),)),
    Operation("random_tone", "随机亮度 / 对比度", "数据增强", "随机调整亮度和对比度。变化幅度为 0 时保持原图。", (p("brightness", "亮度变化幅度", 30, 0, 100), p("contrast", "对比度变化幅度", .2, 0, .9, .05))),
    Operation("mixup", "Mixup 混合", "数据增强", "从 Beta 分布采样混合比例；第二张图像自动缩放至输入尺寸。", (p("alpha", "Beta 分布参数 α", .5, .1, 2, .1),)),
)
OPERATION_MAP = {op.key: op for op in OPERATIONS}
CATEGORIES = tuple(dict.fromkeys(op.category for op in OPERATIONS))


@dataclass
class Result:
    image: np.ndarray
    channels: tuple | None = None
    detail: str = ""


def validate_image(image):
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        raise ValueError("图像为空，请重新打开有效的图像文件。")
    if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("处理输入必须是 8 位、三通道图像。")
    check_size(image.shape[1], image.shape[0])


def check_size(width, height):
    if width < 1 or height < 1 or width * height > MAX_PIXELS:
        raise ValueError("输出尺寸无效，请将图像控制在 4000 万像素以内。")


def rotate(image, angle, expand=False):
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2), angle, 1)
    if expand:
        c, s = abs(matrix[0, 0]), abs(matrix[0, 1])
        new_w = max(1, int(np.ceil(w * c + h * s - 1e-9)))
        new_h = max(1, int(np.ceil(h * c + w * s - 1e-9)))
        check_size(new_w, new_h)
        matrix[0, 2] += (new_w - w) / 2
        matrix[1, 2] += (new_h - h) / 2
        w, h = new_w, new_h
    return cv2.warpAffine(image, matrix, (w, h), borderMode=cv2.BORDER_CONSTANT)


def process(key, image, parameters=None, *, second=None, channels=None, rng=None):
    """Return a fresh uint8 BGR image. Failed operations never alter input."""
    validate_image(image)
    if key not in OPERATION_MAP:
        raise ValueError("未知的处理功能。")
    op = OPERATION_MAP[key]
    values = {field.key: field.default for field in op.parameters}
    values.update(parameters or {})
    for field in op.parameters:
        value = values[field.key]
        if field.choices:
            if value not in field.choices:
                raise ValueError(f"{field.label}：请选择列表中的选项。")
        elif isinstance(field.default, bool):
            if not isinstance(value, bool):
                raise ValueError(f"{field.label}：请输入布尔值。")
        elif isinstance(field.default, (int, float)):
            if not isinstance(value, (int, float)) or not np.isfinite(value):
                raise ValueError(f"{field.label}：请输入有效数字。")
            if not field.minimum <= value <= field.maximum:
                raise ValueError(f"{field.label}：应在 {field.minimum:g} 到 {field.maximum:g} 之间。")
            if isinstance(field.default, int) and int(value) != value:
                raise ValueError(f"{field.label}：请输入整数。")
            if isinstance(field.default, int):
                values[field.key] = int(value)
    v = values
    h, w = image.shape[:2]
    rng = rng if rng is not None else np.random.default_rng()
    cached_channels = None
    detail = ""
    gray = lambda: cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    bgr = lambda value: cv2.cvtColor(value, cv2.COLOR_GRAY2BGR)
    if "kernel" in v and v["kernel"] % 2 == 0:
        raise ValueError("核大小必须为奇数，例如 3、5、7。")

    if key == "threshold":
        out = bgr(cv2.threshold(gray(), v["threshold"], 255, cv2.THRESH_BINARY)[1])
    elif key == "gray":
        out = bgr(gray())
    elif key == "normalize":
        if v["minimum"] >= v["maximum"]:
            raise ValueError("最小值必须小于最大值。")
        out = cv2.normalize(image, None, v["minimum"], v["maximum"], cv2.NORM_MINMAX)
    elif key == "equalize":
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        if v["adaptive"]:
            lab[:, :, 0] = cv2.createCLAHE(clipLimit=v["clip"], tileGridSize=(8, 8)).apply(lab[:, :, 0])
        else:
            lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
        out = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    elif key == "resize":
        width, height = v["width"], v["height"]
        if v["keep_ratio"]:
            scale = min(width / w, height / h)
            width, height = max(1, round(w * scale)), max(1, round(h * scale))
        check_size(width, height)
        out = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA if width < w else cv2.INTER_CUBIC)
    elif key == "flip":
        out = cv2.flip(image, {"水平": 1, "垂直": 0, "水平和垂直": -1}[v["direction"]])
    elif key == "rotate":
        out = rotate(image, v["angle"], v["expand"])
    elif key == "crop":
        x, y, width, height = (v[k] for k in ("x", "y", "width", "height"))
        if x >= w or y >= h or x + width > w or y + height > h:
            raise ValueError(f"裁剪超出图像边界（{w} × {h}）。请缩小宽高或调整起点。")
        out = image[y:y + height, x:x + width].copy()
    elif key == "perspective":
        try:
            points = np.array([[float(n) for n in pair.split(",")] for pair in v["points"].replace("，", ",").split()], np.float32)
        except (TypeError, ValueError):
            raise ValueError("源点格式错误，请使用 x,y x,y x,y x,y。") from None
        if points.shape != (4, 2) or not np.isfinite(points).all():
            raise ValueError("请提供四个有效的源点坐标。")
        if (points < 0).any() or (points[:, 0] >= w).any() or (points[:, 1] >= h).any():
            raise ValueError(f"源点应位于 {w} × {h} 的输入图像内。")
        if not cv2.isContourConvex(points) or abs(cv2.contourArea(points)) < 1:
            raise ValueError("四个点必须按顺序组成有效凸四边形，不能重合或交叉。")
        width, height = v["width"], v["height"]
        if width < 2 or height < 2:
            raise ValueError("透视校正的宽高至少为 2 像素。")
        check_size(width, height)
        target = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
        out = cv2.warpPerspective(image, cv2.getPerspectiveTransform(points, target), (width, height))
    elif key == "gaussian":
        out = cv2.GaussianBlur(image, (v["kernel"], v["kernel"]), v["sigma"])
    elif key == "mean":
        out = cv2.blur(image, (v["kernel"], v["kernel"]))
    elif key == "wiener":
        kernel = cv2.getGaussianKernel(v["kernel"], -1)
        psf = kernel @ kernel.T
        restored = wiener(gray().astype(np.float64) / 255, psf, balance=v["balance"], clip=False)
        out = bgr(np.clip(np.nan_to_num(restored) * 255, 0, 255).astype(np.uint8))
    elif key == "bilateral":
        out = cv2.bilateralFilter(image, v["diameter"], v["sigma_color"], v["sigma_space"])
    elif key in {"erode", "dilate", "open", "close", "gradient", "tophat"}:
        kernel = np.ones((v["kernel"], v["kernel"]), np.uint8)
        codes = {"erode": cv2.MORPH_ERODE, "dilate": cv2.MORPH_DILATE, "open": cv2.MORPH_OPEN, "close": cv2.MORPH_CLOSE, "gradient": cv2.MORPH_GRADIENT, "tophat": cv2.MORPH_TOPHAT}
        out = cv2.morphologyEx(image, codes[key], kernel, iterations=v["iterations"])
    elif key == "white_balance":
        averages = image.mean(axis=(0, 1))
        gains = np.divide(averages.mean(), averages, out=np.ones(3), where=averages > 0)
        out = np.clip(image.astype(np.float32) * gains, 0, 255).astype(np.uint8)
    elif key == "color_space":
        if v["space"] == "灰度":
            out = bgr(gray())
        else:
            check_size(w * 3, h)
            code = {"HSV": cv2.COLOR_BGR2HSV, "YUV": cv2.COLOR_BGR2YUV, "Lab": cv2.COLOR_BGR2LAB}[v["space"]]
            parts = cv2.split(cv2.cvtColor(image, code))
            out = bgr(np.concatenate(parts, axis=1))
            detail = f"{v['space']} 三个通道从左到右排列；显示和导出均为灰度拼图。"
    elif key == "split":
        cached_channels = tuple(c.copy() for c in cv2.split(image))
        out = bgr(cached_channels[op.parameters[0].choices.index(v["channel"])])
    elif key == "merge":
        if channels is None or len(channels) != 3:
            raise ValueError("请先分离通道，或按 B、G、R 顺序加载三张同尺寸图像。")
        if any(c.ndim != 2 or c.dtype != np.uint8 or c.shape != channels[0].shape for c in channels):
            raise ValueError("三个通道必须是相同尺寸的 8 位灰度图像。")
        check_size(channels[0].shape[1], channels[0].shape[0])
        out = cv2.merge(channels)
    elif key == "random_crop":
        height, width = max(1, round(h * v["ratio"])), max(1, round(w * v["ratio"]))
        y, x = int(rng.integers(h - height + 1)), int(rng.integers(w - width + 1))
        out = image[y:y + height, x:x + width].copy()
    elif key == "random_rotate":
        out = rotate(image, rng.uniform(-v["angle"], v["angle"]))
    elif key == "random_flip":
        out = cv2.flip(image, 1) if rng.random() < v["probability"] else image.copy()
    elif key == "random_tone":
        brightness = rng.integers(-v["brightness"], v["brightness"] + 1)
        contrast = 1 + rng.uniform(-v["contrast"], v["contrast"])
        out = np.clip(image.astype(np.float32) * contrast + brightness, 0, 255).astype(np.uint8)
    elif key == "mixup":
        if second is None:
            raise ValueError("请先加载第二张图像。")
        validate_image(second)
        weight = rng.beta(v["alpha"], v["alpha"])
        other = cv2.resize(second, (w, h)).astype(np.float32)
        out = np.clip(weight * image.astype(np.float32) + (1 - weight) * other, 0, 255).astype(np.uint8)
        detail = f"本次混合比例：输入图像 {weight:.1%}，第二张图像 {1 - weight:.1%}。"
    else:
        raise ValueError("该处理功能尚未实现。")
    out = np.ascontiguousarray(out)
    validate_image(out)
    return Result(out, cached_channels, detail)
