# 全能图像处理工具箱

一个基于 **PyQt5、OpenCV、NumPy 和 scikit-image** 的桌面图像处理工具。它提供图形化界面，可完成常见的像素调整、几何变换、滤波去噪、形态学处理、色彩处理和数据增强操作。

> AI 生成声明：本项目源代码使用 **DeepSeek 4.0 API** 生成，并经过人工整理后开源。DeepSeek 4.0 API 仅用于代码生成；运行本工具不需要配置 DeepSeek API Key。

## 功能

- 像素值调整：二值化、灰度化、归一化、直方图均衡、CLAHE
- 几何变换：缩放、翻转、旋转、裁剪、逆透视校正
- 噪声处理：高斯滤波、均值滤波、维纳滤波、双边滤波
- 形态学操作：腐蚀、膨胀、开运算、闭运算、梯度、顶帽
- 通道与色彩：白平衡、色彩空间变换、通道分离与合成
- 数据增强：随机裁剪、随机旋转、随机翻转、亮度/对比度扰动、Mixup
- 原图与处理结果预览，并支持保存为 PNG 或 JPEG

## 界面要求

- Python 3.9 或更高版本
- Windows、macOS 或 Linux 桌面环境

## 安装

建议在虚拟环境中安装依赖。

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux：

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

打开图像后，从左侧选择处理功能、调整参数并点击“应用当前功能”。确认结果后，点击“保存处理结果”即可导出。

## 使用提示

- 逆透视校正需要按“左上、右上、右下、左下”的顺序输入四个源点。
- 通道合成前需要先执行一次通道分离。
- Mixup 需要先加载第二张图像；程序会自动将它缩放到与原图相同的尺寸。
- 当前每次处理都以原始图像为输入，不会自动串联上一次处理结果。

## 项目结构

```text
pyqt-image-toolbox/
├── app.py             # 应用入口与全部图像处理功能
├── requirements.txt  # Python 依赖
├── LICENSE           # MIT 许可证
└── README.md         # 项目说明
```

## 已知限制

- 部分色彩空间（HSV、YUV、Lab）在界面预览时按普通三通道图显示，预览颜色仅用于观察数据，不代表真实 RGB 色彩。
- 维纳滤波当前以灰度图方式处理，输出为三通道灰度图。
- 大尺寸图像和较大的滤波核可能使界面短暂无响应。

## 贡献

欢迎提交 Issue 或 Pull Request。提交前请确保代码能够通过 Python 语法检查，并说明修改内容和验证方式。

## 许可证

本项目采用 [MIT License](LICENSE) 开源。

