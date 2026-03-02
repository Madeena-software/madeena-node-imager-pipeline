"""Tests for the PipelineExecutor — exercises the graph-building, topological
sort, and end-to-end execution logic."""

import os
import sys
import uuid

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.pipeline_executor import PipelineExecutor


@pytest.fixture()
def executor(tmp_path):
    """Create a PipelineExecutor that reads/writes to a temp directory."""
    ex = PipelineExecutor(socketio=None)
    ex.base_dir = str(tmp_path)
    uploads = tmp_path / "uploads"
    outputs = tmp_path / "outputs"
    uploads.mkdir()
    outputs.mkdir()
    return ex


@pytest.fixture()
def uploaded_image(executor):
    """Write a small test image into the executor's uploads folder and return its file_id."""
    file_id = str(uuid.uuid4())
    img = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    path = os.path.join(executor.base_dir, "uploads", f"{file_id}.png")
    cv2.imwrite(path, img)
    return file_id


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------


class TestBuildExecutionGraph:
    def test_simple_chain(self, executor):
        nodes = [
            {"id": "n1", "type": "input", "data": {}},
            {"id": "n2", "type": "processor", "data": {}},
            {"id": "n3", "type": "output", "data": {}},
        ]
        edges = [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
        ]
        graph = executor._build_execution_graph(nodes, edges)
        assert "n1" in graph
        assert "n2" in graph["n1"]["outputs"]
        assert "n1" in graph["n2"]["inputs"]

    def test_isolated_node(self, executor):
        nodes = [{"id": "n1", "type": "input", "data": {}}]
        graph = executor._build_execution_graph(nodes, [])
        assert graph["n1"]["inputs"] == []
        assert graph["n1"]["outputs"] == []


# ---------------------------------------------------------------------------
# Topological sort
# ---------------------------------------------------------------------------


class TestExecutionOrder:
    def test_linear_order(self, executor):
        nodes = [
            {"id": "a", "type": "input", "data": {}},
            {"id": "b", "type": "processor", "data": {}},
            {"id": "c", "type": "output", "data": {}},
        ]
        edges = [
            {"source": "a", "target": "b"},
            {"source": "b", "target": "c"},
        ]
        graph = executor._build_execution_graph(nodes, edges)
        order = executor._get_execution_order(graph, "a")
        assert order.index("a") < order.index("b") < order.index("c")


# ---------------------------------------------------------------------------
# End-to-end pipeline execution
# ---------------------------------------------------------------------------


class TestExecute:
    def test_simple_pipeline(self, executor, uploaded_image):
        """input → grayscale → output should produce a valid result."""
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "grayscale", "data": {}},
            {"id": "out1", "type": "output", "data": {"format": "png"}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
            {"source": "proc1", "target": "out1"},
        ]
        result = executor.execute(nodes, edges)
        assert "output_id" in result
        output_path = os.path.join(
            executor.base_dir, "outputs", f"{result['output_id']}.png"
        )
        assert os.path.exists(output_path)

    def test_no_input_node_raises(self, executor):
        nodes = [{"id": "x", "type": "output", "data": {}}]
        with pytest.raises(ValueError, match="No input node"):
            executor.execute(nodes, [])

    def test_missing_file_id_skips_input(self, executor):
        nodes = [
            {"id": "in1", "type": "input", "data": {}},  # no file_id
        ]
        with pytest.raises(Exception):
            executor.execute(nodes, [])

    def test_unknown_processor_raises(self, executor, uploaded_image):
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "nonexistent_abc", "data": {}},
            {"id": "out1", "type": "output", "data": {}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
            {"source": "proc1", "target": "out1"},
        ]
        with pytest.raises(ValueError, match="Unknown processor"):
            executor.execute(nodes, edges)

    def test_artifact_output_pipeline(self, executor, uploaded_image):
        """input -> artifact processor -> output should emit .npz file."""

        class DummyArtifactProcessor:
            name = "Dummy Artifact"
            multi_input = False

            def process(self, image_path, **kwargs):
                outputs_folder = kwargs["_outputs_folder"]
                artifact_path = os.path.join(outputs_folder, "dummy_calibration.npz")
                np.savez(artifact_path, value=np.array([1, 2, 3], dtype=np.int32))
                return {"artifact_path": artifact_path}

        executor.node_registry.processors["dummy_artifact"] = DummyArtifactProcessor()

        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "dummy_artifact", "data": {}},
            {"id": "out1", "type": "output", "data": {"format": "png"}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
            {"source": "proc1", "target": "out1"},
        ]

        result = executor.execute(nodes, edges)
        assert "output_id" in result
        output_path = os.path.join(
            executor.base_dir, "outputs", f"{result['output_id']}.npz"
        )
        assert os.path.exists(output_path)
        assert result["all_outputs"][0]["output_ext"] == ".npz"
        assert result["all_outputs"][0]["output_type"] == "artifact"
        assert result["all_outputs"][0]["output_name"].endswith(".npz")

    def test_terminal_camera_calibration_without_output_node(
        self, executor, uploaded_image
    ):
        """input -> camera_calibration should return downloadable npz metadata without output node."""

        class DummyArtifactProcessor:
            name = "Dummy Artifact"
            multi_input = False

            def process(self, image_path, **kwargs):
                outputs_folder = kwargs["_outputs_folder"]
                artifact_path = os.path.join(outputs_folder, "terminal_calibration.npz")
                np.savez(artifact_path, value=np.array([4, 5, 6], dtype=np.int32))
                return {"artifact_path": artifact_path}

        executor.node_registry.processors["camera_calibration"] = (
            DummyArtifactProcessor()
        )

        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "camera_calibration", "data": {}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
        ]

        result = executor.execute(nodes, edges)
        assert "output_id" in result
        assert result["all_outputs"][0]["output_ext"] == ".npz"
        assert result["all_outputs"][0]["output_type"] == "artifact"
        assert os.path.exists(result["all_outputs"][0]["output_path"])

    def test_terminal_non_camera_processor_without_output_node(
        self, executor, uploaded_image
    ):
        """Non-camera terminal processors should not auto-create downloadable outputs."""
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "grayscale", "data": {}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
        ]

        result = executor.execute(nodes, edges)
        assert result.get("status") == "completed"
        assert "output_id" not in result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestFindImageFile:
    def test_finds_existing(self, executor, uploaded_image):
        folder = os.path.join(executor.base_dir, "uploads")
        assert executor._find_image_file(uploaded_image, folder) is not None

    def test_returns_none_for_missing(self, executor):
        folder = os.path.join(executor.base_dir, "uploads")
        assert executor._find_image_file("no-such-id", folder) is None
