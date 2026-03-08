"""Helpers for validating and loading custom processor modules safely."""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import os
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Any

from app.processors.base_processor import ImageProcessor

logger = logging.getLogger(__name__)

_VALID_PARAMETER_TYPES = {
    "boolean",
    "color",
    "file",
    "number",
    "range",
    "select",
    "string",
}
_VALID_UPLOAD_ACTIONS = {None, "base64", "json", "npz"}


class CustomNodeValidationError(Exception):
    """Raised when a custom node module fails validation."""


@dataclass(slots=True)
class DiscoveredProcessor:
    """Validated processor ready to be registered in the registry."""

    processor_id: str
    processor: ImageProcessor
    class_name: str


def ensure_custom_node_directory(directory: str) -> None:
    """Ensure the custom node directory exists and is import-friendly."""
    os.makedirs(directory, exist_ok=True)

    package_init = os.path.join(directory, "__init__.py")
    if not os.path.exists(package_init):
        with open(package_init, "w", encoding="utf-8") as file_handle:
            file_handle.write('"""User uploaded custom processors."""\n')


def discover_processors_from_file(
    file_path: str,
) -> tuple[list[DiscoveredProcessor], list[str], object]:
    """Import a Python file and return all validated processor instances from it."""
    module = _load_module_from_path(file_path)
    processor_classes = _find_processor_classes(module)
    if not processor_classes:
        raise CustomNodeValidationError(
            "No valid ImageProcessor subclasses were found in the uploaded file."
        )

    discovered: list[DiscoveredProcessor] = []
    warnings: list[str] = []

    for processor_class in processor_classes:
        try:
            processor = processor_class()
            processor_id = _resolve_processor_id(processor, processor_class)
            validate_processor_instance(processor_id, processor)
            discovered.append(
                DiscoveredProcessor(
                    processor_id=processor_id,
                    processor=processor,
                    class_name=processor_class.__name__,
                )
            )
        except Exception as exc:
            warnings.append(f"{processor_class.__name__}: {exc}")

    if not discovered:
        joined_warnings = "\n".join(warnings)
        raise CustomNodeValidationError(
            "The uploaded file loaded successfully, but no processor classes could be "
            f"instantiated safely.\n{joined_warnings}"
        )

    return discovered, warnings, module


def validate_processor_instance(processor_id: str, processor: ImageProcessor) -> None:
    """Validate processor metadata so /api/nodes stays serializable and stable."""
    if not processor_id or not isinstance(processor_id, str):
        raise CustomNodeValidationError("Processor ID must be a non-empty string.")

    name = getattr(processor, "name", "")
    if not isinstance(name, str) or not name.strip():
        raise CustomNodeValidationError(
            f"Processor '{processor_id}' must define a non-empty string name."
        )

    description = getattr(processor, "description", "")
    if not isinstance(description, str):
        raise CustomNodeValidationError(
            f"Processor '{processor_id}' description must be a string."
        )

    parameters = getattr(processor, "parameters", {})
    if not isinstance(parameters, dict):
        raise CustomNodeValidationError(
            f"Processor '{processor_id}' parameters must be a dictionary."
        )

    for parameter_name, parameter_config in parameters.items():
        _validate_parameter_config(processor_id, parameter_name, parameter_config)

    multi_input = bool(getattr(processor, "multi_input", False))
    if multi_input:
        input_slots = getattr(processor, "input_slots", None)
        if not isinstance(input_slots, list) or len(input_slots) < 2:
            raise CustomNodeValidationError(
                f"Processor '{processor_id}' must define at least two input_slots when multi_input=True."
            )
        if not all(isinstance(slot, str) and slot.strip() for slot in input_slots):
            raise CustomNodeValidationError(
                f"Processor '{processor_id}' input_slots must contain non-empty strings."
            )

    output_count = getattr(processor, "output_count", 1)
    if not isinstance(output_count, int) or output_count < 0:
        raise CustomNodeValidationError(
            f"Processor '{processor_id}' output_count must be an integer >= 0."
        )

    metadata = {
        "id": processor_id,
        "name": processor.name,
        "description": processor.description,
        "parameters": processor.parameters,
        "inputs": len(getattr(processor, "input_slots", [])) if multi_input else 1,
        "outputs": output_count,
        "multi_input": multi_input,
    }
    try:
        json.dumps(metadata)
    except TypeError as exc:
        raise CustomNodeValidationError(
            f"Processor '{processor_id}' metadata is not JSON serializable: {exc}"
        ) from exc


def list_custom_node_files(directory: str) -> list[str]:
    """Return all Python files in the custom node directory."""
    if not os.path.isdir(directory):
        return []

    discovered_files: list[str] = []
    for entry in os.listdir(directory):
        if not entry.endswith(".py"):
            continue
        if entry.startswith("_"):
            continue
        discovered_files.append(os.path.join(directory, entry))
    return sorted(discovered_files)


def unload_module(module_name: str | None) -> None:
    """Remove a dynamically imported module from sys.modules."""
    if module_name:
        sys.modules.pop(module_name, None)


def _load_module_from_path(file_path: str):
    module_name = _build_module_name(file_path)
    importlib.invalidate_caches()
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise CustomNodeValidationError(
            f"Could not create import specification for '{os.path.basename(file_path)}'."
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        unload_module(module_name)
        raise

    return module


def _find_processor_classes(module) -> list[type[ImageProcessor]]:
    classes: list[type[ImageProcessor]] = []
    for _, candidate in inspect.getmembers(module, inspect.isclass):
        if candidate is ImageProcessor:
            continue
        if candidate.__module__ != module.__name__:
            continue
        if issubclass(candidate, ImageProcessor):
            classes.append(candidate)
    return classes


def _resolve_processor_id(
    processor: ImageProcessor, processor_class: type[ImageProcessor]
) -> str:
    explicit_id = getattr(processor, "processor_id", None) or getattr(
        processor, "id", None
    )
    if explicit_id:
        return str(explicit_id).strip()

    class_name = processor_class.__name__
    if class_name.endswith("Processor"):
        class_name = class_name[: -len("Processor")]
    return _to_snake_case(class_name)


def _to_snake_case(value: str) -> str:
    converted = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", value)
    converted = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", converted)
    return converted.replace("__", "_").strip("_").lower()


def _validate_parameter_config(
    processor_id: str, parameter_name: str, parameter_config: Any
) -> None:
    if not isinstance(parameter_config, dict):
        raise CustomNodeValidationError(
            f"Parameter '{parameter_name}' in '{processor_id}' must be an object/dict."
        )

    parameter_type = parameter_config.get("type")
    if parameter_type not in _VALID_PARAMETER_TYPES:
        raise CustomNodeValidationError(
            f"Parameter '{parameter_name}' in '{processor_id}' uses unsupported type '{parameter_type}'."
        )

    if parameter_type == "select":
        options = parameter_config.get("options")
        if not isinstance(options, list) or not options:
            raise CustomNodeValidationError(
                f"Select parameter '{parameter_name}' in '{processor_id}' must define a non-empty options list."
            )

    if parameter_type == "file":
        upload_action = parameter_config.get("upload_action", "base64")
        if upload_action not in _VALID_UPLOAD_ACTIONS:
            raise CustomNodeValidationError(
                f"File parameter '{parameter_name}' in '{processor_id}' uses unsupported upload_action '{upload_action}'."
            )

        if upload_action in {"json", "npz"}:
            file_id_field = parameter_config.get("file_id_field")
            filename_field = parameter_config.get("filename_field")
            resolved_data_field = parameter_config.get("resolved_data_field")
            if not file_id_field or not filename_field or not resolved_data_field:
                raise CustomNodeValidationError(
                    f"File parameter '{parameter_name}' in '{processor_id}' must define file_id_field, filename_field, and resolved_data_field for server-managed uploads."
                )


def _build_module_name(file_path: str) -> str:
    module_stem = os.path.splitext(os.path.basename(file_path))[0]
    normalized = _to_snake_case(module_stem) or "custom_node"
    return f"app.processors.custom.uploaded_{normalized}_{uuid.uuid4().hex}"
