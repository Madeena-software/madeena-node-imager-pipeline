"""Tests for image processors — verifies each processor loads, processes, and
returns a valid NumPy image array."""

import os
import sys

import cv2
import numpy as np
import pytest

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.processors.base_processor import ImageProcessor
from app.processors.basic_processors import (
    AddProcessor,
    BlurProcessor,
    BrightnessProcessor,
    CropProcessor,
    DilateProcessor,
    EdgeDetectionProcessor,
    ErodeProcessor,
    FlipProcessor,
    GammaProcessor,
    GaussianBlurProcessor,
    GrayscaleProcessor,
    HistogramEqualizationProcessor,
    InvertProcessor,
    MaximumFilterProcessor,
    MeanFilterProcessor,
    MedianFilterProcessor,
    MinimumFilterProcessor,
    ResizeProcessor,
    RotateProcessor,
    SepiaProcessor,
    SharpenProcessor,
    SubtractProcessor,
    ThresholdProcessor,
    TopHatProcessor,
    UnsharpMaskProcessor,
    VarianceFilterProcessor,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_image_path(tmp_path):
    """Generate a small colour test image and return its path."""
    img = np.random.randint(0, 256, (120, 160, 3), dtype=np.uint8)
    path = str(tmp_path / "test.png")
    cv2.imwrite(path, img)
    return path


@pytest.fixture()
def grayscale_image_path(tmp_path):
    """Generate a small grayscale test image and return its path."""
    img = np.random.randint(0, 256, (120, 160), dtype=np.uint8)
    path = str(tmp_path / "gray.png")
    cv2.imwrite(path, img)
    return path


def _assert_valid_image(result):
    """Assert that *result* is a valid OpenCV image."""
    assert isinstance(result, np.ndarray), "Processor must return a NumPy array"
    assert result.ndim in (2, 3), "Image must be 2D (gray) or 3D (colour)"
    assert result.size > 0, "Image must not be empty"


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class TestImageProcessor:
    def test_load_image(self, test_image_path):
        proc = ImageProcessor()
        img = proc.load_image(test_image_path)
        _assert_valid_image(img)

    def test_load_missing_raises(self):
        proc = ImageProcessor()
        with pytest.raises(FileNotFoundError):
            proc.load_image("/nonexistent/path.png")

    def test_process_not_implemented(self, test_image_path):
        proc = ImageProcessor()
        with pytest.raises(NotImplementedError):
            proc.process(test_image_path)

    def test_save_image(self, test_image_path, tmp_path):
        proc = ImageProcessor()
        img = proc.load_image(test_image_path)
        out = str(tmp_path / "saved.png")
        proc.save_image(img, out)
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# Single-input processors
# ---------------------------------------------------------------------------


class TestResizeProcessor:
    def test_resize_default(self, test_image_path):
        result = ResizeProcessor().process(test_image_path)
        _assert_valid_image(result)

    def test_resize_custom(self, test_image_path):
        result = ResizeProcessor().process(
            test_image_path, width=200, height=100, maintain_aspect=False
        )
        assert result.shape[:2] == (100, 200)

    def test_resize_maintain_aspect(self, test_image_path):
        result = ResizeProcessor().process(
            test_image_path, width=200, height=200, maintain_aspect=True
        )
        _assert_valid_image(result)
        h, w = result.shape[:2]
        assert h <= 200 and w <= 200


class TestBlurProcessor:
    def test_blur_default(self, test_image_path):
        result = BlurProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestBrightnessProcessor:
    def test_brightness_increase(self, test_image_path):
        result = BrightnessProcessor().process(test_image_path, factor=1.5)
        _assert_valid_image(result)

    def test_brightness_decrease(self, test_image_path):
        result = BrightnessProcessor().process(test_image_path, factor=0.5)
        _assert_valid_image(result)


class TestGrayscaleProcessor:
    def test_grayscale(self, test_image_path):
        result = GrayscaleProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestSepiaProcessor:
    def test_sepia(self, test_image_path):
        result = SepiaProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestInvertProcessor:
    def test_invert(self, test_image_path):
        result = InvertProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestFlipProcessor:
    def test_flip_horizontal(self, test_image_path):
        result = FlipProcessor().process(test_image_path, direction="horizontal")
        _assert_valid_image(result)

    def test_flip_vertical(self, test_image_path):
        result = FlipProcessor().process(test_image_path, direction="vertical")
        _assert_valid_image(result)


class TestRotateProcessor:
    def test_rotate_90(self, test_image_path):
        result = RotateProcessor().process(test_image_path, angle=90)
        _assert_valid_image(result)


class TestCropProcessor:
    def test_crop(self, test_image_path):
        result = CropProcessor().process(
            test_image_path, x=10, y=10, width=50, height=50
        )
        _assert_valid_image(result)
        assert result.shape[:2] == (50, 50)

    def test_crop_from_sides(self, test_image_path):
        result = CropProcessor().process(
            test_image_path,
            top=10,
            bottom=20,
            left=15,
            right=25,
        )
        _assert_valid_image(result)
        assert result.shape[:2] == (90, 120)


class TestSharpenProcessor:
    def test_sharpen(self, test_image_path):
        result = SharpenProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestEdgeDetectionProcessor:
    def test_edge_detection(self, test_image_path):
        result = EdgeDetectionProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestErodeProcessor:
    def test_erode(self, test_image_path):
        result = ErodeProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestDilateProcessor:
    def test_dilate(self, test_image_path):
        result = DilateProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestHistogramEqualizationProcessor:
    def test_histogram_eq(self, test_image_path):
        result = HistogramEqualizationProcessor().process(test_image_path)
        _assert_valid_image(result)


class TestThresholdProcessor:
    def test_threshold_binary(self, test_image_path):
        result = ThresholdProcessor().process(test_image_path, method="binary")
        _assert_valid_image(result)

    def test_threshold_otsu(self, test_image_path):
        result = ThresholdProcessor().process(test_image_path, method="otsu")
        _assert_valid_image(result)


class TestFilterProcessors:
    def test_median_filter(self, test_image_path):
        _assert_valid_image(MedianFilterProcessor().process(test_image_path))

    def test_mean_filter(self, test_image_path):
        _assert_valid_image(MeanFilterProcessor().process(test_image_path))

    def test_maximum_filter(self, test_image_path):
        _assert_valid_image(MaximumFilterProcessor().process(test_image_path))

    def test_minimum_filter(self, test_image_path):
        _assert_valid_image(MinimumFilterProcessor().process(test_image_path))

    def test_unsharp_mask(self, test_image_path):
        _assert_valid_image(UnsharpMaskProcessor().process(test_image_path))

    def test_variance_filter(self, test_image_path):
        _assert_valid_image(VarianceFilterProcessor().process(test_image_path))

    def test_top_hat(self, test_image_path):
        _assert_valid_image(TopHatProcessor().process(test_image_path))

    def test_gaussian_blur(self, test_image_path):
        _assert_valid_image(GaussianBlurProcessor().process(test_image_path))


class TestGammaProcessor:
    def test_gamma(self, test_image_path):
        result = GammaProcessor().process(test_image_path)
        _assert_valid_image(result)


# ---------------------------------------------------------------------------
# Multi-input processors (partial — we test process_multi)
# ---------------------------------------------------------------------------


class TestMultiInputProcessors:
    @pytest.fixture()
    def two_images(self, tmp_path):
        """Return a dict with two same-size images keyed as expected by math processors."""
        a = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        b = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        return {"image1": a, "image2": b}

    def test_add(self, two_images):
        proc = AddProcessor()
        result = proc.process_multi(two_images)
        _assert_valid_image(result)

    def test_subtract(self, two_images):
        proc = SubtractProcessor()
        result = proc.process_multi(two_images)
        _assert_valid_image(result)
