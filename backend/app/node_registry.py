"""Central registry mapping processor IDs to their instances."""

from app.processors.basic_processors import (
    ResizeProcessor, BlurProcessor, BrightnessProcessor, EdgeDetectionProcessor,
    RotateProcessor, FlipProcessor, CropProcessor, GrayscaleProcessor,
    SepiaProcessor, InvertProcessor, SharpenProcessor, ErodeProcessor,
    DilateProcessor, HistogramEqualizationProcessor, DenoiseProcessor,
    ThresholdProcessor, ConvolutionProcessor,
    MedianFilterProcessor, MeanFilterProcessor, MaximumFilterProcessor,
    MinimumFilterProcessor, UnsharpMaskProcessor, VarianceFilterProcessor,
    TopHatProcessor, GaussianBlurProcessor, FlatFieldCorrectionProcessor,
    AddProcessor, SubtractProcessor, MultiplyProcessor, DivideProcessor,
    AndProcessor, OrProcessor, XorProcessor, MinProcessor, MaxProcessor, GammaProcessor
)
from app.processors.pipeline_processors import (
    WaveletDenoiseProcessor,
    PipelineFlatFieldCorrectionProcessor,
    ImageJEnhanceContrastProcessor,
    ImageJCLAHEProcessor,
    ImageJMedianFilterProcessor,
    ImageJHybridMedianFilterProcessor,
    AutoThresholdProcessor,
    PipelineInvertProcessor,
    ImageJNormalizeProcessor,
    WaveletBackgroundRemovalProcessor,
    AdvancedMedianFilterProcessor,
)

class NodeRegistry:
    """Registry for all available image processing nodes"""
    
    def __init__(self):
        self.processors = {
            # Basic operations
            'resize': ResizeProcessor(),
            'blur': BlurProcessor(),
            'brightness': BrightnessProcessor(),
            'edge_detection': EdgeDetectionProcessor(),
            
            # Transform operations
            'rotate': RotateProcessor(),
            'flip': FlipProcessor(),
            'crop': CropProcessor(),
            
            # Color operations
            'grayscale': GrayscaleProcessor(),
            'sepia': SepiaProcessor(),
            'invert': InvertProcessor(),
            
            # Enhancement operations
            'sharpen': SharpenProcessor(),
            'histogram_equalization': HistogramEqualizationProcessor(),
            'denoise': DenoiseProcessor(),
            'threshold': ThresholdProcessor(),
            'convolution': ConvolutionProcessor(),
            
            # Filter operations
            'median_filter': MedianFilterProcessor(),
            'mean_filter': MeanFilterProcessor(),
            'maximum_filter': MaximumFilterProcessor(),
            'minimum_filter': MinimumFilterProcessor(),
            'unsharp_mask': UnsharpMaskProcessor(),
            'variance_filter': VarianceFilterProcessor(),
            'top_hat': TopHatProcessor(),
            'gaussian_blur': GaussianBlurProcessor(),
            
            # Morphological operations
            'erode': ErodeProcessor(),
            'dilate': DilateProcessor(),
            
            # Multi-input operations
            'flat_field': FlatFieldCorrectionProcessor(),
            
            # Math operations
            'add': AddProcessor(),
            'subtract': SubtractProcessor(),
            'multiply': MultiplyProcessor(),
            'divide': DivideProcessor(),
            'and': AndProcessor(),
            'or': OrProcessor(),
            'xor': XorProcessor(),
            'min': MinProcessor(),
            'max': MaxProcessor(),
            'gamma': GammaProcessor(),
            
            # Pipeline operations (from imager-pipeline)
            'wavelet_denoise': WaveletDenoiseProcessor(),
            'pipeline_ffc': PipelineFlatFieldCorrectionProcessor(),
            'imagej_enhance_contrast': ImageJEnhanceContrastProcessor(),
            'imagej_clahe': ImageJCLAHEProcessor(),
            'imagej_median_filter': ImageJMedianFilterProcessor(),
            'imagej_hybrid_median': ImageJHybridMedianFilterProcessor(),
            'auto_threshold': AutoThresholdProcessor(),
            'pipeline_invert': PipelineInvertProcessor(),
            'imagej_normalize': ImageJNormalizeProcessor(),
            'wavelet_bg_removal': WaveletBackgroundRemovalProcessor(),
            'advanced_median_filter': AdvancedMedianFilterProcessor(),
        }
    
    def get_all_nodes(self):
        """Return all available nodes with their metadata"""
        nodes = []
        
        # Input node
        nodes.append({
            'id': 'input',
            'name': 'Image Input',
            'description': 'Load an image file',
            'type': 'input',
            'category': 'Basic',
            'parameters': {
                'file_id': {'type': 'string', 'required': True}
            },
            'inputs': 0,
            'outputs': 1
        })
        
        # Processing nodes with categories
        processor_categories = {
            # Color operations
            'blur': 'Enhancement',
            'brightness': 'Color',
            'grayscale': 'Color',
            'sepia': 'Color',
            'invert': 'Color',
            'adjust_colors': 'Color',
            
            # Transform operations
            'resize': 'Transform',
            'rotate': 'Transform',
            'flip': 'Transform',
            'crop': 'Transform',
            
            # Enhancement operations
            'sharpen': 'Enhancement',
            'histogram_equalization': 'Enhancement',
            'denoise': 'Enhancement',
            'convolution': 'Enhancement',
            
            # Filter operations
            'median_filter': 'Filter',
            'mean_filter': 'Filter',
            'maximum_filter': 'Filter',
            'minimum_filter': 'Filter',
            'unsharp_mask': 'Filter',
            'variance_filter': 'Filter',
            'top_hat': 'Filter',
            'gaussian_blur': 'Filter',
            
            # Detection operations
            'edge_detection': 'Detection',
            'threshold': 'Detection',
            
            # Morphological operations
            'erode': 'Morphological',
            'dilate': 'Morphological',
            
            # Multi-input operations
            'flat_field': 'Enhancement',
            
            # Math operations
            'add': 'Math',
            'subtract': 'Math',
            'multiply': 'Math',
            'divide': 'Math',
            'and': 'Math',
            'or': 'Math',
            'xor': 'Math',
            'min': 'Math',
            'max': 'Math',
            'gamma': 'Math',
            
            # Pipeline operations (from imager-pipeline)
            'wavelet_denoise': 'Pipeline',
            'pipeline_ffc': 'Pipeline',
            'imagej_enhance_contrast': 'Pipeline',
            'imagej_clahe': 'Pipeline',
            'imagej_median_filter': 'Pipeline',
            'imagej_hybrid_median': 'Pipeline',
            'auto_threshold': 'Pipeline',
            'pipeline_invert': 'Pipeline',
            'imagej_normalize': 'Pipeline',
            'wavelet_bg_removal': 'Pipeline',
            'advanced_median_filter': 'Pipeline',
        }
        
        for key, processor in self.processors.items():
            # Check if this is a multi-input processor
            is_multi_input = hasattr(processor, 'multi_input') and processor.multi_input
            input_count = len(processor.input_slots) if is_multi_input else 1
            
            node_data = {
                'id': key,
                'name': processor.name,
                'description': processor.description,
                'type': 'processor',
                'category': processor_categories.get(key, 'Other'),
                'parameters': processor.parameters,
                'inputs': input_count,
                'outputs': 1
            }
            
            # Add input_slots metadata for multi-input nodes
            if is_multi_input:
                node_data['input_slots'] = processor.input_slots
                node_data['multi_input'] = True
            
            nodes.append(node_data)
        
        # Output node
        nodes.append({
            'id': 'output',
            'name': 'Image Output',
            'description': 'Save or display the processed image',
            'type': 'output',
            'category': 'Basic',
            'parameters': {
                'format': {'type': 'select', 'options': ['png', 'jpg', 'bmp'], 'default': 'png'}
            },
            'inputs': 1,
            'outputs': 0
        })
        
        return nodes
    
    def get_processor(self, processor_id):
        """Get a specific processor by ID"""
        return self.processors.get(processor_id)