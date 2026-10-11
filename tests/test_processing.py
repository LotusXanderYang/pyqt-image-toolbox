import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from toolbox.history import History
from toolbox.image_io import read_image, save_image
from toolbox.processing import OPERATIONS, process


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.image = np.random.default_rng(12).integers(0, 256, (80, 96, 3), dtype=np.uint8)

    def test_every_operation_and_input_immutability(self):
        original = self.image.copy()
        for operation in OPERATIONS:
            with self.subTest(operation=operation.key):
                parameters = {}
                if operation.key == "crop":
                    parameters = {"width": 30, "height": 40}
                elif operation.key == "perspective":
                    parameters = {"points": "0,0 95,0 95,79 0,79"}
                result = process(operation.key, self.image, parameters, second=self.image, channels=cv2.split(self.image), rng=np.random.default_rng(1))
                self.assertEqual(result.image.dtype, np.uint8)
                self.assertEqual(result.image.shape[2], 3)
                self.assertTrue(result.image.flags.c_contiguous)
                np.testing.assert_array_equal(self.image, original)

    def test_invalid_inputs_leave_original_intact(self):
        cases = (
            ("crop", {"x": 96, "width": 1, "height": 1}),
            ("crop", {"width": 97, "height": 1}),
            ("normalize", {"minimum": 200, "maximum": 100}),
            ("gaussian", {"kernel": 4}),
            ("resize", {"width": 0}),
            ("resize", {"width": 8192, "height": 8192, "keep_ratio": False}),
            ("perspective", {"points": "0,0 10,10 20,20 30,30"}),
            ("perspective", {"points": "0,0 95,79 95,0 0,79"}),
            ("perspective", {"points": "nan,0 1,0 1,1 0,1"}),
            ("perspective", {"points": "bad"}),
            ("merge", {}), ("mixup", {}),
        )
        for key, parameters in cases:
            with self.subTest(key=key, parameters=parameters):
                with self.assertRaises(ValueError):
                    process(key, self.image, parameters)

    def test_white_balance_handles_black_and_missing_channels(self):
        for image in (np.zeros((10, 10, 3), np.uint8), np.tile(np.uint8([0, 30, 200]), (10, 10, 1))):
            with np.errstate(divide="raise", invalid="raise"):
                result = process("white_balance", image).image
            self.assertTrue(np.isfinite(result).all())

    def test_one_pixel_random_crop_and_extreme_aspect_resize(self):
        one = np.ones((1, 1, 3), np.uint8)
        self.assertEqual(process("random_crop", one, {"ratio": .1}).image.shape, (1, 1, 3))
        wide = np.ones((1, 8192, 3), np.uint8)
        self.assertEqual(process("resize", wide, {"width": 1, "height": 1}).image.shape, (1, 1, 3))

    def test_color_space_mosaic_is_not_false_color(self):
        result = process("color_space", self.image).image
        self.assertEqual(result.shape, (80, 288, 3))
        np.testing.assert_array_equal(result[:, :, 0], result[:, :, 1])

    def test_split_merge_round_trip(self):
        split = process("split", self.image)
        merged = process("merge", split.image, channels=split.channels).image
        np.testing.assert_array_equal(merged, self.image)
        with self.assertRaises(ValueError):
            process("merge", self.image, channels=(np.zeros((1, 1)),) * 3)

    def test_tone_zero_is_identity_and_flip_probability(self):
        np.testing.assert_array_equal(process("random_tone", self.image, {"brightness": 0, "contrast": 0}).image, self.image)
        np.testing.assert_array_equal(process("random_flip", self.image, {"probability": 0}).image, self.image)
        np.testing.assert_array_equal(process("random_flip", self.image, {"probability": 1}).image, cv2.flip(self.image, 1))

    def test_png_unicode_export_and_read_failures(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "中文 图片.png"
            save_image(path, self.image)
            np.testing.assert_array_equal(read_image(path), self.image)
            with self.assertRaises(ValueError):
                save_image(Path(folder) / "invalid.txt", self.image)
            with self.assertRaises(ValueError):
                read_image(Path(folder) / "不存在.png")
            with self.assertRaises(OSError):
                save_image(Path(folder) / "missing" / "output.png", self.image)
            self.assertFalse(list(Path(folder).glob(".toolbox-*.tmp")))

    def test_rotation_expansion_preserves_dimensions(self):
        self.assertEqual(process("rotate", self.image, {"angle": 90, "expand": True}).image.shape, (96, 80, 3))


class HistoryTests(unittest.TestCase):
    def test_branching_and_stable_revision(self):
        history = History()
        image = np.zeros((2, 2, 3), np.uint8)
        first = history.reset(image)
        second = history.push(image + 1, "second")
        self.assertEqual(history.undo().revision, first.revision)
        self.assertEqual(history.redo().revision, second.revision)
        history.undo()
        third = history.push(image + 2, "third")
        self.assertGreater(third.revision, second.revision)
        self.assertFalse(history.can_redo)
        image[:] = 255
        self.assertEqual(history.current.image[0, 0, 0], 2)

    def test_history_memory_budget(self):
        history = History(budget=100, limit=3)
        for i in range(10):
            history.push(np.full((4, 4, 3), i, np.uint8), str(i))
        self.assertLessEqual(sum(s.image.nbytes for s in history.items), 100)
        self.assertEqual(history.current.image[0, 0, 0], 9)
        self.assertTrue(history.can_undo)


if __name__ == "__main__":
    unittest.main()
