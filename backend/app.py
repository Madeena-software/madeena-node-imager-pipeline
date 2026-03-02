"""Flask application entry point for the Image Processing Pipeline API."""

import atexit
import logging
import os
import shutil
import signal
import subprocess
import uuid

import cv2
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from app.node_registry import NodeRegistry
from app.pipeline_executor import PipelineExecutor
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

app = Flask(__name__)
app.config.from_object(_config)

# CORS — restrict in production via CORS_ORIGINS env var
CORS(app, resources={r"/api/*": {"origins": _config.CORS_ORIGINS}})
socketio = SocketIO(app, cors_allowed_origins=_config.CORS_ORIGINS)

# Components
node_registry = NodeRegistry()
pipeline_executor = PipelineExecutor(socketio)

# Ensure runtime directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = _config.ALLOWED_EXTENSIONS
_frontend_process: subprocess.Popen | None = None


def _allowed_file(filename: str) -> bool:
    """Return True if *filename* has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _find_image(file_id: str, *folders: str) -> str | None:
    """Search *folders* for an image matching *file_id*. Return path or None."""
    for folder in folders:
        for ext in ALLOWED_EXTENSIONS:
            path = os.path.join(folder, f"{file_id}.{ext}")
            if os.path.exists(path):
                return path
    return None


def _validate_file_id(file_id: str) -> bool:
    """Basic path-traversal prevention."""
    return bool(file_id) and not any(ch in file_id for ch in ("/", "\\", ".."))


def _should_start_frontend() -> bool:
    """Return True when frontend auto-start is enabled."""
    value = os.environ.get("AUTO_START_FRONTEND", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _frontend_dir() -> str:
    """Return absolute path to frontend directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


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

    filename = secure_filename(file.filename)
    extension = filename.rsplit(".", 1)[1].lower()
    file_id = str(uuid.uuid4())
    new_filename = f"{file_id}.{extension}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], new_filename)
    file.save(filepath)

    logger.info("Uploaded %s as %s", filename, file_id)
    return jsonify({"file_id": file_id, "filename": filename, "filepath": filepath})


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

    logger.info("Executing pipeline with %d nodes and %d edges", len(nodes), len(edges))

    try:
        result = pipeline_executor.execute(nodes, edges)
        return jsonify({"status": "success", "result": result})
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc, exc_info=True)
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/api/image/<file_id>")
def get_image(file_id):
    """Serve a full-size image by *file_id*."""
    if not _validate_file_id(file_id):
        return jsonify({"error": "Invalid file ID"}), 400

    filepath = _find_image(
        file_id, app.config["UPLOAD_FOLDER"], app.config["OUTPUT_FOLDER"]
    )
    if not filepath:
        return jsonify({"error": "Image not found"}), 404

    # Convert TIFF → PNG for browser compatibility
    if filepath.lower().endswith((".tiff", ".tif")):
        image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
        if image is not None:
            temp_png = os.path.join(
                app.config["OUTPUT_FOLDER"], f"{file_id}_display.png"
            )
            cv2.imwrite(temp_png, image)
            return send_file(temp_png, mimetype="image/png")

    return send_file(filepath)


@app.route("/api/preview/<file_id>")
def get_preview(file_id):
    """Serve a thumbnail preview (max 150 px) of an image."""
    if not _validate_file_id(file_id):
        return jsonify({"error": "Invalid file ID"}), 400

    filepath = _find_image(
        file_id, app.config["UPLOAD_FOLDER"], app.config["OUTPUT_FOLDER"]
    )
    if not filepath:
        return jsonify({"error": "Image not found"}), 404

    image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
    if image is None:
        return jsonify({"error": "Cannot read image"}), 500

    max_size = 150
    h, w = image.shape[:2]
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        image = cv2.resize(
            image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA
        )

    temp_path = os.path.join(app.config["OUTPUT_FOLDER"], f"thumb_{file_id}.png")
    cv2.imwrite(temp_path, image)
    return send_file(temp_path, mimetype="image/png")


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
    if path and os.path.exists(os.path.join(_BUILD_DIR, path)):
        return send_from_directory(_BUILD_DIR, path)
    return send_from_directory(_BUILD_DIR, "index.html")


# ---------------------------------------------------------------------------
# SocketIO events
# ---------------------------------------------------------------------------


@socketio.on("connect")
def handle_connect():
    logger.info("Client connected")
    emit("connected", {"data": "Connected to server"})


@socketio.on("disconnect")
def handle_disconnect():
    logger.info("Client disconnected")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if (
        not app.config.get("DEBUG", False)
        or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        _start_frontend_dev_server()

    socketio.run(
        app,
        debug=app.config.get("DEBUG", False),
        use_reloader=False,
        host=_config.HOST,
        port=_config.PORT,
    )
