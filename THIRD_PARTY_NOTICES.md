# 第三方组件与素材

项目自身源码保留 [MIT 许可证](LICENSE)。Windows 软件包含 PyQt5 开源版，因此**完整软件的组合发行采用 GPL-3.0-or-later**，许可证全文见 [COPYING](COPYING)。这不撤销先前已发布源码的 MIT 授权。PyQt5 的授权方式见 [Riverbank 官方说明](https://www.riverbankcomputing.com/commercial/license-faq)。

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| Python | 运行时 | PSF 与其所含许可 |
| PyQt5 | GUI 绑定 | GPL-3.0 |
| Qt 5 | GUI 运行库 | LGPL-3.0 / GPL，详见其组件许可 |
| PyQt5-sip | 绑定运行时 | BSD-2-Clause |
| OpenCV | 图像处理 | Apache-2.0；wheel 所含组件另有许可 |
| NumPy、SciPy、scikit-image | 数值计算与复原 | BSD-3-Clause，含各包随附许可 |
| Pillow | 图像依赖、构建图标 | MIT-CMU |
| NetworkX、imageio、tifffile | scikit-image 依赖 | 各包随附 BSD 许可 |
| lazy-loader | 延迟加载 | BSD-3-Clause |
| packaging | 版本处理 | Apache-2.0 / BSD-2-Clause |

构建脚本从实际安装的依赖中收集许可证文件，随软件内嵌并附于 ZIP 的 `third-party-licenses/`。准确版本见 `requirements-lock.txt`。对应源码入口与构建方式见 [DEPENDENCY_SOURCES.md](DEPENDENCY_SOURCES.md)。

## 示例照片

`assets/demo.png` 来自 scikit-image 随附的 astronaut 数据：宇航员 Eileen Collins 的 NASA 照片，属于公有领域。来源与许可说明见 [scikit-image 数据文档](https://scikit-image.org/docs/stable/api/skimage.data.html#skimage.data.astronaut)。照片仅用作离线图像处理示例，NASA 不为本项目背书。

## 离线界面字体

`assets/fonts/` 包含昭源黑体 Chiron Hei HK Text 2.609 的 Regular 和 SemiBold 原始字体文件。项目作者 Tamcy，基于 Adobe Source Han Sans，采用 SIL Open Font License 1.1。未修改字体，许可证全文随附于 `assets/fonts/OFL.txt`。来源：[官方仓库](https://github.com/chiron-fonts/chiron-hei-hk/tree/v2.609)。

## 应用图标

`assets/icon.svg` 使用 [Lucide 的 image 图标](https://lucide.dev/icons/image)，仅设置单色描边。Lucide 采用 ISC 许可证：

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other copyright (c) for Lucide are held by Lucide Contributors 2022.

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
