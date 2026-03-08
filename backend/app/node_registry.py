"""Central registry mapping processor IDs to their instances."""

from __future__ import annotations

import json
import logging
import os

from app.processors.basic_processors import (
    ResizeProcessor,
    BlurProcessor,
    BrightnessProcessor,
    EdgeDetectionProcessor,
    RotateProcessor,
    FlipProcessor,
    CropProcessor,
    GrayscaleProcessor,
    SepiaProcessor,
    InvertProcessor,
    SharpenProcessor,
    ErodeProcessor,
    DilateProcessor,
    HistogramEqualizationProcessor,
    DenoiseProcessor,
    ThresholdProcessor,
    ConvolutionProcessor,
    MedianFilterProcessor,
    MeanFilterProcessor,
    MaximumFilterProcessor,
    MinimumFilterProcessor,
    UnsharpMaskProcessor,
    VarianceFilterProcessor,
    TopHatProcessor,
    GaussianBlurProcessor,
    FlatFieldCorrectionProcessor,
    AddProcessor,
    SubtractProcessor,
    MultiplyProcessor,
    DivideProcessor,
    AndProcessor,
    OrProcessor,
    XorProcessor,
    MinProcessor,
    MaxProcessor,
    GammaProcessor,
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
    CameraCalibrationProcessor,
    ApplyCameraCalibrationProcessor,
    TiffJsonToDICOMProcessor,
)
from app.custom_node_service import (
    CustomNodeValidationError,
    discover_processors_from_file,
    ensure_custom_node_directory,
    list_custom_node_files,
    unload_module,
)

logger = logging.getLogger(__name__)


BUILTIN_CATEGORIES = {
    "blur": "Enhancement",
    "brightness": "Color",
    "grayscale": "Color",
    "sepia": "Color",
    "invert": "Color",
    "adjust_colors": "Color",
    "resize": "Transform",
    "rotate": "Transform",
    "flip": "Transform",
    "crop": "Transform",
    "sharpen": "Enhancement",
    "histogram_equalization": "Enhancement",
    "denoise": "Enhancement",
    "convolution": "Enhancement",
    "median_filter": "Filter",
    "mean_filter": "Filter",
    "maximum_filter": "Filter",
    "minimum_filter": "Filter",
    "unsharp_mask": "Filter",
    "variance_filter": "Filter",
    "top_hat": "Filter",
    "gaussian_blur": "Filter",
    "edge_detection": "Detection",
    "threshold": "Detection",
    "erode": "Morphological",
    "dilate": "Morphological",
    "flat_field": "Enhancement",
    "add": "Math",
    "subtract": "Math",
    "multiply": "Math",
    "divide": "Math",
    "and": "Math",
    "or": "Math",
    "xor": "Math",
    "min": "Math",
    "max": "Math",
    "gamma": "Math",
    "wavelet_denoise": "Pipeline",
    "pipeline_ffc": "Pipeline",
    "imagej_enhance_contrast": "Pipeline",
    "imagej_clahe": "Pipeline",
    "imagej_median_filter": "Pipeline",
    "imagej_hybrid_median": "Pipeline",
    "auto_threshold": "Pipeline",
    "pipeline_invert": "Pipeline",
    "imagej_normalize": "Pipeline",
    "wavelet_bg_removal": "Pipeline",
    "advanced_median_filter": "Pipeline",
    "camera_calibration": "Pipeline",
    "apply_camera_calibration": "Pipeline",
    "tiff_json_to_dicom": "Pipeline",
}


class NodeRegistry:
    """Registry for all available image processing nodes"""

    def __init__(
        self, custom_node_dir: str | None = None, load_custom_nodes: bool = True
    ):
        self.processors = {}
        self.processor_categories = {}
        self.processor_sources = {}
        self.source_to_processor_ids = {}
        self.loaded_modules = {}
        self.custom_source_categories = {}

        self._register_builtin_processors()

        if custom_node_dir and load_custom_nodes:
            self.load_custom_nodes_from_directory(custom_node_dir)

    def _register_builtin_processors(self):
        builtin_processors = {
            "resize": ResizeProcessor(),
            "blur": BlurProcessor(),
            "brightness": BrightnessProcessor(),
            "edge_detection": EdgeDetectionProcessor(),
            "rotate": RotateProcessor(),
            "flip": FlipProcessor(),
            "crop": CropProcessor(),
            "grayscale": GrayscaleProcessor(),
            "sepia": SepiaProcessor(),
            "invert": InvertProcessor(),
            "sharpen": SharpenProcessor(),
            "histogram_equalization": HistogramEqualizationProcessor(),
            "denoise": DenoiseProcessor(),
            "threshold": ThresholdProcessor(),
            "convolution": ConvolutionProcessor(),
            "median_filter": MedianFilterProcessor(),
            "mean_filter": MeanFilterProcessor(),
            "maximum_filter": MaximumFilterProcessor(),
            "minimum_filter": MinimumFilterProcessor(),
            "unsharp_mask": UnsharpMaskProcessor(),
            "variance_filter": VarianceFilterProcessor(),
            "top_hat": TopHatProcessor(),
            "gaussian_blur": GaussianBlurProcessor(),
            "erode": ErodeProcessor(),
            "dilate": DilateProcessor(),
            "flat_field": FlatFieldCorrectionProcessor(),
            "add": AddProcessor(),
            "subtract": SubtractProcessor(),
            "multiply": MultiplyProcessor(),
            "divide": DivideProcessor(),
            "and": AndProcessor(),
            "or": OrProcessor(),
            "xor": XorProcessor(),
            "min": MinProcessor(),
            "max": MaxProcessor(),
            "gamma": GammaProcessor(),
            "wavelet_denoise": WaveletDenoiseProcessor(),
            "pipeline_ffc": PipelineFlatFieldCorrectionProcessor(),
            "imagej_enhance_contrast": ImageJEnhanceContrastProcessor(),
            "imagej_clahe": ImageJCLAHEProcessor(),
            "imagej_median_filter": ImageJMedianFilterProcessor(),
            "imagej_hybrid_median": ImageJHybridMedianFilterProcessor(),
            "auto_threshold": AutoThresholdProcessor(),
            "pipeline_invert": PipelineInvertProcessor(),
            "imagej_normalize": ImageJNormalizeProcessor(),
            "wavelet_bg_removal": WaveletBackgroundRemovalProcessor(),
            "advanced_median_filter": AdvancedMedianFilterProcessor(),
            "camera_calibration": CameraCalibrationProcessor(),
            "apply_camera_calibration": ApplyCameraCalibrationProcessor(),
            "tiff_json_to_dicom": TiffJsonToDICOMProcessor(),
        }

        for processor_id, processor in builtin_processors.items():
            self.register_processor(
                processor_id,
                processor,
                BUILTIN_CATEGORIES[processor_id],
                source="builtin",
            )

    def register_processor(
        self, processor_id, processor, category, source, module=None
    ):
        """Register a processor instance under a category and source."""
        existing_source = self.processor_sources.get(processor_id)
        if existing_source and existing_source != source:
            raise CustomNodeValidationError(
                f"Processor ID '{processor_id}' is already registered by '{existing_source}'."
            )

        self.processors[processor_id] = processor
        self.processor_categories[processor_id] = category or "Other"
        self.processor_sources[processor_id] = source
        self.source_to_processor_ids.setdefault(source, set()).add(processor_id)
        if module is not None:
            self.loaded_modules[source] = module
        if source != "builtin":
            self.custom_source_categories[source] = category or "Other"

    def unregister_source(self, source):
        """Remove all processors registered from a given source path."""
        processor_ids = self.source_to_processor_ids.pop(source, set())
        for processor_id in processor_ids:
            self.processors.pop(processor_id, None)
            self.processor_categories.pop(processor_id, None)
            self.processor_sources.pop(processor_id, None)

        module = self.loaded_modules.pop(source, None)
        unload_module(getattr(module, "__name__", None))
        self.custom_source_categories.pop(source, None)

    def load_custom_nodes_from_directory(self, directory):
        """Load all persisted custom node files from disk."""
        ensure_custom_node_directory(directory)
        for file_path in list_custom_node_files(directory):
            try:
                self.register_custom_module(
                    file_path, self._read_custom_category(file_path)
                )
            except Exception as exc:
                logger.error(
                    "Failed to load custom node file %s: %s",
                    file_path,
                    exc,
                    exc_info=True,
                )
                try:
                    os.remove(file_path)
                except OSError:
                    logger.warning(
                        "Could not remove invalid custom node file %s", file_path
                    )
                self.remove_custom_metadata(file_path)

    def register_custom_module(self, file_path, category):
        """Load, validate, and register processors from a custom Python file."""
        source = os.path.abspath(file_path)
        discovered_processors, warnings, module = discover_processors_from_file(source)

        self.unregister_source(source)

        registered_ids = []
        try:
            for discovered in discovered_processors:
                self.register_processor(
                    discovered.processor_id,
                    discovered.processor,
                    category,
                    source=source,
                    module=module,
                )
                registered_ids.append(discovered.processor_id)
        except Exception:
            self.unregister_source(source)
            raise

        return {
            "registered_ids": registered_ids,
            "warnings": warnings,
            "module_name": getattr(module, "__name__", None),
            "category": category,
            "source": source,
        }

    def get_source_category(self, source):
        """Return the current category used for a custom source file."""
        return self.custom_source_categories.get(source)

    def save_custom_category_metadata(self, file_path, category):
        """Persist custom node category so it survives backend restarts."""
        metadata_path = self._metadata_path(file_path)
        with open(metadata_path, "w", encoding="utf-8") as file_handle:
            json.dump({"category": category}, file_handle)

    def remove_custom_metadata(self, file_path):
        """Delete persisted custom-node metadata if it exists."""
        metadata_path = self._metadata_path(file_path)
        if os.path.exists(metadata_path):
            os.remove(metadata_path)

    def _derive_category_name(self, file_path):
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        title = base_name.replace("_", " ").replace("-", " ").strip()
        return title.title() if title else "Custom"

    def _metadata_path(self, file_path):
        return f"{file_path}.meta.json"

    def _read_custom_category(self, file_path):
        metadata_path = self._metadata_path(file_path)
        if os.path.isfile(metadata_path):
            try:
                with open(metadata_path, "r", encoding="utf-8") as file_handle:
                    metadata = json.load(file_handle)
                category = (metadata.get("category") or "").strip()
                if category:
                    return category
            except (OSError, ValueError, TypeError):
                logger.warning("Could not read custom node metadata for %s", file_path)
        return self._derive_category_name(file_path)

    def get_all_nodes(self):
        """Return all available nodes with their metadata"""
        nodes = []

        # Input node
        nodes.append(
            {
                "id": "input",
                "name": "Image Input",
                "description": "Load an image file",
                "type": "input",
                "category": "Basic",
                "parameters": {"file_id": {"type": "string", "required": True}},
                "inputs": 0,
                "outputs": 1,
            }
        )

        for key, processor in self.processors.items():
            # Check if this is a multi-input processor
            is_multi_input = hasattr(processor, "multi_input") and processor.multi_input
            input_count = len(processor.input_slots) if is_multi_input else 1
            output_count = getattr(processor, "output_count", 1)

            node_data = {
                "id": key,
                "name": processor.name,
                "description": processor.description,
                "type": "processor",
                "category": self.processor_categories.get(key, "Other"),
                "parameters": processor.parameters,
                "inputs": input_count,
                "outputs": output_count,
            }

            # Add input_slots metadata for multi-input nodes
            if is_multi_input:
                node_data["input_slots"] = processor.input_slots
                node_data["multi_input"] = True

            nodes.append(node_data)

        # Output node
        nodes.append(
            {
                "id": "output",
                "name": "Image Output",
                "description": "Save or display the processed image",
                "type": "output",
                "category": "Basic",
                "parameters": {
                    "format": {
                        "type": "select",
                        "options": ["png", "jpg", "bmp"],
                        "default": "png",
                    }
                },
                "inputs": 1,
                "outputs": 0,
            }
        )

        return nodes

    def get_processor(self, processor_id):
        """Get a specific processor by ID"""
        return self.processors.get(processor_id)
