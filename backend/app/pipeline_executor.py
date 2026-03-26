"""Pipeline executor — runs a connected graph of image processing nodes."""

import os
import uuid
import logging
import shutil

import cv2

from app.node_registry import NodeRegistry

logger = logging.getLogger(__name__)


class PipelineExecutor:
    """Executes image processing pipelines."""

    def __init__(self, socketio=None, node_registry=None):
        self.socketio = socketio
        self.node_registry = node_registry or NodeRegistry()
        # Get the base directory (backend folder)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def execute(self, nodes, edges):
        """Execute a pipeline of connected nodes"""
        try:
            # Build execution graph
            execution_graph = self._build_execution_graph(nodes, edges)

            # Find ALL input nodes (support multiple inputs for multi-input processors)
            source_input_nodes = [node for node in nodes if node["type"] == "input"]
            if not source_input_nodes:
                raise ValueError("No input node found in pipeline")

            uploads_folder = os.path.join(self.base_dir, "uploads")

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

                input_path = self._find_image_file(file_id, uploads_folder)
                if not input_path:
                    logger.warning(
                        f"Input image not found for node {input_node['id']}: {file_id}"
                    )
                    continue

                logger.info(
                    f"Found input image for node {input_node['id']} at: {input_path}"
                )

                # Verify the image can be loaded
                test_image = cv2.imread(input_path)
                if test_image is None:
                    logger.warning(
                        f"Cannot load input image for node {input_node['id']}: {input_path}"
                    )
                    continue

                logger.info(
                    f"Input image loaded for node {input_node['id']}, shape: {test_image.shape}"
                )

                # Store the image path for this input node
                node_outputs[input_node["id"]] = input_path

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

                    source_image_path = node_outputs.get(output_source_ids[0])
                    if not source_image_path:
                        raise ValueError(
                            f"No image available from source node {output_source_ids[0]}"
                        )

                    # Save final result
                    output_id = str(uuid.uuid4())
                    outputs_folder = os.path.join(self.base_dir, "outputs")
                    source_ext = os.path.splitext(source_image_path)[1].lower()

                    if source_ext == ".npz":
                        output_path = os.path.join(outputs_folder, f"{output_id}.npz")
                        shutil.copy2(source_image_path, output_path)
                    else:
                        output_format = node["data"].get("format", "png")
                        output_path = os.path.join(
                            outputs_folder, f"{output_id}.{output_format}"
                        )
                        image = cv2.imread(source_image_path)
                        if image is None:
                            raise ValueError(
                                f"Cannot load output image from source: {source_image_path}"
                            )
                        cv2.imwrite(output_path, image)

                    output_results.append(
                        {
                            "output_id": output_id,
                            "output_path": output_path,
                            "output_ext": os.path.splitext(output_path)[1].lower(),
                            "output_name": os.path.basename(output_path),
                            "output_type": (
                                "artifact" if source_ext == ".npz" else "image"
                            ),
                            "node_id": node["id"],
                        }
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
                    processor_kwargs = dict(node["data"])
                    outputs_folder = os.path.join(self.base_dir, "outputs")
                    processor_kwargs["_outputs_folder"] = outputs_folder

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
                            source_image_path = node_outputs.get(source_node_id)
                            if source_image_path:
                                raw_input_slots = set(
                                    getattr(processor, "raw_input_slots", [])
                                )
                                if slot_name in raw_input_slots:
                                    images_dict[slot_name] = source_image_path
                                    logger.debug(
                                        f"  Mapped raw slot '{slot_name}' from node {source_node_id}"
                                    )
                                else:
                                    img = cv2.imread(source_image_path)
                                    if img is not None:
                                        images_dict[slot_name] = img
                                        logger.debug(
                                            f"  Mapped slot '{slot_name}' from node {source_node_id}"
                                        )
                                    else:
                                        logger.warning(
                                            f"  Could not load image for slot '{slot_name}' from {source_image_path}"
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
                            processed_image = processor.process_multi(
                                images_dict, **processor_kwargs
                            )
                        else:
                            raise TypeError(
                                f"Processor {processor.name} claims multi_input but has no process_multi method"
                            )

                    else:
                        # Single input processor (existing behavior)
                        source_image_path = node_outputs.get(upstream_ids[0])
                        if not source_image_path:
                            raise ValueError(
                                f"No image available from source node {upstream_ids[0]}"
                            )

                        logger.debug(f"Input image path: {source_image_path}")

                        # Verify source image exists and is loadable
                        if not os.path.exists(source_image_path):
                            raise FileNotFoundError(
                                f"Image file not found: {source_image_path}"
                            )

                        test_img = cv2.imread(source_image_path)
                        if test_img is None:
                            raise ValueError(
                                f"Cannot load image for processing: {source_image_path}"
                            )

                        processed_image = processor.process(
                            source_image_path, **processor_kwargs
                        )

                    preview_id = None
                    if hasattr(processed_image, "shape"):
                        intermediate_id = str(uuid.uuid4())
                        intermediate_path = os.path.join(
                            outputs_folder, f"{intermediate_id}.png"
                        )
                        cv2.imwrite(intermediate_path, processed_image)
                        node_outputs[node["id"]] = intermediate_path
                        preview_id = intermediate_id
                    elif isinstance(processed_image, dict) and processed_image.get(
                        "artifact_path"
                    ):
                        artifact_path = processed_image["artifact_path"]
                        if not os.path.exists(artifact_path):
                            raise FileNotFoundError(
                                f"Processor artifact output not found: {artifact_path}"
                            )
                        node_outputs[node["id"]] = artifact_path
                    elif isinstance(processed_image, str) and os.path.exists(
                        processed_image
                    ):
                        node_outputs[node["id"]] = processed_image
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
            if not output_results:
                outputs_folder = os.path.join(self.base_dir, "outputs")
                sink_node_ids = [
                    node_id
                    for node_id, node_info in execution_graph.items()
                    if not node_info["outputs"]
                ]

                for sink_node_id in sink_node_ids:
                    sink_node = next(
                        (n for n in nodes if n["id"] == sink_node_id), None
                    )
                    if not sink_node:
                        continue
                    if sink_node["type"] in {"input", "output"}:
                        continue

                    source_path = node_outputs.get(sink_node_id)
                    if not source_path or not os.path.exists(source_path):
                        continue

                    source_ext = os.path.splitext(source_path)[1].lower()
                    source_dir = os.path.abspath(os.path.dirname(source_path))
                    outputs_dir_abs = os.path.abspath(outputs_folder)

                    if source_dir == outputs_dir_abs:
                        output_path = source_path
                    else:
                        output_id = str(uuid.uuid4())
                        output_path = os.path.join(
                            outputs_folder, f"{output_id}{source_ext}"
                        )
                        shutil.copy2(source_path, output_path)

                    output_id = os.path.splitext(os.path.basename(output_path))[0]
                    output_results.append(
                        {
                            "output_id": output_id,
                            "output_path": output_path,
                            "output_ext": os.path.splitext(output_path)[1].lower(),
                            "output_name": os.path.basename(output_path),
                            "output_type": (
                                "artifact"
                                if os.path.splitext(output_path)[1].lower() == ".npz"
                                else "image"
                            ),
                            "node_id": sink_node_id,
                        }
                    )

            if output_results:
                # If multiple outputs, return the first one for compatibility
                # but include all outputs in the response
                return {
                    "output_id": output_results[0]["output_id"],
                    "output_path": output_results[0]["output_path"],
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

    def _find_image_file(self, file_id, folder):
        """Find image file by ID in specified folder"""
        # Extended list of supported image formats
        extensions = [
            "png",
            "jpg",
            "jpeg",
            "gif",
            "bmp",
            "tiff",
            "tif",
            "webp",
            "ico",
            "jfif",
        ]
        for ext in extensions:
            filepath = os.path.join(folder, f"{file_id}.{ext}")
            if os.path.exists(filepath):
                return filepath
        return None
