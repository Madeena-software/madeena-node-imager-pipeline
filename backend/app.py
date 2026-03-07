"""Flask application entry point for the Image Processing Pipeline API."""

import atexit
import io
import json
import logging
import os
import shutil
import signal
import subprocess
import time
import uuid

import cv2
import numpy as np
from flask import Flask, jsonify, request, send_file, send_from_directory, session
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from app.node_registry import NodeRegistry
from app.pipeline_executor import PipelineExecutor
from app.in_memory_storage import storage
from config import get_config

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App factory helpers
# ---------------------------------------------------------------------------

_config = get_config()

app = Flask(__name__, static_folder=None)
app.config.from_object(_config)

# CORS — restrict in production via CORS_ORIGINS env var
CORS(app, resources={r"/api/*": {"origins": _config.CORS_ORIGINS}})
socketio_async_mode = os.environ.get("SOCKETIO_ASYNC_MODE")
if not socketio_async_mode and os.name == "nt":
    socketio_async_mode = "threading"

socketio_kwargs = {
    "cors_allowed_origins": _config.CORS_ORIGINS,
}
if socketio_async_mode:
    socketio_kwargs["async_mode"] = socketio_async_mode

socketio = SocketIO(app, **socketio_kwargs)

# Components
node_registry = NodeRegistry()
pipeline_executor = PipelineExecutor(socketio)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = _config.ALLOWED_EXTENSIONS
_frontend_process: subprocess.Popen | None = None


def _allowed_file(filename: str) -> bool:
    """Return True if *filename* has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_file_id(file_id: str) -> bool:
    """Basic path-traversal prevention."""
    return bool(file_id) and not any(ch in file_id for ch in ("/", "\\", ".."))


def _get_session_id() -> str:
    """Return a stable session id for HTTP requests."""
    session_id = session.get("_pipeline_session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        session["_pipeline_session_id"] = session_id
    return session_id


def _allowed_json_file(filename: str) -> bool:
    """Return True if *filename* has a .json extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "json"


def _format_bytes(byte_count: int) -> str:
    """Format bytes as a readable string (B/KB/MB/GB)."""
    value = float(max(0, byte_count))
    units = ["B", "KB", "MB", "GB"]
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024.0
        unit_index += 1
    return f"{value:.1f} {units[unit_index]}"


def _should_start_frontend() -> bool:
    """Return True when frontend auto-start is enabled."""
    value = os.environ.get("AUTO_START_FRONTEND", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _frontend_dir() -> str:
    """Return absolute path to frontend directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


def _frontend_build_index() -> str:
    """Return path to frontend build index.html."""
    return os.path.join(_BUILD_DIR, "index.html")


def _has_frontend_build() -> bool:
    """Return True when frontend build output exists."""
    return os.path.isfile(_frontend_build_index())


def _should_auto_build_frontend() -> bool:
    """Return True when frontend auto-build is enabled."""
    value = os.environ.get("AUTO_BUILD_FRONTEND", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _ensure_frontend_build() -> None:
    """Ensure frontend build exists for integrated backend+frontend serving."""
    if _has_frontend_build():
        logger.info("Frontend build found: %s", _frontend_build_index())
        return

    logger.warning("Frontend build not found at %s", _frontend_build_index())

    if not _should_auto_build_frontend():
        logger.warning(
            "AUTO_BUILD_FRONTEND is disabled. Run 'npm run build' in frontend directory."
        )
        return

    frontend_dir = _frontend_dir()
    npm_executable = shutil.which("npm.cmd") or shutil.which("npm")

    if not os.path.isdir(frontend_dir):
        logger.warning("Frontend directory not found: %s", frontend_dir)
        return

    if not npm_executable:
        logger.warning("npm executable not found in PATH, cannot auto-build frontend")
        return

    logger.info("Running frontend build check: npm run build")
    try:
        subprocess.run(
            [npm_executable, "run", "build"],
            cwd=frontend_dir,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error("Frontend build failed with exit code %s", exc.returncode)
        return

    if _has_frontend_build():
        logger.info("Frontend build created successfully")
    else:
        logger.warning("Frontend build command finished but build output was not found")


def _stop_frontend_dev_server() -> None:
    """Stop frontend dev server process if it is running."""
    global _frontend_process

    if not _frontend_process or _frontend_process.poll() is not None:
        return

    logger.info("Stopping frontend dev server (pid=%s)", _frontend_process.pid)

    try:
        if os.name == "nt":
            _frontend_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            _frontend_process.terminate()
        _frontend_process.wait(timeout=5)
    except Exception:
        _frontend_process.kill()
    finally:
        _frontend_process = None


def _start_frontend_dev_server() -> None:
    """Start `npm start` from frontend directory for one-command local dev."""
    global _frontend_process

    if not _should_start_frontend():
        logger.info(
            "Frontend auto-start disabled (AUTO_START_FRONTEND=%s)",
            os.environ.get("AUTO_START_FRONTEND"),
        )
        return

    frontend_dir = _frontend_dir()
    if not os.path.isdir(frontend_dir):
        logger.warning(
            "Frontend folder not found, skipping auto-start: %s", frontend_dir
        )
        return

    npm_executable = shutil.which("npm.cmd") or shutil.which("npm")
    if not npm_executable:
        logger.warning("npm executable not found in PATH, skipping frontend auto-start")
        return

    popen_kwargs: dict = {"cwd": frontend_dir}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    _frontend_process = subprocess.Popen([npm_executable, "start"], **popen_kwargs)
    atexit.register(_stop_frontend_dev_server)
    logger.info("Frontend dev server started (pid=%s)", _frontend_process.pid)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(_error):
    """Return JSON response when uploaded file exceeds MAX_CONTENT_LENGTH."""
    max_bytes = int(app.config.get("MAX_CONTENT_LENGTH") or 0)
    max_human = _format_bytes(max_bytes) if max_bytes else "configured limit"
    return (
        jsonify(
            {
                "error": f"Uploaded file is too large. Max allowed size is {max_human}.",
                "message": f"Uploaded file is too large. Max allowed size is {max_human}.",
                "max_content_length": max_bytes,
            }
        ),
        413,
    )


@app.route("/api/nodes", methods=["GET"])
def get_available_nodes():
    """Return metadata for every available processing node."""
    return jsonify(node_registry.get_all_nodes())


@app.route("/api/upload", methods=["POST"])
def upload_image():
    """Upload an image file and return its unique file_id."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_file(file.filename):
        return (
            jsonify(
                {
                    "error": f"Invalid file type. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                }
            ),
            400,
        )

    in_memory_file = file.read()
    np_image = np.frombuffer(in_memory_file, np.uint8)
    img = cv2.imdecode(np_image, cv2.IMREAD_UNCHANGED)

    if img is None:
        return jsonify({"error": "Cannot read image"}), 500

    session_id = _get_session_id()
    file_id = str(uuid.uuid4())
    storage.put(session_id, file_id, img)

    logger.info("Uploaded %s as %s for session %s", file.filename, file_id, session_id)
    return jsonify({"file_id": file_id, "filename": file.filename})


@app.route("/api/upload-json", methods=["POST"])
def upload_json_metadata():
    """Upload a JSON metadata file and return its unique file_id."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    if not _allowed_json_file(file.filename):
        return jsonify({"error": "Invalid file type. Supported: .json"}), 400

    try:
        file_bytes = file.read()
        metadata = json.loads(file_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({"error": "Invalid JSON file"}), 400

    if not isinstance(metadata, dict):
        return jsonify({"error": "JSON metadata must be an object"}), 400

    session_id = _get_session_id()
    file_id = str(uuid.uuid4())
    storage.put(
        session_id,
        file_id,
        {
            "kind": "json_metadata",
            "data": metadata,
            "filename": secure_filename(file.filename),
        },
    )

    logger.info(
        "Uploaded metadata %s as %s for session %s", file.filename, file_id, session_id
    )
    return jsonify({"file_id": file_id, "filename": secure_filename(file.filename)})


@app.route("/api/execute-pipeline", methods=["POST"])
def execute_pipeline():
    """Execute an image processing pipeline described by nodes & edges."""
    pipeline_data = request.get_json(silent=True)
    if not pipeline_data:
        return jsonify({"status": "error", "message": "No pipeline data provided"}), 400

    nodes = pipeline_data.get("nodes", [])
    edges = pipeline_data.get("edges", [])

    if not nodes:
        return jsonify({"status": "error", "message": "Pipeline has no nodes"}), 400

    session_id = _get_session_id()
    logger.info(
        "Executing pipeline with %d nodes and %d edges for session %s",
        len(nodes),
        len(edges),
        session_id,
    )

    try:
        result = pipeline_executor.execute(nodes, edges, session_id)
        return jsonify({"status": "success", "result": result})
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/image/<file_id>")
def get_image(file_id):
    """Serve a full-size image by *file_id*."""
    if not _validate_file_id(file_id):
        return jsonify({"error": "Invalid file ID"}), 400

    image = storage.get(_get_session_id(), file_id)
    if image is None or not isinstance(image, np.ndarray):
        return jsonify({"error": "Image not found"}), 404

    success, encoded = cv2.imencode(".png", image)
    if not success:
        return jsonify({"error": "Cannot encode image"}), 500

    return send_file(io.BytesIO(encoded.tobytes()), mimetype="image/png")


@app.route("/api/preview/<file_id>")
def get_preview(file_id):
    """Serve a thumbnail preview (max 150 px) of an image."""
    if not _validate_file_id(file_id):
        return jsonify({"error": "Invalid file ID"}), 400

    image = storage.get(_get_session_id(), file_id)
    if image is None or not isinstance(image, np.ndarray):
        return jsonify({"error": "Image not found"}), 404

    max_size = 150
    h, w = image.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        image = cv2.resize(
            image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
        )

    success, encoded = cv2.imencode(".png", image)
    if not success:
        return jsonify({"error": "Cannot encode image preview"}), 500

    return send_file(io.BytesIO(encoded.tobytes()), mimetype="image/png")


@app.route("/api/output/<file_id>")
def get_output_file(file_id):
    """Serve output artifacts (image or non-image, e.g. .npz) by output_id."""
    if not _validate_file_id(file_id):
        return jsonify({"error": "Invalid file ID"}), 400

    data = storage.get(_get_session_id(), file_id)
    if data is None:
        return jsonify({"error": "Output file not found"}), 404

    if isinstance(data, np.ndarray):
        success, encoded = cv2.imencode(".png", data)
        if not success:
            return jsonify({"error": "Cannot encode image"}), 500
        return send_file(
            io.BytesIO(encoded.tobytes()),
            mimetype="image/png",
            as_attachment=True,
            download_name=f"{file_id}.png",
        )

    if isinstance(data, dict) and "content" in data:
        download_name = (
            data.get("download_name") or f"{file_id}{data.get('output_ext', '.bin')}"
        )
        return send_file(
            io.BytesIO(data["content"]),
            mimetype=data.get("mimetype", "application/octet-stream"),
            as_attachment=True,
            download_name=download_name,
        )

    return jsonify({"error": "Unsupported output type"}), 500


# ---------------------------------------------------------------------------
# Frontend static files (serve React build)
# ---------------------------------------------------------------------------

_BUILD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "frontend", "build")
)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    """Serve React build files or fall back to index.html for client-side routing."""
    if not _has_frontend_build():
        return (
            "Frontend build not found. Run `npm run build` in the frontend directory "
            "or enable AUTO_BUILD_FRONTEND=1.",
            503,
        )

    if path and os.path.exists(os.path.join(_BUILD_DIR, path)):
        return send_from_directory(_BUILD_DIR, path)
    return send_from_directory(_BUILD_DIR, "index.html")


# ---------------------------------------------------------------------------
# SocketIO events
# ---------------------------------------------------------------------------


@socketio.on("connect")
def handle_connect(auth):
    logger.info(f"Client connected with session ID: {request.sid}")
    emit("connected", {"data": "Connected to server"})


@socketio.on("disconnect")
def handle_disconnect():
    logger.info(f"Client disconnected, cleaning up session: {request.sid}")
    storage.destroy_session_cache(request.sid)


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _ensure_frontend_build()

    if (
        not app.config.get("DEBUG", False)
        or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        _start_frontend_dev_server()

    # Reduce werkzeug logging noise and print a single, explicit startup line
    try:
        import werkzeug

        logging.getLogger("werkzeug").setLevel(logging.WARNING)
    except Exception:
        # If werkzeug is not available or the import fails, continue silently
        pass

    # Print a concise startup message showing only the chosen host and port
    logger.info("Server available at http://%s:%s", _config.HOST, _config.PORT)

    socketio.run(
        app,
        debug=app.config.get("DEBUG", False),
        use_reloader=False,
        host=_config.HOST,
        port=_config.PORT,
    )
