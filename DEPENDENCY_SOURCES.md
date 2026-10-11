# 对应源码与可复现构建

本软件的应用源码、图标、示例、构建脚本、测试和依赖版本均随 GitHub `v2.0.0` 标签提供：

- [下载应用对应源码](https://github.com/LotusXanderYang/pyqt-image-toolbox/archive/refs/tags/v2.0.0.zip)
- [源码仓库](https://github.com/LotusXanderYang/pyqt-image-toolbox/tree/v2.0.0)
- 构建：Windows x64 + Python 3.13，安装 `requirements-lock.txt` 后运行 `python scripts/build_windows.py`。

未对第三方组件源码作修改。它们的完整对应源码可从下列原厂项目或 PyPI 版本页获取；请使用 `requirements-lock.txt` 中记录的版本，在版本页的 Download files 中选择 source distribution（`.tar.gz` / `.zip`）。许可证原文一并内嵌于程序，并随发行 ZIP 提供。

| 组件 | 官方源码入口 |
| --- | --- |
| Python 3.13.9 | https://www.python.org/downloads/release/python-3139/ |
| PyQt5 5.15.11 | https://pypi.org/project/PyQt5/5.15.11/#files |
| Qt 5.15.2 | https://download.qt.io/archive/qt/5.15/5.15.2/single/ |
| PyQt5-sip | https://pypi.org/project/PyQt5-sip/#files |
| NumPy | https://github.com/numpy/numpy |
| OpenCV 与 Python wheel 构建 | https://github.com/opencv/opencv-python |
| SciPy | https://github.com/scipy/scipy |
| scikit-image | https://github.com/scikit-image/scikit-image |
| Pillow | https://github.com/python-pillow/Pillow |
| NetworkX | https://github.com/networkx/networkx |
| imageio | https://github.com/imageio/imageio |
| tifffile | https://github.com/cgohlke/tifffile |
| lazy-loader | https://github.com/scientific-python/lazy-loader |
| packaging | https://github.com/pypa/packaging |
| PyInstaller（构建工具与 bootloader） | https://github.com/pyinstaller/pyinstaller |

也可使用 `python -m pip download --no-deps --no-binary=:all: --no-build-isolation <包名>==<版本>` 获取指定包的源码归档。部分源码包下载时会运行构建元数据步骤，需相应构建依赖。

软件完整组合发行按 GPL-3.0-or-later 提供，见 `COPYING`；应用自身源文件的 MIT 授权和各第三方组件原有许可均保留。重构或再次分发时，请保留这些声明。
