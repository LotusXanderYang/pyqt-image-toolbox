"""Unicode-safe local image loading and atomic exports."""

import os
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .processing import validate_image

IMAGE_FILTER = "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp);;所有文件 (*)"


def read_image(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError("文件不存在，请重新选择图像。")
    if path.stat().st_size > 512 * 1024 * 1024:
        raise ValueError("文件超过 512 MB，请先缩小图像。")
    try:
        encoded = np.fromfile(str(path), dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR) if encoded.size else None
        validate_image(image)
    except (cv2.error, ValueError) as error:
        raise ValueError("无法读取图像。请检查文件是否损坏、格式是否受支持或尺寸是否过大。") from error
    return image


def save_image(path, image, quality=95):
    """Encode first, then replace the target atomically; report write failures."""
    validate_image(image)
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
        raise ValueError("请使用 PNG、JPEG、BMP、TIFF 或 WebP 文件扩展名。")
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if suffix in {".jpg", ".jpeg"} else []
    ok, buffer = cv2.imencode(suffix, image, params)
    if not ok:
        raise ValueError("图像编码失败，请尝试保存为 PNG。")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".toolbox-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(buffer.tobytes())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return path
