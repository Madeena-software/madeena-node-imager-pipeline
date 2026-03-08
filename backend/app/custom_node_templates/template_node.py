"""Template for user-uploaded custom pipeline nodes.

This file is intentionally verbose so it can be downloaded and used as a guide.
"""

from app.processors.base_processor import ImageProcessor


class ExampleSingleInputProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()

        # Give the node a stable backend ID. If omitted, the class name will be
        # converted automatically to snake_case.
        self.processor_id = "example_single_input"
        self.name = "Example Single Input"
        self.description = "Minimal example: one image in, one image out."

        # By default, processors use a single input and one output.
        # If you want to expose a different output count in the UI, set this.
        self.output_count = 1

        # Parameters defined here appear in the node properties modal.
        # Supported types in the current UI:
        # - number
        # - string
        # - select
        # - boolean
        # - range
        # - color
        # - file
        self.parameters = {
            "scale_factor": {
                "type": "number",
                "default": 1.0,
                "min": 0.1,
                "max": 5.0,
                "step": 0.1,
                "description": "Example numeric parameter shown in the UI.",
            },
            "label_text": {
                "type": "string",
                "default": "custom node",
                "placeholder": "Any text value",
                "description": "Example text parameter.",
            },
            "mode": {
                "type": "select",
                "options": ["fast", "accurate"],
                "default": "fast",
                "description": "Example dropdown/select parameter.",
            },
        }

    def process(self, image, **kwargs):
        # Access node property values from kwargs.
        scale_factor = float(kwargs.get("scale_factor", 1.0))
        label_text = kwargs.get("label_text", "custom node")
        mode = kwargs.get("mode", "fast")

        # Replace this with real image-processing logic.
        print(
            f"Processing image with scale_factor={scale_factor}, "
            f"label_text={label_text!r}, mode={mode}"
        )
        return image


class ExampleMultiInputProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.processor_id = "example_multi_input"
        self.name = "Example Multi Input"
        self.description = "Example node with multiple named input slots."

        # Enable multi-input mode.
        self.multi_input = True

        # Each slot name becomes a target handle in the UI.
        # The executor will pass a dict to process_multi(images_dict, **kwargs)
        # with keys that match these slot names.
        self.input_slots = ["primary", "secondary"]

        # A multi-input node can still expose any output count metadata.
        self.output_count = 1

        self.parameters = {
            "blend_weight": {
                "type": "number",
                "default": 0.5,
                "min": 0.0,
                "max": 1.0,
                "step": 0.05,
                "description": "Example parameter for multi-input processing.",
            }
        }

    def process_multi(self, images_dict, **kwargs):
        primary_image = images_dict.get("primary")
        secondary_image = images_dict.get("secondary")
        blend_weight = float(kwargs.get("blend_weight", 0.5))

        if primary_image is None or secondary_image is None:
            raise ValueError("Both 'primary' and 'secondary' inputs are required.")

        print(f"Blend weight: {blend_weight}")
        return primary_image

    def process(self, image, **kwargs):
        # Optional fallback when the node is executed like a single-input node.
        return image


class ExampleFileUploadProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.processor_id = "example_file_upload"
        self.name = "Example File Upload"
        self.description = (
            "Demonstrates file upload parameters in the node properties UI."
        )

        self.parameters = {
            # Example 1: server-managed JSON upload.
            # The frontend uploads the file to the backend and stores the returned
            # file ID inside the node data. During execution, the executor resolves
            # that file ID and injects these kwargs for your process() method:
            # - metadata_json
            # - metadata_filename
            "metadata_file": {
                "type": "file",
                "default": None,
                "required": True,
                "file_filter": ".json",
                "upload_action": "json",
                "file_id_field": "metadata_file_id",
                "filename_field": "metadata_filename",
                "resolved_data_field": "metadata_json",
                "resolved_filename_field": "metadata_filename",
                "description": "Upload a JSON file and receive parsed data in kwargs.",
            },
            # Example 2: server-managed NPZ upload.
            # During execution, the executor injects:
            # - calibration_bytes
            # - calibration_filename
            "calibration_file": {
                "type": "file",
                "default": None,
                "required": False,
                "file_filter": ".npz",
                "upload_action": "npz",
                "file_id_field": "calibration_file_id",
                "filename_field": "calibration_filename",
                "resolved_data_field": "calibration_bytes",
                "resolved_filename_field": "calibration_filename",
                "description": "Upload a .npz file and receive raw bytes in kwargs.",
            },
            # Example 3: inline/base64 file upload.
            # Use this only for smaller files because the file contents are stored
            # directly in the pipeline JSON.
            "inline_attachment": {
                "type": "file",
                "default": None,
                "required": False,
                "file_filter": ".txt,.csv",
                "upload_action": "base64",
                "description": "Stores file contents directly as a data URL string.",
            },
        }

    def process(self, image, **kwargs):
        metadata_json = kwargs.get("metadata_json")
        metadata_filename = kwargs.get("metadata_filename")
        calibration_bytes = kwargs.get("calibration_bytes")
        calibration_filename = kwargs.get("calibration_filename")
        inline_attachment = kwargs.get("inline_attachment")

        if metadata_json is None:
            raise ValueError("metadata_json is required for this example processor.")

        print(f"Loaded metadata from {metadata_filename}")
        print(f"Metadata keys: {sorted(metadata_json.keys())}")

        if calibration_bytes:
            print(
                f"Loaded calibration file {calibration_filename} "
                f"with {len(calibration_bytes)} bytes"
            )

        if inline_attachment:
            print("Inline attachment was provided as a data URL string.")

        return image
