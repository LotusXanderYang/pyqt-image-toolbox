"""Build an offline single-file Windows executable and distributable ZIP."""
import argparse
import hashlib
import importlib.metadata
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from toolbox import __version__


def collect_licenses(destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("PyQt5", "PyQt5-Qt5", "PyQt5-sip", "numpy", "opencv-python", "scikit-image", "scipy", "pillow", "networkx", "imageio", "tifffile", "lazy-loader", "packaging"):
        distribution = importlib.metadata.distribution(name)
        for entry in distribution.files or []:
            basename = Path(str(entry)).name
            if "LICENSE" in basename.upper() or "COPYING" in basename.upper():
                origin = Path(distribution.locate_file(entry))
                if origin.is_file():
                    target = destination / name / str(entry).replace("../", "").replace("..\\", "")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(origin, target)
    for name in ("LICENSE.txt", "LICENSE_PYTHON.txt"):
        source = Path(sys.base_prefix) / name
        if source.is_file():
            shutil.copyfile(source, destination / f"Python-{name}")


def make_icon(destination):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QImage, QPainter
    from PyQt5.QtSvg import QSvgRenderer
    from PyQt5.QtWidgets import QApplication
    from PIL import Image
    app = QApplication.instance() or QApplication([])
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    QSvgRenderer(str(ROOT / "assets/icon.svg")).render(painter)
    painter.end()
    temporary = destination.with_suffix(".png")
    image.save(str(temporary))
    with Image.open(temporary) as asset:
        asset.save(destination, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    parser.add_argument("--work", type=Path, default=ROOT / "build")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Windows executable must be built on Windows.")
    output, work = args.output.resolve(), args.work.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    executable_name = f"ImageToolbox-{__version__}-Windows-x64"
    licenses = work / "third-party-licenses"
    collect_licenses(licenses)
    qt_app = make_icon(work / "ImageToolbox.ico")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--noupx",
               "--name", executable_name, "--distpath", str(output), "--workpath", str(work / "pyinstaller"),
               "--specpath", str(work), "--icon", str(work / "ImageToolbox.ico"),
               "--add-data", f"{ROOT / 'assets'}{os.pathsep}assets",
               "--add-data", f"{licenses}{os.pathsep}third-party-licenses",
               "--hidden-import", "skimage.restoration.deconvolution", "--collect-data", "skimage"]
    for name in ("LICENSE", "COPYING", "THIRD_PARTY_NOTICES.md", "DEPENDENCY_SOURCES.md"):
        command.extend(["--add-data", f"{ROOT / name}{os.pathsep}."])
    for name in ("tkinter", "matplotlib", "IPython", "notebook", "pandas", "PySide6", "PyQt6", "pytest"):
        command.extend(["--exclude-module", name])
    command.append(str(ROOT / "app.py"))
    subprocess.run(command, cwd=ROOT, check=True)
    executable = output / f"{executable_name}.exe"
    # Test the frozen binary, including Qt plugins, lazy imports, resources and exports.
    test_dir = work / "frozen-self-test"
    completed = subprocess.run([str(executable), "--self-test", str(test_dir)], cwd=work, timeout=180)
    if completed.returncode != 0:
        report = test_dir / "report.json"
        raise RuntimeError(report.read_text(encoding="utf-8") if report.exists() else "Frozen executable self-test failed.")
    archive = output / f"{executable_name}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        zipped.write(executable, executable.name)
        for name in ("QUICKSTART.txt", "LICENSE", "COPYING", "THIRD_PARTY_NOTICES.md", "DEPENDENCY_SOURCES.md", "requirements-lock.txt"):
            zipped.write(ROOT / name, name)
        for license_file in licenses.rglob("*"):
            if license_file.is_file():
                zipped.write(license_file, "third-party-licenses/" + license_file.relative_to(licenses).as_posix())
    hashes = output / "SHA256SUMS.txt"
    entries = []
    for path in (executable, archive):
        with path.open("rb") as stream:
            entries.append(f"{hashlib.file_digest(stream, 'sha256').hexdigest()}  {path.name}\n")
    hashes.write_text("".join(entries), encoding="utf-8")
    print(f"Built and verified {executable}\nPackaged {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
