import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import json
import uuid
from werkzeug.utils import secure_filename
from app.pipeline_executor import PipelineExecutor
from app.node_registry import NodeRegistry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24).hex())

# Use absolute paths for upload and output folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(BASE_DIR, 'outputs')

# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
node_registry = NodeRegistry()
pipeline_executor = PipelineExecutor(socketio)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

@app.route('/api/nodes', methods=['GET'])
def get_available_nodes():
    """Get all available image processing nodes"""
    return jsonify(node_registry.get_all_nodes())

@app.route('/api/upload', methods=['POST'])
def upload_image():
    """Upload an image file"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Expanded list of supported image formats
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico', '.jfif')
    
    if file and file.filename and '.' in file.filename:
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        
        if f'.{file_extension}' in allowed_extensions:
            file_id = str(uuid.uuid4())
            new_filename = f"{file_id}.{file_extension}"
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(filepath)
            
            return jsonify({
                'file_id': file_id,
                'filename': filename,
                'filepath': filepath
            })
    
    return jsonify({'error': f'Invalid file type. Supported formats: {", ".join(allowed_extensions)}'}), 400

@app.route('/api/execute-pipeline', methods=['POST'])
def execute_pipeline():
    """Execute an image processing pipeline"""
    try:
        pipeline_data = request.json
        if not pipeline_data:
            return jsonify({'status': 'error', 'message': 'No pipeline data provided'}), 400
        
        nodes = pipeline_data.get('nodes', [])
        edges = pipeline_data.get('edges', [])
        
        if not nodes:
            return jsonify({'status': 'error', 'message': 'Pipeline has no nodes'}), 400
        
        logger.info(f"Executing pipeline with {len(nodes)} nodes and {len(edges)} edges")
        
        # Execute pipeline
        result = pipeline_executor.execute(nodes, edges)
        
        return jsonify({
            'status': 'success',
            'result': result
        })
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/image/<file_id>')
def get_image(file_id):
    """Serve processed images"""
    import cv2
    
    # Validate file_id to prevent path traversal
    if not file_id or '/' in file_id or '\\' in file_id or '..' in file_id:
        return jsonify({'error': 'Invalid file ID'}), 400
    
    # Try uploads folder first, then outputs
    extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'ico', 'jfif']
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for ext in extensions:
            filepath = os.path.join(folder, f"{file_id}.{ext}")
            if os.path.exists(filepath):
                # For TIFF files, convert to PNG for browser compatibility
                if ext in ['tiff', 'tif']:
                    image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
                    if image is not None:
                        temp_png = os.path.join(app.config['OUTPUT_FOLDER'], f"{file_id}_display.png")
                        cv2.imwrite(temp_png, image)
                        return send_file(temp_png, mimetype='image/png')
                
                return send_file(filepath)
    
    return jsonify({'error': 'Image not found'}), 404

@app.route('/api/preview/<file_id>')
def get_preview(file_id):
    """Serve thumbnail preview of images"""
    import cv2
    
    # Try to find the image
    extensions = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'tif', 'webp', 'ico', 'jfif']
    for folder in [app.config['UPLOAD_FOLDER'], app.config['OUTPUT_FOLDER']]:
        for ext in extensions:
            filepath = os.path.join(folder, f"{file_id}.{ext}")
            if os.path.exists(filepath):
                # Create thumbnail
                image = cv2.imread(filepath, cv2.IMREAD_UNCHANGED)
                if image is not None:
                    # Resize to thumbnail size (max 150px)
                    h, w = image.shape[:2]
                    max_size = 150
                    if max(h, w) > max_size:
                        scale = max_size / max(h, w)
                        new_w = int(w * scale)
                        new_h = int(h * scale)
                        thumbnail = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
                    else:
                        thumbnail = image
                    
                    # Save thumbnail as PNG (works for all formats including TIFF)
                    temp_path = os.path.join(app.config['OUTPUT_FOLDER'], f"thumb_{file_id}.png")
                    cv2.imwrite(temp_path, thumbnail)
                    return send_file(temp_path, mimetype='image/png')
    
    return jsonify({'error': 'Image not found'}), 404

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')
    emit('connected', {'data': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)