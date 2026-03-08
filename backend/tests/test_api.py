"""Tests for the Flask API routes — upload, node listing, pipeline execution."""

import importlib.util
import io
import json
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("FLASK_ENV", "testing")

_app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
_spec = importlib.util.spec_from_file_location("app_entry", _app_path)
_app_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_module)
flask_app = _app_module.app


@pytest.fixture()
def app(tmp_path):
    flask_app.config["TESTING"] = True
    custom_node_dir = tmp_path / "custom_nodes"
    custom_node_dir.mkdir(parents=True, exist_ok=True)
    flask_app.config["CUSTOM_NODE_UPLOAD_DIR"] = str(custom_node_dir)
    existing_sources = set(_app_module.node_registry.source_to_processor_ids.keys())
    yield flask_app

    new_sources = (
        set(_app_module.node_registry.source_to_processor_ids.keys()) - existing_sources
    )
    for source in list(new_sources):
        _app_module.node_registry.unregister_source(source)


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_png_bytes():
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


def _make_json_bytes():
    return json.dumps(
        {
            "OperatorName": "Administrator",
            "Patient Name": "01-GBS-Thorax_PA",
            "NIK": "01-GBS",
            "KVP": 70,
            "TubeCurrent": 8,
            "ExposureTime": 0.5,
            "Time": "250227155852 ",
            "Scale X": 104.31,
            "Scale Y": 103.25,
            "Birthdate": "1965-08-24",
            "Age": "60 Y",
            "Gender": "Male",
        }
    ).encode("utf-8")


def _make_valid_custom_node_bytes():
    return b"""
from app.processors.base_processor import ImageProcessor


class UploadedDemoProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.processor_id = "uploaded_demo"
        self.name = "Uploaded Demo"
        self.description = "Dynamically uploaded processor"
        self.parameters = {
            "metadata_file": {
                "type": "file",
                "required": False,
                "default": None,
                "file_filter": ".json",
                "file_id_field": "metadata_file_id",
                "filename_field": "metadata_filename",
                "resolved_data_field": "metadata_json",
                "resolved_filename_field": "metadata_filename",
                "upload_action": "json",
                "description": "Optional metadata upload",
            }
        }

    def process(self, image, **kwargs):
        return image
"""


def _make_invalid_custom_node_bytes():
    return b"class BrokenNode(ImageProcessor):\n    def __init__(self)\n        pass\n"


def _make_no_processor_bytes():
    return b"class NotAProcessor:\n    pass\n"


class TestGetNodes:
    def test_returns_list(self, client):
        resp = client.get("/api/nodes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 2

    def test_tiff_json_to_dicom_node_present(self, client):
        data = client.get("/api/nodes").get_json()
        tiff_node = next(node for node in data if node["id"] == "tiff_json_to_dicom")
        assert tiff_node["category"] == "Pipeline"
        assert tiff_node["name"] == "TIFF JSON to DICOM"
        assert tiff_node["inputs"] == 1
        assert tiff_node["outputs"] == 0
        assert "metadata_file" in tiff_node["parameters"]


class TestCustomNodes:
    def test_download_template(self, client):
        resp = client.get("/api/custom-nodes/template")
        assert resp.status_code == 200
        assert resp.mimetype == "text/x-python"
        assert b"class ExampleSingleInputProcessor" in resp.data
        assert b"upload_action" in resp.data

    def test_upload_custom_node_registers_new_processor(self, client, app):
        response = client.post(
            "/api/custom-nodes/upload",
            data={
                "file": (
                    io.BytesIO(_make_valid_custom_node_bytes()),
                    "../uploaded_demo.py",
                ),
                "kategori_grup": "Experimental",
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["status"] == "success"
        assert body["filename"] == "uploaded_demo.py"
        assert "uploaded_demo" in body["registered_node_ids"]

        saved_path = os.path.join(
            app.config["CUSTOM_NODE_UPLOAD_DIR"], "uploaded_demo.py"
        )
        assert os.path.isfile(saved_path)
        assert os.path.isfile(f"{saved_path}.meta.json")

        nodes = client.get("/api/nodes").get_json()
        uploaded_node = next(node for node in nodes if node["id"] == "uploaded_demo")
        assert uploaded_node["category"] == "Experimental"
        assert uploaded_node["name"] == "Uploaded Demo"

    def test_upload_custom_node_rejects_syntax_error_and_deletes_file(
        self, client, app
    ):
        response = client.post(
            "/api/custom-nodes/upload",
            data={
                "file": (
                    io.BytesIO(_make_invalid_custom_node_bytes()),
                    "broken_node.py",
                ),
                "kategori_grup": "Experimental",
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        body = response.get_json()
        assert body["error"] == "Custom node upload failed"
        assert (
            "expected ':'" in body["message"]
            or "invalid syntax" in body["message"].lower()
        )
        assert not os.path.exists(
            os.path.join(app.config["CUSTOM_NODE_UPLOAD_DIR"], "broken_node.py")
        )

    def test_upload_custom_node_rejects_missing_processor_class(self, client, app):
        response = client.post(
            "/api/custom-nodes/upload",
            data={
                "file": (io.BytesIO(_make_no_processor_bytes()), "not_a_processor.py"),
                "kategori_grup": "Experimental",
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400
        body = response.get_json()
        assert "No valid ImageProcessor subclasses" in body["message"]
        assert not os.path.exists(
            os.path.join(app.config["CUSTOM_NODE_UPLOAD_DIR"], "not_a_processor.py")
        )


class TestUpload:
    def test_upload_png(self, client):
        data = {"file": (io.BytesIO(_make_png_bytes()), "test.png")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "file_id" in body
        assert body["filename"] == "test.png"

    def test_upload_json_metadata(self, client):
        data = {"file": (io.BytesIO(_make_json_bytes()), "meta.json")}
        resp = client.post(
            "/api/upload-json", data=data, content_type="multipart/form-data"
        )
        assert resp.status_code == 200
        body = resp.get_json()
        assert "file_id" in body
        assert body["filename"] == "meta.json"

    def test_upload_json_rejects_invalid_payload(self, client):
        data = {"file": (io.BytesIO(b"not-json"), "meta.json")}
        resp = client.post(
            "/api/upload-json", data=data, content_type="multipart/form-data"
        )
        assert resp.status_code == 400
        assert "Invalid JSON" in resp.get_json()["error"]

    def test_upload_too_large_returns_json_413(self, client, app):
        original_limit = app.config.get("MAX_CONTENT_LENGTH")
        try:
            app.config["MAX_CONTENT_LENGTH"] = 64
            data = {"file": (io.BytesIO(_make_png_bytes()), "test.png")}
            resp = client.post(
                "/api/upload", data=data, content_type="multipart/form-data"
            )
            assert resp.status_code == 413
            body = resp.get_json()
            assert "too large" in body["error"].lower()
            assert body.get("max_content_length") == 64
        finally:
            app.config["MAX_CONTENT_LENGTH"] = original_limit


class TestExecutePipeline:
    def test_empty_body(self, client):
        resp = client.post("/api/execute-pipeline", json=None)
        assert resp.status_code == 400

    def test_no_nodes(self, client):
        resp = client.post("/api/execute-pipeline", json={"nodes": [], "edges": []})
        assert resp.status_code == 400

    def test_terminal_dicom_pipeline(self, client):
        image_upload = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(_make_png_bytes()), "test.png")},
            content_type="multipart/form-data",
        )
        image_file_id = image_upload.get_json()["file_id"]

        metadata_upload = client.post(
            "/api/upload-json",
            data={"file": (io.BytesIO(_make_json_bytes()), "meta.json")},
            content_type="multipart/form-data",
        )
        json_file_id = metadata_upload.get_json()["file_id"]

        pipeline = {
            "nodes": [
                {"id": "in1", "type": "input", "data": {"file_id": image_file_id}},
                {
                    "id": "dcm1",
                    "type": "tiff_json_to_dicom",
                    "data": {"json_file_id": json_file_id},
                },
            ],
            "edges": [{"source": "in1", "target": "dcm1"}],
        }

        resp = client.post("/api/execute-pipeline", json=pipeline)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert body["result"]["all_outputs"][0]["output_ext"] == ".dcm"
        assert body["result"]["all_outputs"][0]["output_type"] == "dicom"

        output_id = body["result"]["output_id"]
        download = client.get(f"/api/output/{output_id}")
        assert download.status_code == 200
        assert download.mimetype == "application/dicom"
        assert ".dcm" in download.headers.get("Content-Disposition", "")


class TestGetImage:
    def test_invalid_id_with_traversal(self, client):
        resp = client.get("/api/image/..etc..passwd")
        assert resp.status_code == 400

    def test_not_found(self, client):
        resp = client.get("/api/image/nonexistent-id")
        assert resp.status_code == 404

    def test_existing_image(self, client):
        upload = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(_make_png_bytes()), "test.png")},
            content_type="multipart/form-data",
        )
        file_id = upload.get_json()["file_id"]
        resp = client.get(f"/api/image/{file_id}")
        assert resp.status_code == 200


class TestGetOutput:
    def test_not_found(self, client):
        resp = client.get("/api/output/nonexistent-id")
        assert resp.status_code == 404
