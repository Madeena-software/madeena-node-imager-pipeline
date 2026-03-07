import cv2
import numpy as np
import os
from .base_processor import ImageProcessor


class ResizeProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Resize"
        self.description = "Resize image to specified dimensions"
        self.parameters = {
            "width": {
                "type": "number",
                "default": 800,
                "min": 1,
                "max": 5000,
                "description": "Target width in pixels",
            },
            "height": {
                "type": "number",
                "default": 600,
                "min": 1,
                "max": 5000,
                "description": "Target height in pixels",
            },
            "maintain_aspect": {
                "type": "boolean",
                "default": True,
                "description": "Maintain original aspect ratio",
            },
            "interpolation": {
                "type": "select",
                "options": ["INTER_LINEAR", "INTER_CUBIC", "INTER_NEAREST"],
                "default": "INTER_LINEAR",
                "description": "Interpolation method for resizing",
            },
        }

    def process(self, image, **kwargs):

        width = kwargs.get("width", 800)
        height = kwargs.get("height", 600)
        maintain_aspect = kwargs.get("maintain_aspect", True)
        interpolation = kwargs.get("interpolation", "INTER_LINEAR")

        # Map interpolation string to OpenCV constant
        interp_map = {
            "INTER_LINEAR": cv2.INTER_LINEAR,
            "INTER_CUBIC": cv2.INTER_CUBIC,
            "INTER_NEAREST": cv2.INTER_NEAREST,
        }
        interp_method = interp_map.get(interpolation, cv2.INTER_LINEAR)

        if maintain_aspect:
            # Calculate aspect ratio
            h, w = image.shape[:2]
            aspect = w / h

            if width / height > aspect:
                width = int(height * aspect)
            else:
                height = int(width / aspect)

        resized = cv2.resize(image, (width, height), interpolation=interp_method)
        return resized


class BlurProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Blur"
        self.description = "Apply Gaussian blur to image"
        self.parameters = {
            "kernel_size": {
                "type": "range",
                "default": 15,
                "min": 1,
                "max": 99,
                "step": 2,
                "description": "Blur kernel size (must be odd)",
            },
            "sigma_x": {
                "type": "number",
                "default": 0,
                "min": 0,
                "max": 10,
                "step": 0.1,
                "description": "Standard deviation in X direction",
            },
            "sigma_y": {
                "type": "number",
                "default": 0,
                "min": 0,
                "max": 10,
                "step": 0.1,
                "description": "Standard deviation in Y direction",
            },
        }

    def process(self, image, **kwargs):

        # Additional safety check
        if image is None or image.size == 0:
            raise ValueError(f"Invalid or empty image provided.")

        kernel_size = kwargs.get("kernel_size", 15)
        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        sigma_x = kwargs.get("sigma_x", 0)
        sigma_y = kwargs.get("sigma_y", 0)

        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma_x, sigma_y)
        return blurred


class BrightnessProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Brightness"
        self.description = "Adjust image brightness and contrast"
        self.parameters = {
            "brightness": {
                "type": "range",
                "default": 0,
                "min": -100,
                "max": 100,
                "description": "Brightness adjustment (-100 to 100)",
            },
            "contrast": {
                "type": "number",
                "default": 1.0,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "description": "Contrast multiplier (0.1 to 3.0)",
            },
        }

    def process(self, image, **kwargs):

        brightness = kwargs.get("brightness", 0)
        contrast = kwargs.get("contrast", 1.0)

        # Apply brightness and contrast
        adjusted = cv2.convertScaleAbs(image, alpha=contrast, beta=brightness)
        return adjusted


class EdgeDetectionProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Edge Detection"
        self.description = "Detect edges using Canny algorithm"
        self.parameters = {
            "low_threshold": {
                "type": "range",
                "default": 50,
                "min": 0,
                "max": 255,
                "description": "Low threshold for edge detection",
            },
            "high_threshold": {
                "type": "range",
                "default": 150,
                "min": 0,
                "max": 255,
                "description": "High threshold for edge detection",
            },
            "kernel_size": {
                "type": "select",
                "options": [3, 5, 7],
                "default": 3,
                "description": "Sobel kernel size",
            },
            "l2_gradient": {
                "type": "boolean",
                "default": False,
                "description": "Use L2 gradient for more accurate results",
            },
        }

    def process(self, image, **kwargs):

        low_threshold = kwargs.get("low_threshold", 50)
        high_threshold = kwargs.get("high_threshold", 150)
        kernel_size = kwargs.get("kernel_size", 3)
        l2_gradient = kwargs.get("l2_gradient", False)

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(
            gray,
            low_threshold,
            high_threshold,
            apertureSize=kernel_size,
            L2gradient=l2_gradient,
        )

        # Convert back to 3-channel for consistency
        edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        return edges_colored


class RotateProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Rotate"
        self.description = "Rotate image by specified angle"
        self.parameters = {
            "angle": {
                "type": "range",
                "default": 0,
                "min": -180,
                "max": 180,
                "step": 1,
                "description": "Rotation angle in degrees",
            },
            "scale": {
                "type": "number",
                "default": 1.0,
                "min": 0.1,
                "max": 3.0,
                "step": 0.1,
                "description": "Scale factor",
            },
            "keep_size": {
                "type": "boolean",
                "default": False,
                "description": "Keep original image size (may crop)",
            },
        }

    def process(self, image, **kwargs):
        angle = kwargs.get("angle", 0)
        scale = kwargs.get("scale", 1.0)
        keep_size = kwargs.get("keep_size", False)

        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        # Get rotation matrix
        matrix = cv2.getRotationMatrix2D(center, angle, scale)

        if not keep_size:
            # Calculate new image size to fit rotated image
            cos = np.abs(matrix[0, 0])
            sin = np.abs(matrix[0, 1])
            new_w = int((h * sin) + (w * cos))
            new_h = int((h * cos) + (w * sin))

            # Adjust translation
            matrix[0, 2] += (new_w / 2) - center[0]
            matrix[1, 2] += (new_h / 2) - center[1]

            rotated = cv2.warpAffine(image, matrix, (new_w, new_h))
        else:
            rotated = cv2.warpAffine(image, matrix, (w, h))

        return rotated


class FlipProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Flip"
        self.description = "Flip image horizontally or vertically"
        self.parameters = {
            "direction": {
                "type": "select",
                "options": ["horizontal", "vertical", "both"],
                "default": "horizontal",
                "description": "Flip direction",
            }
        }

    def process(self, image, **kwargs):
        direction = kwargs.get("direction", "horizontal")

        if direction == "horizontal":
            flipped = cv2.flip(image, 1)
        elif direction == "vertical":
            flipped = cv2.flip(image, 0)
        else:  # both
            flipped = cv2.flip(image, -1)

        return flipped


class CropProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Crop"
        self.description = "Crop image by removing pixels from each side"

        def env_int(name, default=0):
            try:
                return max(0, int(os.environ.get(name, default)))
            except (TypeError, ValueError):
                return max(0, int(default))

        crop_top_default = env_int("CROP_TOP", 0)
        crop_bottom_default = env_int("CROP_BOTTOM", 0)
        crop_left_default = env_int("CROP_LEFT", 0)
        crop_right_default = env_int("CROP_RIGHT", 0)

        self.parameters = {
            "top": {
                "type": "number",
                "default": crop_top_default,
                "min": 0,
                "max": 10000,
                "description": "Pixels to crop from top",
            },
            "bottom": {
                "type": "number",
                "default": crop_bottom_default,
                "min": 0,
                "max": 10000,
                "description": "Pixels to crop from bottom",
            },
            "left": {
                "type": "number",
                "default": crop_left_default,
                "min": 0,
                "max": 10000,
                "description": "Pixels to crop from left",
            },
            "right": {
                "type": "number",
                "default": crop_right_default,
                "min": 0,
                "max": 10000,
                "description": "Pixels to crop from right",
            },
        }

    def process(self, image, **kwargs):

        h, w = image.shape[:2]

        # Backward compatibility: old x/y/width/height format
        if any(key in kwargs for key in ("x", "y", "width", "height")):
            x = int(kwargs.get("x", 0))
            y = int(kwargs.get("y", 0))
            width = int(kwargs.get("width", 100))
            height = int(kwargs.get("height", 100))

            x = max(0, min(x, w - 1))
            y = max(0, min(y, h - 1))
            width = max(1, min(width, w - x))
            height = max(1, min(height, h - y))

            return image[y : y + height, x : x + width]

        top = max(0, int(kwargs.get("top", self.parameters["top"]["default"])))
        bottom = max(0, int(kwargs.get("bottom", self.parameters["bottom"]["default"])))
        left = max(0, int(kwargs.get("left", self.parameters["left"]["default"])))
        right = max(0, int(kwargs.get("right", self.parameters["right"]["default"])))

        x1 = min(left, w - 1)
        y1 = min(top, h - 1)
        x2 = max(x1 + 1, w - right)
        y2 = max(y1 + 1, h - bottom)

        cropped = image[y1:y2, x1:x2]
        return cropped


class GrayscaleProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Grayscale"
        self.description = "Convert image to grayscale"
        self.parameters = {}

    def process(self, image, **kwargs):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Convert back to 3-channel for consistency
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


class SepiaProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Sepia"
        self.description = "Apply sepia tone effect"
        self.parameters = {
            "intensity": {
                "type": "range",
                "default": 100,
                "min": 0,
                "max": 100,
                "description": "Sepia intensity (0-100%)",
            }
        }

    def process(self, image, **kwargs):
        intensity = kwargs.get("intensity", 100) / 100.0

        # Sepia transformation matrix
        sepia_matrix = np.array(
            [[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]]
        )

        sepia_image = cv2.transform(image, sepia_matrix)
        sepia_image = np.clip(sepia_image, 0, 255).astype(np.uint8)

        # Blend with original based on intensity
        result = cv2.addWeighted(image, 1 - intensity, sepia_image, intensity, 0)
        return result


class InvertProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Invert Colors"
        self.description = "Invert image colors (negative)"
        self.parameters = {}

    def process(self, image, **kwargs):
        inverted = cv2.bitwise_not(image)
        return inverted


class SharpenProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Sharpen"
        self.description = "Sharpen image details"
        self.parameters = {
            "strength": {
                "type": "range",
                "default": 1.0,
                "min": 0.0,
                "max": 3.0,
                "step": 0.1,
                "description": "Sharpening strength",
            }
        }

    def process(self, image, **kwargs):
        strength = kwargs.get("strength", 1.0)

        # Create sharpening kernel
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]]) * strength

        # Adjust center value
        kernel[1, 1] = 1 + (4 * strength)

        sharpened = cv2.filter2D(image, -1, kernel)
        return sharpened


class ErodeProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Erode"
        self.description = "Morphological erosion operation"
        self.parameters = {
            "kernel_size": {
                "type": "range",
                "default": 5,
                "min": 1,
                "max": 21,
                "step": 2,
                "description": "Kernel size (must be odd)",
            },
            "iterations": {
                "type": "number",
                "default": 1,
                "min": 1,
                "max": 10,
                "description": "Number of iterations",
            },
        }

    def process(self, image, **kwargs):
        kernel_size = kwargs.get("kernel_size", 5)
        iterations = kwargs.get("iterations", 1)

        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        eroded = cv2.erode(image, kernel, iterations=iterations)
        return eroded


class DilateProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Dilate"
        self.description = "Morphological dilation operation"
        self.parameters = {
            "kernel_size": {
                "type": "range",
                "default": 5,
                "min": 1,
                "max": 21,
                "step": 2,
                "description": "Kernel size (must be odd)",
            },
            "iterations": {
                "type": "number",
                "default": 1,
                "min": 1,
                "max": 10,
                "description": "Number of iterations",
            },
        }

    def process(self, image, **kwargs):
        kernel_size = kwargs.get("kernel_size", 5)
        iterations = kwargs.get("iterations", 1)

        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        dilated = cv2.dilate(image, kernel, iterations=iterations)
        return dilated


class HistogramEqualizationProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Histogram Equalization"
        self.description = "Enhance image contrast using histogram equalization"
        self.parameters = {
            "method": {
                "type": "select",
                "options": ["standard", "adaptive"],
                "default": "standard",
                "description": "Equalization method",
            },
            "clip_limit": {
                "type": "number",
                "default": 2.0,
                "min": 1.0,
                "max": 10.0,
                "step": 0.5,
                "description": "Clip limit for adaptive method",
            },
        }

    def process(self, image, **kwargs):
        method = kwargs.get("method", "standard")
        clip_limit = kwargs.get("clip_limit", 2.0)

        # Convert to YCrCb color space
        ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
        channels = list(cv2.split(ycrcb))

        if method == "standard":
            # Apply histogram equalization to Y channel
            channels[0] = cv2.equalizeHist(channels[0])
        else:  # adaptive
            # Apply CLAHE to Y channel
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            channels[0] = clahe.apply(channels[0])

        # Merge channels and convert back to BGR
        ycrcb = cv2.merge(channels)
        result = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        return result


class DenoiseProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Denoise"
        self.description = "Remove noise from image"
        self.parameters = {
            "strength": {
                "type": "range",
                "default": 10,
                "min": 1,
                "max": 30,
                "description": "Denoising strength",
            },
            "method": {
                "type": "select",
                "options": ["fast", "quality"],
                "default": "fast",
                "description": "Denoising method",
            },
        }

    def process(self, image, **kwargs):
        strength = kwargs.get("strength", 10)
        method = kwargs.get("method", "fast")

        if method == "fast":
            denoised = cv2.fastNlMeansDenoisingColored(
                image, None, strength, strength, 7, 21
            )
        else:
            denoised = cv2.fastNlMeansDenoisingColored(
                image, None, strength, strength, 7, 35
            )

        return denoised


class ThresholdProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Threshold"
        self.description = "Apply threshold to create binary image"
        self.parameters = {
            "threshold_value": {
                "type": "range",
                "default": 127,
                "min": 0,
                "max": 255,
                "description": "Threshold value",
            },
            "method": {
                "type": "select",
                "options": ["binary", "binary_inv", "otsu", "adaptive"],
                "default": "binary",
                "description": "Threshold method",
            },
        }

    def process(self, image, **kwargs):
        threshold_value = kwargs.get("threshold_value", 127)
        method = kwargs.get("method", "binary")

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if method == "binary":
            _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        elif method == "binary_inv":
            _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
        elif method == "otsu":
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:  # adaptive
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

        # Convert back to 3-channel
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)


class ConvolutionProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Custom Convolution"
        self.description = "Apply custom convolution kernel to image"
        self.parameters = {
            "kernel": {
                "type": "text",
                "default": "0,-1,0;-1,5,-1;0,-1,0",
                "description": "Kernel matrix (semicolon-separated rows, comma-separated values). Example: '0,-1,0;-1,5,-1;0,-1,0' for sharpening",
            },
            "normalize": {
                "type": "boolean",
                "default": False,
                "description": "Normalize kernel (divide by sum of absolute values)",
            },
            "scale": {
                "type": "number",
                "default": 1.0,
                "min": 0.1,
                "max": 10.0,
                "description": "Scale factor to multiply the result",
            },
        }

    def process(self, image, **kwargs):
        kernel_str = kwargs.get("kernel", "0,-1,0;-1,5,-1;0,-1,0")
        normalize = kwargs.get("normalize", False)
        scale = kwargs.get("scale", 1.0)

        try:
            # Parse kernel string
            rows = kernel_str.split(";")
            kernel = []
            for row in rows:
                values = [float(v.strip()) for v in row.split(",")]
                kernel.append(values)

            kernel = np.array(kernel, dtype=np.float32)

            # Validate kernel
            if kernel.shape[0] != kernel.shape[1]:
                raise ValueError("Kernel must be square")
            if kernel.shape[0] % 2 == 0:
                raise ValueError("Kernel dimensions must be odd")

            # Normalize if requested
            if normalize:
                kernel_sum = np.abs(kernel).sum()
                if kernel_sum != 0:
                    kernel = kernel / kernel_sum

            # Apply convolution
            result = cv2.filter2D(image, -1, kernel)

            # Apply scale
            if scale != 1.0:
                result = cv2.convertScaleAbs(result, alpha=scale)

            return result

        except Exception as e:
            print(f"Error parsing kernel: {e}")
            # Return original image if kernel parsing fails
            return image


class MedianFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Median Filter"
        self.description = "Apply median filter to reduce noise"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size (must be odd)",
            }
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))

        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        return cv2.medianBlur(image, kernel_size)


class MeanFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Mean Filter"
        self.description = "Apply mean (average) filter for smoothing"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size",
            }
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))

        return cv2.blur(image, (kernel_size, kernel_size))


class MaximumFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Maximum Filter"
        self.description = "Apply maximum filter (dilation-based)"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size",
            }
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))

        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return cv2.dilate(image, kernel)


class MinimumFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Minimum Filter"
        self.description = "Apply minimum filter (erosion-based)"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size",
            }
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))

        kernel = np.ones((kernel_size, kernel_size), np.uint8)
        return cv2.erode(image, kernel)


class UnsharpMaskProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Unsharp Mask"
        self.description = "Sharpen image using unsharp masking"
        self.parameters = {
            "amount": {
                "type": "number",
                "default": 1.5,
                "min": 0.5,
                "max": 5.0,
                "description": "Sharpening amount",
            },
            "radius": {
                "type": "number",
                "default": 1.0,
                "min": 0.5,
                "max": 10.0,
                "description": "Blur radius",
            },
            "threshold": {
                "type": "number",
                "default": 0,
                "min": 0,
                "max": 255,
                "description": "Threshold for edge detection",
            },
        }

    def process(self, image, **kwargs):
        amount = kwargs.get("amount", 1.5)
        radius = kwargs.get("radius", 1.0)
        threshold = kwargs.get("threshold", 0)

        # Create blurred version
        kernel_size = int(radius * 2) * 2 + 1
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), radius)

        # Calculate the sharpened image
        sharpened = cv2.addWeighted(image, 1.0 + amount, blurred, -amount, 0)

        # Apply threshold if specified
        if threshold > 0:
            low_contrast_mask = np.abs(image - blurred) < threshold
            sharpened = np.where(low_contrast_mask, image, sharpened)

        return np.clip(sharpened, 0, 255).astype(np.uint8)


class VarianceFilterProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Variance Filter"
        self.description = "Calculate local variance for texture analysis"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size",
            }
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))

        # Convert to grayscale for variance calculation
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Calculate mean
        mean = cv2.blur(gray.astype(np.float32), (kernel_size, kernel_size))

        # Calculate mean of squares
        mean_sq = cv2.blur((gray.astype(np.float32) ** 2), (kernel_size, kernel_size))

        # Variance = E[X^2] - E[X]^2
        variance = mean_sq - (mean**2)
        variance = np.clip(variance, 0, 255).astype(np.uint8)

        # Convert back to BGR
        return cv2.cvtColor(variance, cv2.COLOR_GRAY2BGR)


class TopHatProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Top Hat"
        self.description = "Top-hat morphological transformation"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 9,
                "min": 3,
                "max": 31,
                "description": "Kernel size",
            },
            "operation": {
                "type": "select",
                "options": ["white", "black"],
                "default": "white",
                "description": "Top-hat type (white for bright features, black for dark features)",
            },
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 9))
        operation = kwargs.get("operation", "white")

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        if operation == "white":
            # White top-hat: original - opening
            result = cv2.morphologyEx(image, cv2.MORPH_TOPHAT, kernel)
        else:
            # Black top-hat: closing - original
            result = cv2.morphologyEx(image, cv2.MORPH_BLACKHAT, kernel)

        return result


class GaussianBlurProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Gaussian Blur"
        self.description = "Apply Gaussian blur filter"
        self.parameters = {
            "kernel_size": {
                "type": "number",
                "default": 5,
                "min": 3,
                "max": 31,
                "description": "Kernel size (must be odd)",
            },
            "sigma": {
                "type": "number",
                "default": 0,
                "min": 0,
                "max": 10,
                "description": "Standard deviation (0 for auto)",
            },
        }

    def process(self, image, **kwargs):
        kernel_size = int(kwargs.get("kernel_size", 5))
        sigma = kwargs.get("sigma", 0)

        # Ensure kernel size is odd
        if kernel_size % 2 == 0:
            kernel_size += 1

        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)


class FlatFieldCorrectionProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Flat Field Correction"
        self.description = "Apply flat field correction using gain and dark images"
        self.parameters = {
            "input_type": {
                "type": "select",
                "options": ["projection", "gain", "dark"],
                "default": "projection",
                "description": "Type of input image (projection=raw image, gain=bright field, dark=dark field)",
            },
            "epsilon": {
                "type": "number",
                "default": 1e-6,
                "min": 1e-10,
                "max": 1.0,
                "description": "Small value to prevent division by zero",
            },
        }
        self.multi_input = True
        self.input_slots = ["projection", "gain", "dark"]

    def process_multi(self, images_dict, **kwargs):
        """Process multiple input images
        Formula: corrected = (projection - dark) / (gain - dark)
        """
        epsilon = kwargs.get("epsilon", 1e-6)

        # Get images from dict
        projection = images_dict.get("projection")
        gain = images_dict.get("gain")
        dark = images_dict.get("dark")

        # Validate inputs
        if projection is None or gain is None or dark is None:
            raise ValueError(
                "Flat field correction requires projection, gain, and dark images"
            )

        # Convert to float for calculations
        projection_f = projection.astype(np.float32)
        gain_f = gain.astype(np.float32)
        dark_f = dark.astype(np.float32)

        # Apply flat field correction
        numerator = projection_f - dark_f
        denominator = gain_f - dark_f + epsilon

        corrected = numerator / denominator

        # Normalize to 0-255 range
        corrected = np.clip(corrected * 255, 0, 255).astype(np.uint8)

        return corrected

    def process(self, image, **kwargs):
        """Single input mode - just return the image"""
        return image


# =============================================================================
# Math Operations (Multi-input processors)
# =============================================================================


class AddProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Add"
        self.description = "Add two or more images pixel-wise"
        self.parameters = {
            "weight": {
                "type": "number",
                "default": 1.0,
                "min": 0.0,
                "max": 2.0,
                "step": 0.1,
                "description": "Weight for the addition",
            }
        }
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        weight = kwargs.get("weight", 1.0)
        images = list(images_dict.values())

        if len(images) < 2:
            raise ValueError("Add operation requires at least 2 images")

        result = images[0].astype(np.float32)
        for img in images[1:]:
            result = cv2.add(result, img.astype(np.float32))

        result = result * weight
        return np.clip(result, 0, 255).astype(np.uint8)

    def process(self, image, **kwargs):
        return image


class SubtractProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Subtract"
        self.description = "Subtract second image from first image"
        self.parameters = {
            "absolute": {
                "type": "boolean",
                "default": False,
                "description": "Take absolute value of result",
            }
        }
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        absolute = kwargs.get("absolute", False)

        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("Subtract operation requires both image1 and image2")

        result = cv2.subtract(image1.astype(np.float32), image2.astype(np.float32))

        if absolute:
            result = np.abs(result)

        return np.clip(result, 0, 255).astype(np.uint8)

    def process(self, image, **kwargs):
        return image


class MultiplyProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Multiply"
        self.description = "Multiply two images pixel-wise"
        self.parameters = {
            "scale": {
                "type": "number",
                "default": 1.0,
                "min": 0.001,
                "max": 10.0,
                "step": 0.1,
                "description": "Scale factor for result",
            }
        }
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        scale = kwargs.get("scale", 1.0)

        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("Multiply operation requires both image1 and image2")

        result = (image1.astype(np.float32) / 255.0) * (
            image2.astype(np.float32) / 255.0
        )
        result = result * 255.0 * scale

        return np.clip(result, 0, 255).astype(np.uint8)

    def process(self, image, **kwargs):
        return image


class DivideProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Divide"
        self.description = "Divide first image by second image"
        self.parameters = {
            "epsilon": {
                "type": "number",
                "default": 1e-6,
                "min": 1e-10,
                "max": 1.0,
                "description": "Small value to prevent division by zero",
            },
            "scale": {
                "type": "number",
                "default": 255.0,
                "min": 1.0,
                "max": 1000.0,
                "description": "Scale factor for result",
            },
        }
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        epsilon = kwargs.get("epsilon", 1e-6)
        scale = kwargs.get("scale", 255.0)

        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("Divide operation requires both image1 and image2")

        result = image1.astype(np.float32) / (image2.astype(np.float32) + epsilon)
        result = result * scale

        return np.clip(result, 0, 255).astype(np.uint8)

    def process(self, image, **kwargs):
        return image


class AndProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "AND (Bitwise)"
        self.description = "Perform bitwise AND operation on two images"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("AND operation requires both image1 and image2")

        result = cv2.bitwise_and(image1, image2)
        return result

    def process(self, image, **kwargs):
        return image


class OrProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "OR (Bitwise)"
        self.description = "Perform bitwise OR operation on two images"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("OR operation requires both image1 and image2")

        result = cv2.bitwise_or(image1, image2)
        return result

    def process(self, image, **kwargs):
        return image


class XorProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "XOR (Bitwise)"
        self.description = "Perform bitwise XOR operation on two images"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("XOR operation requires both image1 and image2")

        result = cv2.bitwise_xor(image1, image2)
        return result

    def process(self, image, **kwargs):
        return image


class MinProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Minimum"
        self.description = "Take minimum pixel values from two or more images"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        images = list(images_dict.values())

        if len(images) < 2:
            raise ValueError("Minimum operation requires at least 2 images")

        result = images[0]
        for img in images[1:]:
            result = cv2.min(result, img)

        return result

    def process(self, image, **kwargs):
        return image


class MaxProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Maximum"
        self.description = "Take maximum pixel values from two or more images"
        self.parameters = {}
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        images = list(images_dict.values())

        if len(images) < 2:
            raise ValueError("Maximum operation requires at least 2 images")

        result = images[0]
        for img in images[1:]:
            result = cv2.max(result, img)

        return result

    def process(self, image, **kwargs):
        return image


class GammaProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Gamma Correction"
        self.description = "Apply gamma correction to two images combined"
        self.parameters = {
            "gamma": {
                "type": "number",
                "default": 1.0,
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "description": "Gamma value (< 1 brightens, > 1 darkens)",
            },
            "blend_alpha": {
                "type": "number",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.1,
                "description": "Blend ratio between images (0=image1, 1=image2)",
            },
        }
        self.multi_input = True
        self.input_slots = ["image1", "image2"]

    def process_multi(self, images_dict, **kwargs):
        gamma = kwargs.get("gamma", 1.0)
        blend_alpha = kwargs.get("blend_alpha", 0.5)

        image1 = images_dict.get("image1")
        image2 = images_dict.get("image2")

        if image1 is None or image2 is None:
            raise ValueError("Gamma correction requires both image1 and image2")

        blended = cv2.addWeighted(image1, 1 - blend_alpha, image2, blend_alpha, 0)

        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(
            np.uint8
        )

        result = cv2.LUT(blended, table)

        return result

    def process(self, image, **kwargs):
        return image
