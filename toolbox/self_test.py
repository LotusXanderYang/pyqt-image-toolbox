"""Offline frozen-app smoke test. Only runs with explicit --self-test."""
import json
import traceback

import cv2
import numpy as np
from PyQt5.QtCore import QEventLoop, QTimer
from PyQt5.QtWidgets import QFileDialog

from . import __version__
from .image_io import read_image, save_image
from .processing import OPERATIONS, process


def run_self_test(app, window, output):
    report = {"version": __version__, "passed": False, "checks": []}
    try:
        app.processEvents()
        assert not window.apply_button.isEnabled()
        assert not window.save_button.isEnabled()
        window.grab().save(str(output / "empty.png"))
        window.load_demo()
        assert window.current_image is not None, "Bundled example missing"
        original = window.current_image.copy()
        from PyQt5.QtGui import QFontMetrics
        assert QFontMetrics(app.font()).inFont("图"), "Bundled Chinese font missing"
        report["checks"].append("bundled example and empty-state controls")
        sample = cv2.resize(original, (96, 80))
        channels = cv2.split(sample)
        for op in OPERATIONS:
            params = {}
            if op.key == "perspective":
                params = {"points": "0,0 95,0 95,79 0,79", "width": 96, "height": 80}
            elif op.key == "crop":
                params = {"width": 40, "height": 30}
            result = process(op.key, sample, params, second=sample, channels=channels, rng=np.random.default_rng(42))
            assert result.image.size and result.image.dtype == np.uint8, op.key
            window.select_operation(op.key)
            assert window.selected_key == op.key
            window.get_parameters()
        report["checks"].append(f"all {len(OPERATIONS)} image operations and parameter pages")

        def apply_and_wait(key):
            window.select_operation(key)
            window.apply_current_function()
            assert window.busy
            assert not window.save_button.isEnabled()
            loop = QEventLoop()
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)
            window.worker.finished.connect(loop.quit)
            timer.start(30000)
            loop.exec_()
            app.processEvents()
            assert not window.busy, "Worker timeout"
            assert window.apply_button.isEnabled()

        apply_and_wait("gray")
        gray = window.current_image.copy()
        assert np.array_equal(gray[:, :, 0], gray[:, :, 1])
        window.undo()
        assert np.array_equal(window.current_image, original)
        window.redo()
        assert np.array_equal(window.current_image, gray)
        apply_and_wait("flip")
        assert np.array_equal(window.current_image, cv2.flip(gray, 1))
        window.input_source.setCurrentIndex(1)
        apply_and_wait("flip")
        assert np.array_equal(window.current_image, cv2.flip(original, 1))
        window.undo()
        window.undo()
        report["checks"].append("Qt worker, continuous/original inputs, undo and redo")

        revision = window.history.current.revision
        apply_and_wait("mixup")
        assert window.history.current.revision == revision
        assert window.notice.property("error") is True
        assert window.save_button.isEnabled()
        report["checks"].append("failed operation preserves result and restores controls")

        # Exercise the actual GUI save action with a deterministic noninteractive path.
        saved_path = output / "中文路径_处理结果.png"
        original_dialog = QFileDialog.getSaveFileName
        try:
            QFileDialog.getSaveFileName = lambda *args, **kwargs: (str(saved_path), "PNG (*.png)")
            assert window.save_result()
        finally:
            QFileDialog.getSaveFileName = original_dialog
        assert np.array_equal(read_image(saved_path), window.current_image)
        assert not window.dirty
        report["checks"].append("GUI export and Unicode PNG round trip")

        window.input_source.setCurrentIndex(0)
        window.select_operation("equalize")
        window.show_notice("已应用灰度化 · 原始图像与当前结果并排对照")
        window.resize(1380, 860)
        app.processEvents()
        assert window.grab().save(str(output / "workbench.png"))
        window.resize(1000, 700)
        app.processEvents()
        assert window.grab().save(str(output / "compact.png"))
        window.search.setText("找不到的功能")
        assert window.tools.count() == 0 and not window.apply_button.isEnabled()
        window.search.clear()
        assert window.tools.count() == len(OPERATIONS)
        window.compare.setChecked(False)
        assert not window.original_preview.isVisible()
        window.compare.setChecked(True)
        window.zoom.setCurrentText("100%")
        assert abs(window.result_preview.view.transform().m11() - 1) < 1e-6
        report["checks"].append("responsive rendering, search, comparison and zoom")
        report["passed"] = True
    except Exception:
        report["error"] = traceback.format_exc()
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    window.saved_revision = window.history.current.revision if window.history.current else None
    app.exit(0 if report["passed"] else 1)
