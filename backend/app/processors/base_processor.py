"""Base image processor class used by all processing nodes."""

import logging
import os

import cv2
import numpy as np
from PIL import Image as PILImage

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Base class for all image processors."""

    def __init__(self):
        self.name = ""
        self.description = ""
        self.parameters = {}

    def process(self, image_path, **kwargs):
        """Process a single image. Must be overridden by subclasses."""
        raise NotImplementedError

    def load_image(self, image_path):
        """Load an image using OpenCV, falling back to PIL for unsupported formats."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Try OpenCV first
        image = cv2.imread(image_path)
        if image is not None:
            return image

        # Fall back to PIL
        try:
            pil_image = PILImage.open(image_path)
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as exc:
            raise ValueError(
                f"Could not load image from: {image_path}. "
                f"OpenCV failed and PIL fallback also failed: {exc}"
            ) from exc

    def save_image(self, image, output_path):
        """Save an image using OpenCV."""
        cv2.imwrite(output_path, image)
        return output_path