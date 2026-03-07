"""Tests for the PipelineExecutor with session-scoped in-memory storage."""

import os
import sys
import uuid

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.in_memory_storage import storage
from app.pipeline_executor import PipelineExecutor


@pytest.fixture()
def executor():
    return PipelineExecutor(socketio=None)


@pytest.fixture()
def session_id():
    return f"test-session-{uuid.uuid4()}"


@pytest.fixture()
def uploaded_image(session_id):
    file_id = str(uuid.uuid4())
    image = np.random.randint(0, 256, (64, 64, 3), dtype=np.uint8)
    storage.put(session_id, file_id, image)
    yield file_id
    storage.clear_session(session_id)


@pytest.fixture()
def uploaded_json(session_id):
    file_id = str(uuid.uuid4())
    storage.put(
        session_id,
        file_id,
        {
            "kind": "json_metadata",
            "filename": "meta.json",
            "data": {
                "Patient Name": "Test Patient",
                "NIK": "123",
                "Gender": "Male",
                "Birthdate": "1965-08-24",
                "Scale X": 104.31,
                "Scale Y": 103.25,
                "Time": "250227155852 ",
            },
        },
    )
    return file_id


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
        assert graph["n2"]["inputs"] == ["n1"]
        assert graph["n2"]["outputs"] == ["n3"]


class TestExecutionOrder:
    def test_linear_order(self, executor):
        graph = executor._build_execution_graph(
            [
                {"id": "a", "type": "input", "data": {}},
                {"id": "b", "type": "processor", "data": {}},
                {"id": "c", "type": "output", "data": {}},
            ],
            [
                {"source": "a", "target": "b"},
                {"source": "b", "target": "c"},
            ],
        )
        order = executor._get_execution_order(graph, "a")
        assert order.index("a") < order.index("b") < order.index("c")


class TestExecute:
    def test_simple_pipeline(self, executor, session_id, uploaded_image):
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "grayscale", "data": {}},
            {"id": "out1", "type": "output", "data": {"format": "png"}},
        ]
        edges = [
            {"source": "in1", "target": "proc1"},
            {"source": "proc1", "target": "out1"},
        ]

        result = executor.execute(nodes, edges, session_id)
        assert result["all_outputs"][0]["output_ext"] == ".png"
        assert result["all_outputs"][0]["output_type"] == "image"

    def test_terminal_dicom_processor_returns_downloadable_artifact(
        self, executor, session_id, uploaded_image, uploaded_json
    ):
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {
                "id": "dcm1",
                "type": "tiff_json_to_dicom",
                "data": {"json_file_id": uploaded_json},
            },
        ]
        edges = [{"source": "in1", "target": "dcm1"}]

        result = executor.execute(nodes, edges, session_id)
        output = result["all_outputs"][0]
        stored_output = storage.get(session_id, output["output_id"])

        assert output["output_ext"] == ".dcm"
        assert output["output_type"] == "dicom"
        assert stored_output["download_name"].endswith(".dcm")
        assert stored_output["mimetype"] == "application/dicom"
        assert isinstance(stored_output["content"], bytes)

    def test_unknown_processor_raises(self, executor, session_id, uploaded_image):
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "nonexistent_abc", "data": {}},
        ]
        edges = [{"source": "in1", "target": "proc1"}]

        with pytest.raises(ValueError, match="Unknown processor"):
            executor.execute(nodes, edges, session_id)

    def test_terminal_non_artifact_without_output_node_returns_completed(
        self, executor, session_id, uploaded_image
    ):
        nodes = [
            {"id": "in1", "type": "input", "data": {"file_id": uploaded_image}},
            {"id": "proc1", "type": "grayscale", "data": {}},
        ]
        edges = [{"source": "in1", "target": "proc1"}]

        result = executor.execute(nodes, edges, session_id)
        assert result == {"status": "completed"}
