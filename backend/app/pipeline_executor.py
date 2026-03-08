"""Pipeline executor — runs a connected graph of image processing nodes."""

import io
import logging
import os
import shutil
import uuid
from contextlib import redirect_stdout

import cv2
import numpy as np

from app.node_registry import NodeRegistry
from app.in_memory_storage import storage

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes image processing pipelines."""

    def __init__(self, socketio=None, node_registry=None):
        self.socketio = socketio
        self.node_registry = node_registry or NodeRegistry()

    def _store_artifact(self, session_id, artifact_descriptor, output_id=None):
        """Persist an artifact payload for download and return output metadata."""
        artifact_bytes = artifact_descriptor.get("artifact")
        if isinstance(artifact_bytes, bytearray):
            artifact_bytes = bytes(artifact_bytes)

        if not isinstance(artifact_bytes, bytes):
            raise TypeError(
                "Artifact outputs must provide bytes in the 'artifact' field"
            )

        output_ext = artifact_descriptor.get("output_ext", ".bin")
        if not output_ext.startswith("."):
            output_ext = f".{output_ext}"

        output_id = output_id or str(uuid.uuid4())
        output_type = artifact_descriptor.get("output_type", "artifact")
        output_name = (
            artifact_descriptor.get("output_name") or f"{output_id}{output_ext}"
        )

        storage.put(
            session_id,
            output_id,
            {
                "content": artifact_bytes,
                "mimetype": artifact_descriptor.get(
                    "mime_type", "application/octet-stream"
                ),
                "download_name": output_name,
                "output_ext": output_ext,
                "output_type": output_type,
            },
        )

        return {
            "output_id": output_id,
            "output_ext": output_ext,
            "output_name": output_name,
            "output_type": output_type,
        }

    def _resolve_processor_kwargs(self, processor_kwargs, session_id):
        """Hydrate processor kwargs that reference uploaded session files."""
        return dict(processor_kwargs)

    def _resolve_uploaded_file_parameters(
        self, processor, processor_kwargs, session_id
    ):
        """Hydrate generic file-upload parameters from session storage."""
        resolved_kwargs = self._resolve_processor_kwargs(processor_kwargs, session_id)
        processor_parameters = getattr(processor, "parameters", {}) or {}

        for _, parameter_config in processor_parameters.items():
            if parameter_config.get("type") != "file":
                continue

            upload_action = parameter_config.get("upload_action", "base64")
            file_id_field = parameter_config.get("file_id_field")
            if upload_action not in {"json", "npz"} or not file_id_field:
                continue

            file_id = processor_kwargs.get(file_id_field)
            if not file_id:
                continue

            record = storage.get(session_id, file_id)
            if record is None:
                raise ValueError(
                    f"Uploaded file '{file_id_field}' was not found for this session"
                )

            expected_kind = (
                "json_metadata" if upload_action == "json" else "npz_calibration"
            )
            if not isinstance(record, dict) or record.get("kind") != expected_kind:
                raise TypeError(
                    f"{file_id_field} does not reference a valid uploaded {upload_action.upper()} file"
                )

            resolved_data_field = parameter_config.get("resolved_data_field")
            if resolved_data_field:
                resolved_kwargs[resolved_data_field] = record.get(
                    "data" if upload_action == "json" else "data"
                )

            resolved_filename_field = parameter_config.get(
                "resolved_filename_field",
                parameter_config.get("filename_field"),
            )
            if resolved_filename_field:
                resolved_kwargs[resolved_filename_field] = record.get("filename")

        return resolved_kwargs

    def execute(self, nodes, edges, session_id):
        """Execute a pipeline of connected nodes"""
        try:
            # Build execution graph
            execution_graph = self._build_execution_graph(nodes, edges)

            # Find ALL input nodes (support multiple inputs for multi-input processors)
            source_input_nodes = [node for node in nodes if node["type"] == "input"]
            if not source_input_nodes:
                raise ValueError("No input node found in pipeline")

            # Track processed images for each node
            node_outputs = {}

            # Process all input nodes and load their images
            for input_node in source_input_nodes:
                file_id = input_node["data"].get("file_id")
                if not file_id:
                    logger.warning(
                        f"Input node {input_node['id']} has no file_id, skipping"
                    )
                    continue

                image = storage.get(session_id, file_id)
                if image is None:
                    logger.warning(
                        f"Input image not found for node {input_node['id']}: {file_id}"
                    )
                    continue

                logger.info(
                    f"Input image loaded for node {input_node['id']}, shape: {image.shape}"
                )

                # Store the image for this input node
                node_outputs[input_node["id"]] = image

            # Verify we have at least one valid input
            if not node_outputs:
                raise Exception("No valid input images found")

            # Get first input node for execution order (any input node works as starting point)
            first_input_node = source_input_nodes[0]
            processed_nodes = set()
            output_results = []

            # Process nodes in topological order
            execution_order = self._get_execution_order(
                execution_graph, first_input_node["id"]
            )

            for node_id in execution_order:
                node = next((n for n in nodes if n["id"] == node_id), None)
                if not node or node["id"] in processed_nodes:
                    continue

                if node["type"] == "input":
                    processed_nodes.add(node["id"])
                    continue

                elif node["type"] == "output":
                    # Get the image feeding into this output node
                    output_source_ids = execution_graph[node["id"]]["inputs"]
                    if not output_source_ids:
                        raise ValueError(f"Output node {node['id']} has no input")

                    source_image = node_outputs.get(output_source_ids[0])
                    if source_image is None:
                        raise ValueError(
                            f"No image available from source node {output_source_ids[0]}"
                        )

                    if isinstance(source_image, np.ndarray):
                        output_id = str(uuid.uuid4())
                        storage.put(session_id, output_id, source_image)
                        output_results.append(
                            {
                                "output_id": output_id,
                                "output_ext": ".png",
                                "output_name": f"{output_id}.png",
                                "output_type": "image",
                                "node_id": node["id"],
                            }
                        )
                    elif isinstance(source_image, dict) and source_image.get(
                        "artifact"
                    ):
                        output_result = self._store_artifact(session_id, source_image)
                        output_result["node_id"] = node["id"]
                        output_results.append(output_result)
                    else:
                        raise TypeError(
                            f"Output node {node['id']} received unsupported input type: {type(source_image)}"
                        )

                    processed_nodes.add(node["id"])

                else:
                    # Process node — get image from input node(s)
                    upstream_ids = execution_graph[node["id"]]["inputs"]
                    if not upstream_ids:
                        raise ValueError(f"Processing node {node['id']} has no input")

                    processor = self.node_registry.get_processor(node["type"])
                    if not processor:
                        raise ValueError(f"Unknown processor: {node['type']}")

                    # Emit progress update
                    if self.socketio:
                        self.socketio.emit(
                            "pipeline_progress",
                            {
                                "node_id": node["id"],
                                "status": "processing",
                                "message": f"Processing {processor.name}",
                            },
                        )

                    logger.info(f"Processing node {node['id']} with {processor.name}")
                    processor_kwargs = self._resolve_uploaded_file_parameters(
                        processor,
                        dict(node["data"]),
                        session_id,
                    )

                    # Check if processor supports multiple inputs
                    if hasattr(processor, "multi_input") and processor.multi_input:
                        # Multi-input processor
                        images_dict = {}

                        # Get input slot mapping from node data
                        input_mapping = node["data"].get("input_mapping", {})

                        logger.info(
                            f"Multi-input node {node['id']}: mapping={input_mapping}"
                        )

                        # Iterate through the slot mapping
                        for slot_name, source_node_id in input_mapping.items():
                            source_image = node_outputs.get(source_node_id)
                            if source_image is not None:
                                images_dict[slot_name] = source_image
                                logger.debug(
                                    f"  Mapped slot '{slot_name}' from node {source_node_id}"
                                )
                            else:
                                logger.warning(
                                    f"  No output found for slot '{slot_name}' from node {source_node_id}"
                                )

                        logger.info(
                            f"Multi-input processing with {len(images_dict)} slots: {list(images_dict.keys())}"
                        )

                        if not images_dict:
                            raise ValueError(
                                f"No images available for multi-input processor {processor.name}"
                            )

                        # Resize images to match dimensions if needed for multi-input ops
                        image_inputs = {
                            k: v for k, v in images_dict.items() if hasattr(v, "shape")
                        }
                        if len(image_inputs) > 1:
                            sizes = {k: v.shape[:2] for k, v in image_inputs.items()}
                            unique_sizes = set(sizes.values())
                            if len(unique_sizes) > 1:
                                # Use the first image's size as reference
                                ref_key = list(image_inputs.keys())[0]
                                ref_h, ref_w = image_inputs[ref_key].shape[:2]
                                logger.info(
                                    f"Resizing multi-input images to match {ref_key}: {ref_w}x{ref_h}"
                                )
                                for k, v in image_inputs.items():
                                    if v.shape[:2] != (ref_h, ref_w):
                                        images_dict[k] = cv2.resize(
                                            v,
                                            (ref_w, ref_h),
                                            interpolation=cv2.INTER_LINEAR,
                                        )

                        # Process with multiple inputs
                        if hasattr(processor, "process_multi"):
                            _buf_multi = io.StringIO()
                            with redirect_stdout(_buf_multi):
                                processed_image = processor.process_multi(
                                    images_dict, **processor_kwargs
                                )
                            _log_multi = _buf_multi.getvalue().strip()
                            if self.socketio and _log_multi:
                                self.socketio.emit(
                                    "pipeline_progress",
                                    {
                                        "node_id": node["id"],
                                        "status": "log",
                                        "message": _log_multi,
                                    },
                                )
                        else:
                            raise TypeError(
                                f"Processor {processor.name} claims multi_input but has no process_multi method"
                            )

                    else:
                        # Single input processor (existing behavior)
                        source_image = node_outputs.get(upstream_ids[0])
                        if source_image is None:
                            raise ValueError(
                                f"No image available from source node {upstream_ids[0]}"
                            )

                        _buf_single = io.StringIO()
                        with redirect_stdout(_buf_single):
                            processed_image = processor.process(
                                source_image, **processor_kwargs
                            )
                        _log_single = _buf_single.getvalue().strip()
                        if self.socketio and _log_single:
                            self.socketio.emit(
                                "pipeline_progress",
                                {
                                    "node_id": node["id"],
                                    "status": "log",
                                    "message": _log_single,
                                },
                            )

                    preview_id = None
                    if isinstance(processed_image, np.ndarray):
                        intermediate_id = str(uuid.uuid4())
                        storage.put(session_id, intermediate_id, processed_image)
                        node_outputs[node["id"]] = processed_image
                        preview_id = intermediate_id
                    elif isinstance(processed_image, dict) and processed_image.get(
                        "artifact"
                    ):
                        node_outputs[node["id"]] = processed_image

                        if not execution_graph[node["id"]]["outputs"]:
                            output_result = self._store_artifact(
                                session_id, processed_image
                            )
                            output_result["node_id"] = node["id"]
                            output_results.append(output_result)
                    else:
                        raise TypeError(
                            f"Processor {processor.name} returned unsupported output type: {type(processed_image)}"
                        )

                    processed_nodes.add(node["id"])

                    # Emit completion update
                    if self.socketio:
                        progress_payload = {
                            "node_id": node["id"],
                            "status": "completed",
                        }
                        if preview_id:
                            progress_payload["preview_id"] = preview_id
                        self.socketio.emit("pipeline_progress", progress_payload)

            # Return all outputs or status
            if output_results:
                # If multiple outputs, return the first one for compatibility
                # but include all outputs in the response
                return {
                    "output_id": output_results[0]["output_id"],
                    "all_outputs": output_results,
                }

            return {"status": "completed"}

        except Exception as e:
            if self.socketio:
                self.socketio.emit("pipeline_error", {"error": str(e)})
            raise

    def _build_execution_graph(self, nodes, edges):
        """Build execution graph from nodes and edges"""
        graph = {}

        for node in nodes:
            graph[node["id"]] = {"node": node, "inputs": [], "outputs": []}

        for edge in edges:
            source = edge["source"]
            target = edge["target"]

            if source in graph and target in graph:
                graph[source]["outputs"].append(target)
                graph[target]["inputs"].append(source)

        return graph

    def _get_execution_order(self, graph, start_node_id):
        """Get topological order for pipeline execution"""
        visited = set()
        order = []

        def visit(node_id):
            if node_id in visited:
                return

            visited.add(node_id)

            # Visit all dependencies first
            for input_node in graph[node_id]["inputs"]:
                visit(input_node)

            order.append(node_id)

        visit(start_node_id)

        # Add remaining nodes
        for node_id in graph:
            if node_id not in visited:
                visit(node_id)

        return order
