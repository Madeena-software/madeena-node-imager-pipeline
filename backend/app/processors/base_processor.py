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

    def process(self, image, **kwargs):
        """Process a single image. Must be overridden by subclasses."""
        raise NotImplementedError