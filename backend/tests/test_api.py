"""Tests for the Flask API routes — upload, node listing, pipeline execution."""

import importlib.util
import io
import os
import sys

import cv2
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We need to import the app *after* setting env vars
os.environ.setdefault("FLASK_ENV", "testing")

# app.py is shadowed by the app/ package, so load it by file path
_app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
_spec = importlib.util.spec_from_file_location("app_entry", _app_path)
_app_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_app_module)
flask_app = _app_module.app


@pytest.fixture()
def app(tmp_path):
    flask_app.config["TESTING"] = True
    flask_app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    flask_app.config["OUTPUT_FOLDER"] = str(tmp_path / "outputs")
    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(flask_app.config["OUTPUT_FOLDER"], exist_ok=True)

    # Also make the pipeline_executor look at the same temp dirs
    _app_module.pipeline_executor.base_dir = str(tmp_path)

    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_png_bytes():
    """Return raw PNG bytes for a tiny image."""
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    return buf.tobytes()


# ---------------------------------------------------------------------------
# GET /api/nodes
# ---------------------------------------------------------------------------

class TestGetNodes:
    def test_returns_list(self, client):
        resp = client.get("/api/nodes")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 2  # at least input + output + some processors

    def test_input_output_present(self, client):
        data = client.get("/api/nodes").get_json()
        ids = [n["id"] for n in data]
        assert "input" in ids
        assert "output" in ids


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_upload_png(self, client):
        data = {"file": (io.BytesIO(_make_png_bytes()), "test.png")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "file_id" in body
        assert "filename" in body

    def test_upload_no_file(self, client):
        resp = client.post("/api/upload", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_upload_bad_extension(self, client):
        data = {"file": (io.BytesIO(b"not an image"), "test.txt")}
        resp = client.post("/api/upload", data=data, content_type="multipart/form-data")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/execute-pipeline
# ---------------------------------------------------------------------------

class TestExecutePipeline:
    def test_empty_body(self, client):
        resp = client.post("/api/execute-pipeline", json=None)
        assert resp.status_code == 400

    def test_no_nodes(self, client):
        resp = client.post("/api/execute-pipeline", json={"nodes": [], "edges": []})
        assert resp.status_code == 400

    def test_simple_pipeline(self, client, app):
        # Upload an image first
        upload = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(_make_png_bytes()), "test.png")},
            content_type="multipart/form-data",
        )
        file_id = upload.get_json()["file_id"]

        pipeline = {
            "nodes": [
                {"id": "in1", "type": "input", "data": {"file_id": file_id}},
                {"id": "proc1", "type": "grayscale", "data": {}},
                {"id": "out1", "type": "output", "data": {"format": "png"}},
            ],
            "edges": [
                {"source": "in1", "target": "proc1"},
                {"source": "proc1", "target": "out1"},
            ],
        }
        resp = client.post("/api/execute-pipeline", json=pipeline)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert "output_id" in body["result"]


# ---------------------------------------------------------------------------
# GET /api/image/<file_id>
# ---------------------------------------------------------------------------

class TestGetImage:
    def test_invalid_id_with_traversal(self, client):
        # file_id containing '..' should be rejected
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
