"""
Pipeline processors - Nodes that import directly from imager-pipeline.
These wrap the actual processing functions from the imager-pipeline project.
"""

import base64
import sys
import os
import io
import uuid
import cv2
import numpy as np
from .base_processor import ImageProcessor

# Add imager-pipeline to Python path so we can import from it
IMAGER_PIPELINE_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "imager-pipeline")
)
if IMAGER_PIPELINE_DIR not in sys.path:
    sys.path.insert(0, IMAGER_PIPELINE_DIR)

# Import from imager-pipeline
from wavelet_denoising import WaveletDenoiser, WaveletBackgroundRemover
from imagej_replicator import ImageJReplicator
from camera_calibration import CameraCalibrator, undistort_image
from complete_pipeline import (
    flat_field_correction,
    auto_threshold_detection,
    apply_threshold_separation,
    invert_image as pipeline_invert_image,
    normalize_to_max_value,
    apply_advanced_median_filter,
)
from tiff_json_to_dcm import image_to_dicom_bytes

MAX_16BIT = 65535
MAX_8BIT = 255


def _to_optional_int(value):
    """Convert values from UI to optional int (treat empty/-1/None as None)."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        value = stripped

    parsed = int(value)
    if parsed < 0:
        return None
    return parsed


# =============================================================================
# 1. Wavelet Denoise
# =============================================================================
class WaveletDenoiseProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Wavelet Denoise"
        self.description = (
            "Denoise image using 2D wavelet transform (from imager-pipeline)"
        )
        self.parameters = {
            "wavelet": {
                "type": "select",
                "options": ["db4", "db8", "sym4", "coif1", "bior4.4"],
                "default": "sym4",
                "description": "Wavelet type",
            },
            "level": {
                "type": "number",
                "default": 3,
                "min": 1,
                "max": 8,
                "description": "Decomposition level (0 = auto)",
            },
            "method": {
                "type": "select",
                "options": ["BayesShrink", "VisuShrink", "manual"],
                "default": "BayesShrink",
                "description": "Thresholding method",
            },
            "mode": {
                "type": "select",
                "options": ["soft", "hard"],
                "default": "soft",
                "description": "Thresholding mode",
            },
        }

    def process(self, image, **kwargs):
        wavelet = kwargs.get("wavelet", "sym4")
        level = int(kwargs.get("level", 3))
        method = kwargs.get("method", "BayesShrink")
        mode = kwargs.get("mode", "soft")

        # Convert to grayscale if needed for wavelet processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Use level=None for auto if level is 0
        actual_level = level if level > 0 else None

        denoiser = WaveletDenoiser(wavelet=wavelet, level=actual_level)
        denoised = denoiser.denoise_wavelet(gray, method=method, mode=mode)

        # Convert back to BGR for pipeline consistency
        if len(denoised.shape) == 2:
            denoised = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)

        return denoised


# =============================================================================
# 2. Flat Field Correction (FFC) - Multi-input: 3 images -> 1
# =============================================================================
class PipelineFlatFieldCorrectionProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "FFC (Pipeline)"
        self.description = "Flat-field correction from imager-pipeline: corrected = (raw - dark) / (flat - dark) * mean(flat - dark)"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["projection", "gain", "dark"]

    def process_multi(self, images_dict, **kwargs):
        """
        Process FFC with 3 inputs: projection (raw), gain (flat), dark.
        Uses the exact formula from imager-pipeline's complete_pipeline.py.
        """
        projection = images_dict.get("projection")
        gain = images_dict.get("gain")
        dark = images_dict.get("dark")

        if projection is None or gain is None or dark is None:
            raise ValueError(
                "FFC requires projection, gain, and dark images. Connect 3 Image Input nodes."
            )

        # Convert to grayscale if needed
        if len(projection.shape) == 3:
            projection = cv2.cvtColor(projection, cv2.COLOR_BGR2GRAY)
        if len(gain.shape) == 3:
            gain = cv2.cvtColor(gain, cv2.COLOR_BGR2GRAY)
        if len(dark.shape) == 3:
            dark = cv2.cvtColor(dark, cv2.COLOR_BGR2GRAY)

        # Use the imager-pipeline function directly
        corrected = flat_field_correction(projection, dark, gain)

        # Convert back to BGR for pipeline consistency
        if len(corrected.shape) == 2:
            corrected = cv2.cvtColor(corrected, cv2.COLOR_GRAY2BGR)

        return corrected

    def process(self, image, **kwargs):
        """Single input mode - just return the image"""
        return image


# =============================================================================
# 3. Enhance Contrast (ImageJ)
# =============================================================================
class ImageJEnhanceContrastProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Enhance Contrast (ImageJ)"
        self.description = "ImageJ-style contrast enhancement with histogram stretching and equalization"
        self.parameters = {
            "saturated_pixels": {
                "type": "number",
                "default": 0.35,
                "min": 0.0,
                "max": 100.0,
                "step": 0.05,
                "description": "Percentage of saturated pixels (ImageJ default: 0.35)",
            },
            "normalize": {
                "type": "boolean",
                "default": True,
                "description": "Apply histogram stretching (LUT normalization)",
            },
            "equalize": {
                "type": "boolean",
                "default": False,
                "description": "Apply histogram equalization",
            },
            "classic_equalization": {
                "type": "boolean",
                "default": False,
                "description": "Use classic HE instead of sqrt-weighted (ImageJ default)",
            },
        }

    def process(self, image, **kwargs):
        saturated_pixels = float(kwargs.get("saturated_pixels", 0.35))
        normalize = kwargs.get("normalize", True)
        equalize = kwargs.get("equalize", False)
        classic_equalization = kwargs.get("classic_equalization", False)

        # Convert to grayscale for ImageJ processing
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Ensure uint8 or uint16
        if gray.dtype == np.float32 or gray.dtype == np.float64:
            gray = (gray * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)

        result = ImageJReplicator.enhance_contrast(
            gray,
            saturated_pixels=saturated_pixels,
            equalize=equalize,
            normalize=normalize,
            classic_equalization=classic_equalization,
        )

        # Convert back to BGR
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 4. CLAHE (ImageJ)
# =============================================================================
class ImageJCLAHEProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "CLAHE (ImageJ)"
        self.description = (
            "ImageJ-style CLAHE (Contrast Limited Adaptive Histogram Equalization)"
        )
        self.parameters = {
            "blocksize": {
                "type": "number",
                "default": 127,
                "min": 3,
                "max": 511,
                "step": 2,
                "description": "Block size in pixels (must be odd, ImageJ default: 127)",
            },
            "histogram_bins": {
                "type": "number",
                "default": 256,
                "min": 2,
                "max": 65536,
                "description": "Number of histogram bins (default: 256)",
            },
            "max_slope": {
                "type": "number",
                "default": 3.0,
                "min": 0.1,
                "max": 10.0,
                "step": 0.1,
                "description": "Contrast limiting slope (1-2 for X-ray, 3 = ImageJ default)",
            },
            "fast": {
                "type": "boolean",
                "default": True,
                "description": "Use fast (OpenCV-based) mode",
            },
        }

    def process(self, image, **kwargs):
        blocksize = int(kwargs.get("blocksize", 127))
        histogram_bins = int(kwargs.get("histogram_bins", 256))
        max_slope = float(kwargs.get("max_slope", 3.0))
        fast = kwargs.get("fast", True)

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Ensure uint8 or uint16
        if gray.dtype == np.float32 or gray.dtype == np.float64:
            gray = (gray * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)

        result = ImageJReplicator.apply_clahe(
            gray,
            blocksize=blocksize,
            histogram_bins=histogram_bins,
            max_slope=max_slope,
            fast=fast,
            composite=True,
        )

        # Convert back to BGR
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 5. Median Filter (ImageJ - circular kernel)
# =============================================================================
class ImageJMedianFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Median Filter (ImageJ)"
        self.description = "ImageJ-style median filter with circular kernel (Process > Filters > Median)"
        self.parameters = {
            "radius": {
                "type": "number",
                "default": 5.0,
                "min": 0.5,
                "max": 50.0,
                "step": 0.5,
                "description": "Radius of circular kernel in pixels",
            }
        }

    def process(self, image, **kwargs):
        radius = float(kwargs.get("radius", 5.0))

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        result = ImageJReplicator.median_filter_imagej(gray, radius=radius)

        # Convert back to BGR
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 6. Hybrid Median Filter (ImageJ)
# =============================================================================
class ImageJHybridMedianFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Hybrid Median Filter (ImageJ)"
        self.description = (
            "ImageJ Hybrid 2D Median Filter - edge-preserving, uses Plus and X kernels"
        )
        self.parameters = {
            "kernel_size": {
                "type": "select",
                "options": [3, 5, 7],
                "default": 5,
                "description": "Kernel size (3x3, 5x5, or 7x7)",
            },
            "repetitions": {
                "type": "number",
                "default": 1,
                "min": 1,
                "max": 10,
                "description": "Number of filter repetitions",
            },
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))
        repetitions = int(kwargs.get("repetitions", 1))

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        result = ImageJReplicator.hybrid_median_filter_2d(
            gray, kernel_size=kernel_size, repetitions=repetitions
        )

        # Convert back to BGR
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 7. Auto Threshold (from pipeline)
# =============================================================================
class AutoThresholdProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Auto Threshold"
        self.description = (
            "Auto threshold detection and background separation from imager-pipeline"
        )
        self.parameters = {
            "method": {
                "type": "select",
                "options": [
                    "auto",
                    "valley",
                    "otsu",
                    "knee",
                    "percentile_25",
                    "secondary_peak",
                ],
                "default": "auto",
                "description": "Threshold detection method",
            }
        }

    def process(self, image, **kwargs):
        method = kwargs.get("method", "auto")

        # Convert to grayscale float32 [0,1]
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if gray.dtype == np.uint8:
            gray_float = gray.astype(np.float32) / MAX_8BIT
        elif gray.dtype == np.uint16:
            gray_float = gray.astype(np.float32) / MAX_16BIT
        else:
            gray_float = gray.astype(np.float32)

        # Temporarily override CONFIG threshold method
        from complete_pipeline import CONFIG

        original_method = CONFIG.get("THRESHOLD_METHOD", "auto")
        CONFIG["THRESHOLD_METHOD"] = method

        try:
            threshold = auto_threshold_detection(gray_float)
            result = apply_threshold_separation(gray_float, threshold)
        finally:
            CONFIG["THRESHOLD_METHOD"] = original_method

        # Convert back to uint8 BGR
        result_uint8 = (result * MAX_8BIT).clip(0, MAX_8BIT).astype(np.uint8)
        result_bgr = cv2.cvtColor(result_uint8, cv2.COLOR_GRAY2BGR)

        return result_bgr


# =============================================================================
# 8. Invert Image (pipeline version)
# =============================================================================
class PipelineInvertProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Invert (Pipeline)"
        self.description = (
            "Invert image colors using the imager-pipeline method (supports float32)"
        )
        self.parameters = {}

    def process(self, image, **kwargs):

        # Convert to float32 for pipeline invert
        if image.dtype == np.uint8:
            image_float = image.astype(np.float32) / MAX_8BIT
            inverted = pipeline_invert_image(image_float)
            return (inverted * MAX_8BIT).clip(0, MAX_8BIT).astype(np.uint8)
        elif image.dtype == np.uint16:
            image_float = image.astype(np.float32) / MAX_16BIT
            inverted = pipeline_invert_image(image_float)
            return (inverted * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
        else:
            inverted = pipeline_invert_image(image)
            return (inverted * MAX_8BIT).clip(0, MAX_8BIT).astype(np.uint8)


# =============================================================================
# 9. Normalize (ImageJ histogram stretch)
# =============================================================================
class ImageJNormalizeProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Normalize (ImageJ)"
        self.description = "Stretch histogram to full dynamic range using ImageJ method"
        self.parameters = {
            "saturated_pixels": {
                "type": "number",
                "default": 0.35,
                "min": 0.0,
                "max": 100.0,
                "step": 0.05,
                "description": "Percentage of saturated pixels",
            }
        }

    def process(self, image, **kwargs):
        saturated_pixels = float(kwargs.get("saturated_pixels", 0.35))

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Ensure uint16 for ImageJ processing
        if gray.dtype == np.float32 or gray.dtype == np.float64:
            gray = (gray * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)
        elif gray.dtype == np.uint8:
            gray = gray.astype(np.uint16) * 257  # Scale 0-255 to 0-65535

        result = normalize_to_max_value(gray, saturated_pixels=saturated_pixels)

        # Convert back to BGR
        if result.dtype == np.uint16:
            result = (result.astype(np.float32) / MAX_16BIT * MAX_8BIT).astype(np.uint8)

        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 10. Wavelet Background Removal
# =============================================================================
class WaveletBackgroundRemovalProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Wavelet Background Removal"
        self.description = (
            "Remove background using wavelet-based approach (from imager-pipeline)"
        )
        self.parameters = {
            "wavelet": {
                "type": "select",
                "options": ["db4", "db8", "sym4", "coif1"],
                "default": "db4",
                "description": "Wavelet type",
            },
            "level": {
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 5,
                "description": "Decomposition level for background removal",
            },
        }

    def process(self, image, **kwargs):
        wavelet = kwargs.get("wavelet", "db4")
        level = int(kwargs.get("level", 2))

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        bg_remover = WaveletBackgroundRemover(wavelet=wavelet)
        result, mask = bg_remover.remove_background_wavelet(gray, level=level)

        # Convert back to BGR
        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 11. Advanced Median Filter (multiple types from pipeline)
# =============================================================================
class AdvancedMedianFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Advanced Median Filter"
        self.description = (
            "Advanced median filtering with multiple methods from imager-pipeline"
        )
        self.parameters = {
            "filter_type": {
                "type": "select",
                "options": [
                    "hybrid_imagej",
                    "circular_imagej",
                    "standard",
                    "bilateral",
                    "adaptive",
                    "morphological",
                ],
                "default": "hybrid_imagej",
                "description": "Filter type (hybrid_imagej is best for X-ray images)",
            },
            "radius": {
                "type": "number",
                "default": 2,
                "min": 1,
                "max": 15,
                "description": "Filter radius",
            },
        }

    def process(self, image, **kwargs):
        filter_type = kwargs.get("filter_type", "hybrid_imagej")
        radius = int(kwargs.get("radius", 2))

        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Ensure uint16 for pipeline processing
        if gray.dtype == np.float32 or gray.dtype == np.float64:
            gray = (gray * MAX_16BIT).clip(0, MAX_16BIT).astype(np.uint16)

        result = apply_advanced_median_filter(
            gray, filter_type=filter_type, radius=radius
        )

        # Convert back to uint8 BGR
        if result.dtype == np.uint16:
            result = (result.astype(np.float32) / MAX_16BIT * MAX_8BIT).astype(np.uint8)

        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)

        return result


# =============================================================================
# 12. Camera Calibration (image -> npz artifact)
# =============================================================================
class CameraCalibrationProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Camera Calibration"
        self.description = (
            "Generate camera calibration .npz from circle-grid calibration image"
        )
        self.parameters = {
            "auto_detect_params": {
                "type": "boolean",
                "default": True,
                "description": "Auto-detect grid size and circle diameter from image",
            },
            "pattern_cols": {
                "type": "number",
                "default": 27,
                "min": 1,
                "max": 200,
                "description": "Circle-grid columns (if auto-detect is off)",
            },
            "pattern_rows": {
                "type": "number",
                "default": 18,
                "min": 1,
                "max": 200,
                "description": "Circle-grid rows (if auto-detect is off)",
            },
            "circle_diameter": {
                "type": "number",
                "default": 40.0,
                "min": 0.0001,
                "max": 100000.0,
                "step": 0.1,
                "description": "Pixel circle diameter (if auto-detect is off)",
            },
            "roi_x": {
                "type": "number",
                "default": -1,
                "min": -1,
                "max": 100000,
                "description": "Custom ROI X (-1 = auto)",
            },
            "roi_y": {
                "type": "number",
                "default": -1,
                "min": -1,
                "max": 100000,
                "description": "Custom ROI Y (-1 = auto)",
            },
            "roi_w": {
                "type": "number",
                "default": -1,
                "min": -1,
                "max": 100000,
                "description": "Custom ROI width (-1 = auto)",
            },
            "roi_h": {
                "type": "number",
                "default": -1,
                "min": -1,
                "max": 100000,
                "description": "Custom ROI height (-1 = auto)",
            },
            "output_filename": {
                "type": "string",
                "default": "camera_calibration.npz",
                "description": "Output .npz filename",
            },
        }

    def process(self, image, **kwargs):
        auto_detect = kwargs.get("auto_detect_params", True)
        
        pattern_cols = None
        pattern_rows = None
        circle_diameter = None
        pattern_size = None

        if not auto_detect:
            pattern_cols = int(kwargs.get("pattern_cols", 27))
            pattern_rows = int(kwargs.get("pattern_rows", 18))
            circle_diameter = float(kwargs.get("circle_diameter", 40.0))
            pattern_size = (pattern_cols, pattern_rows)

        roi_x = _to_optional_int(kwargs.get("roi_x", -1))
        roi_y = _to_optional_int(kwargs.get("roi_y", -1))
        roi_w = _to_optional_int(kwargs.get("roi_w", -1))
        roi_h = _to_optional_int(kwargs.get("roi_h", -1))
        custom_roi = (
            (roi_x, roi_y, roi_w, roi_h)
            if None not in [roi_x, roi_y, roi_w, roi_h]
            else None
        )

        calibrator = CameraCalibrator(
            pattern_size=pattern_size,
            circle_diameter=circle_diameter,
        )

        try:
            calibration_data = calibrator.calibrate_from_image_in_memory(
                image, roi_crop=custom_roi
            )
        except Exception as e:
            raise ValueError(f"Calibration failed: {e}")

        if not calibration_data:
            raise ValueError("Camera calibration failed; could not generate artifact")

        # Serialize calibration dict to .npz bytes for artifact storage
        buf = io.BytesIO()
        np.savez_compressed(
            buf,
            mtx=calibration_data["mtx"],
            dist=calibration_data["dist"],
            newcameramtx=calibration_data["newcameramtx"],
            image_size=np.array(calibration_data["image_size"]),
            pattern_size=np.array(calibration_data["pattern_size"]),
            circle_diameter=np.array(calibration_data["circle_diameter"]),
        )
        npz_bytes = buf.getvalue()

        output_filename = kwargs.get("output_filename", "camera_calibration.npz")

        return {
            "artifact": npz_bytes,
            "output_ext": ".npz",
            "output_type": "calibration",
            "mime_type": "application/octet-stream",
            "output_name": output_filename,
            "_calibration_data": calibration_data,  # raw dict for downstream nodes
        }


# =============================================================================
# 13. Apply Camera Calibration (image + npz -> image)
# =============================================================================
class ApplyCameraCalibrationProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Apply Camera Calibration"
        self.description = "Undistort image using an uploaded calibration .npz file"
        self.parameters = {
            "calibration_file": {
                "type": "file",
                "file_filter": ".npz",
                "description": "Upload camera calibration .npz file",
            },
            "alpha": {
                "type": "number",
                "default": 0.0,
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "description": "Undistort alpha (0=crop strongest, 1=keep all pixels)",
            },
            "crop_to_roi": {
                "type": "boolean",
                "default": True,
                "description": "Crop output to valid ROI",
            },
        }

    def process(self, image, **kwargs):
        calibration_file_b64 = kwargs.get("calibration_file")
        if not calibration_file_b64:
            raise ValueError(
                "Apply Camera Calibration requires an uploaded .npz calibration file."
            )

        try:
            # The frontend sends a data URL like "data:application/octet-stream;base64,..."
            header, encoded = calibration_file_b64.split(",", 1)
            decoded_bytes = base64.b64decode(encoded)
            
            with io.BytesIO(decoded_bytes) as buf:
                calibration_data = np.load(buf)
        except (ValueError, TypeError, base64.binascii.Error) as e:
            raise ValueError(f"Failed to decode or load calibration file: {e}")

        alpha = float(kwargs.get("alpha", 0.0))
        crop_to_roi = bool(kwargs.get("crop_to_roi", True))
        
        result = undistort_image(
            image,
            calibration_data,
            alpha=alpha,
            crop_to_roi=crop_to_roi,
        )

        if len(result.shape) == 2:
            result = cv2.cvtColor(result, cv2.COLOR_GRAY2BGR)
        return result


# =============================================================================
# 14. TIFF JSON to DICOM (terminal artifact)
# =============================================================================
class TiffJsonToDICOMProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "TIFF JSON to DICOM"
        self.description = (
            "Convert the incoming image into a DICOM file using uploaded JSON metadata"
        )
        self.parameters = {}
        self.output_count = 0

    def process(self, image, **kwargs):
        json_metadata = kwargs.get("json_metadata")
        json_filename = kwargs.get("json_filename", "metadata.json")

        if not json_metadata:
            raise ValueError(
                "TIFF JSON to DICOM requires an uploaded JSON metadata file"
            )

        output_stem = os.path.splitext(os.path.basename(json_filename))[0] or "output"
        output_name = f"{output_stem}.dcm"
        dicom_bytes = image_to_dicom_bytes(
            image, json_metadata, output_name=output_name
        )

        return {
            "artifact": dicom_bytes,
            "output_ext": ".dcm",
            "output_type": "dicom",
            "mime_type": "application/dicom",
            "output_name": output_name,
        }
