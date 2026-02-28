import cv2
import numpy as np
from PIL import Image
import os
import logging

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Base class for all image processors"""
    
    def __init__(self):
        self.name = ""
        self.description = ""
        self.parameters = {}
    
    def process(self, image_path, **kwargs):
        """Override this method in subclasses"""
        raise NotImplementedError
    
    def load_image(self, image_path):
        """Load image using OpenCV, with PIL fallback for unsupported formats"""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Try OpenCV first
        image = cv2.imread(image_path)
        if image is not None:
            return image
        
        # If OpenCV fails, try PIL as fallback
        try:
            from PIL import Image as PILImage
            
            pil_image = PILImage.open(image_path)
            # Convert PIL image to OpenCV format (RGB -> BGR)
            if pil_image.mode == 'RGBA':
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array and change color channel order
            opencv_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            return opencv_image
            
        except Exception as e:
            raise ValueError(
                f"Could not load image from: {image_path}. "
                f"OpenCV failed and PIL fallback also failed: {str(e)}"
            )
    
    def save_image(self, image, output_path):
        """Save image using OpenCV"""
        cv2.imwrite(output_path, image)
        return output_path