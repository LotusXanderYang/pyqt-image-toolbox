# 图像工具箱 · Image Toolbox

一个可离线运行的桌面图像处理工作台。左侧选择工具，右侧调整参数，中间对照原图和结果；支持连续处理、撤销重做、缩放平移和导出。

**Windows 用户可以直接下载 EXE，双击运行，无需安装 Python，也无需 API Key。**

[下载 Windows 便携版](https://github.com/LotusXanderYang/pyqt-image-toolbox/releases/latest) · [使用指南](#使用方法) · [反馈问题](https://github.com/LotusXanderYang/pyqt-image-toolbox/issues)

![图像工具箱真实界面：原始照片与灰度化结果并排对照](assets/workbench.png)

> **生成来源说明：初始版本源代码使用 DeepSeek 4.0 API 生成。** 2.0 版本在该代码基础上进行了 GUI 重设计、功能修复、模块化和桌面软件打包。DeepSeek API 用于初始代码生成；软件运行时不调用 DeepSeek API，也不需要配置密钥。

## Windows 点击即用

1. 打开 [Releases 下载页面](https://github.com/LotusXanderYang/pyqt-image-toolbox/releases/latest)。
2. 下载 `ImageToolbox-2.0.0-Windows-x64.exe`，双击运行。
3. 也可下载同名 ZIP，解压后双击 EXE；ZIP 额外包含快速指南、许可证及第三方声明。
4. 初次打开可以点击左下角“试用示例图像”，体验全部操作流程。

面向 Windows 10 / 11 的 x64 系统。依赖和开源中文字体已包含在软件内，可以离线使用。单文件程序每次启动需要先解包依赖，可能需等待数秒。当前发行版未进行代码签名；如果系统提示无法验证发布者，请先核对下载来源与 `SHA256SUMS.txt`，无需关闭系统防护。

## 使用方法

1. **打开图像**：点击顶部按钮，或把一张本地图像拖入窗口。
2. **选择工具**：左侧可按分类浏览，也可输入名称或关键词搜索。
3. **调整参数**：右侧展示对应设置和说明；“重置参数”恢复该工具默认值。
4. **应用处理**：点击右下角“应用处理”，在中间比较原图与结果。
5. **继续调整**：默认以当前结果作为下一步输入；切换为“原始图像”即可独立比较效果。
6. **保存图像**：导出当前结果，默认使用新的 `_处理结果` 文件名。

预览支持滚轮缩放、拖动平移、双击适应窗口，也可在上方选择 100% 等显示比例。“对照原图”控制原图面板显示。历史记录最多保留 20 个状态，受 128 MB 预算限制；大图会保留更少步骤。原图另外保留，可随时恢复。

退出或打开其他图像前，软件会提醒保存未导出的结果。图像处理在后台线程执行，处理失败时保留已有结果并显示原因。

| 快捷键 | 操作 |
| --- | --- |
| `Ctrl+O` | 打开图像 |
| `Ctrl+S` | 保存图像 |
| `Ctrl+Z` | 撤销 |
| `Ctrl+Shift+Z` | 重做 |
| `Ctrl+Enter` | 应用当前处理 |
| `F1` | 快速使用指南 |
| `Ctrl+Q` | 退出 |

## 28 个处理工具

| 分类 | 功能 |
| --- | --- |
| 基础调整 | 二值化、灰度化、归一化、直方图均衡 / CLAHE |
| 几何变换 | 调整大小、翻转、旋转、裁剪、透视校正 |
| 滤波去噪 | 高斯滤波、均值滤波、维纳去模糊、双边滤波 |
| 形态学 | 腐蚀、膨胀、开运算、闭运算、梯度、顶帽 |
| 色彩与通道 | 自动白平衡、色彩空间观察、通道分离、通道合成 |
| 数据增强 | 随机裁剪、随机旋转、随机翻转、亮度 / 对比度扰动、Mixup |

- 透视校正的四个点按**左上、右上、右下、左下**排列，坐标以当前“处理输入”为准。
- 通道合成可使用最近分离的通道，也可按 B、G、R 顺序加载三张同尺寸图像。
- Mixup 必须加载第二张图像；该图会自动缩放至输入尺寸。
- HSV / YUV / Lab 观察输出三个灰度通道的并排拼图，保存的也是拼图，不将这些原始数据误显示成 RGB 彩色图。
- 维纳去模糊以灰度图处理，使用模拟高斯 PSF，不能保证恢复任意真实模糊。

## 从源码运行

需要 Python 3.10 或更高版本及桌面环境。Windows 已验证 Python 3.13；自动检查覆盖 Python 3.11 / 3.13。macOS、Linux 可从源码运行，但当前只提供 Windows 二进制发行版。

```bash
git clone https://github.com/LotusXanderYang/pyqt-image-toolbox.git
cd pyqt-image-toolbox
python -m venv .venv
```

Windows 无需激活环境也可直接运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

可指定启动图像或使用内置示例：

```bash
python app.py "你的图像.png"
python app.py --demo
```

## 构建 Windows EXE

在 Windows x64 + Python 3.13 环境中执行：

```powershell
python -m pip install -r requirements-lock.txt
python scripts/build_windows.py
```

构建脚本生成单文件、无控制台窗口的 EXE，自动运行打包自检，然后输出 ZIP 和 SHA-256 校验文件到 `dist/`。自检失败会终止构建。`requirements-build.txt` 用于更新构建环境；复现 2.0.0 的依赖使用 `requirements-lock.txt`。

自定义输出路径：

```powershell
python scripts/build_windows.py --output dist --work build
```

GitHub Actions 会在提交和 Pull Request 时验证功能与 GUI；推送版本标签或手动运行工作流时，额外生成 Windows 构建产物。

## 验证

```bash
python -m unittest discover -s tests -v
python app.py --self-test build/source-smoke
```

`--self-test` 离线检查所有 28 个操作、参数页面、后台线程、连续 / 原图输入、撤销重做、失败恢复、中文路径导出、搜索、缩放和界面布局，生成 `report.json` 与真实界面截图后自动退出。构建脚本对打包后的 EXE 执行相同验证，以发现资源或 Qt 插件遗漏。

## 限制

- 当前工作格式为 8 位 RGB；透明通道、16 位等高位深数据与 EXIF 元数据不保留。
- 支持常见 PNG、JPEG、BMP、TIFF、WebP；具体可解码格式取决于 OpenCV。
- 限制输入文件不超过 512 MB，图像 / 输出不超过 4000 万像素；大图仍会占用较多内存。
- 随机增强每次会重新采样。历史记录保存已生成的结果，重做不会重新采样。
- 程序不上传图像、不进行联网处理；只有主动点击 GitHub 链接时才打开网站。

## 项目结构

```text
app.py                       应用入口
toolbox/gui.py               桌面界面与后台处理流程
toolbox/processing.py        图像处理与参数定义
toolbox/image_io.py          中文路径读写、原子保存
toolbox/history.py           有内存预算的撤销 / 重做
toolbox/theme.py             统一界面样式
toolbox/self_test.py         源码与 EXE 的离线自检
assets/                      图标、示例、开源字体与界面截图
tests/                       回归测试
scripts/build_windows.py     EXE / ZIP 构建
.github/workflows/windows.yml 自动验证与构建
```

## 开源与第三方许可

项目自身源码保留 [MIT License](LICENSE)。发布的完整 Windows 软件包含 PyQt5 开源版，因此按 **GPL-3.0-or-later** 提供，全文见 [COPYING](COPYING)。第三方组件和素材保留各自许可；详见 [第三方声明](THIRD_PARTY_NOTICES.md) 与 [对应源码说明](DEPENDENCY_SOURCES.md)。软件菜单“帮助 → 许可证与对应源码”也可离线查看这些说明。

欢迎提交 Issue 和 Pull Request。涉及图像处理的修改请运行回归测试；涉及界面、资源或打包的修改请同时运行 GUI 自检与 Windows 构建。
