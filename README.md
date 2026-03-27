# Image Processing Pipeline App

A Node-RED style visual editor for image processing workflows. Drag and drop image processing nodes, configure parameters, and execute pipelines in real-time.

## Features

- **Visual Node Editor**: Drag-and-drop interface similar to Node-RED
- **Real-time Processing**: Live updates during pipeline execution
- **Parameter Configuration**: Easy-to-use parameter panels for each node
- **Python Backend**: Leverage powerful Python image processing libraries
- **WebSocket Support**: Real-time progress updates
- **Modular Architecture**: Easy to add new image processing nodes

## Architecture

- **Frontend**: React + React Flow for the visual editor
- **Backend**: Python Flask with OpenCV and PIL for image processing
- **Communication**: REST API + WebSockets for real-time updates

### imager-pipeline Placement

Current recommendation:

- Keep `imager-pipeline/` as a standalone Python package focused on scientific/image-processing logic.
- Keep `backend/` as the API/orchestration layer that imports the package.

This separation improves modularity and testability:

- `imager-pipeline/`: reusable processing algorithms and calibration functions.
- `backend/`: request validation, execution graph orchestration, file I/O, and realtime API.

The backend supports explicit package path configuration via:

```dotenv
IMAGER_PIPELINE_DIR=/absolute/path/to/imager-pipeline
```

If omitted, it defaults to the repository sibling folder.

## Available Nodes

### Input/Output Nodes

- **Image Input**: Load image files
- **Image Output**: Save processed images

### Processing Nodes

- **Resize**: Change image dimensions with aspect ratio options
- **Blur**: Gaussian blur with configurable kernel size
- **Brightness**: Adjust brightness and contrast
- **Edge Detection**: Canny edge detection algorithm

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate  # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the Flask server:

```bash
python app.py
```

The backend will be available at `http://localhost:5000`

By default, running `python app.py` also auto-starts the frontend dev server (`npm start`) from `../frontend`.
To disable this behavior, set `AUTO_START_FRONTEND=0` before running.

When backend and frontend are run as one app, backend now checks `frontend/build/index.html` on startup.
If the build is missing, it will try `npm run build` automatically (disable with `AUTO_BUILD_FRONTEND=0`).

### Backend Environment Options

Add these in `backend/.env`:

```dotenv
# Image cropping parameters (pixels to crop from each side)
CROP_TOP=0
CROP_BOTTOM=0
CROP_LEFT=0
CROP_RIGHT=0

# Storage cleanup (prevents uploads/outputs from growing forever)
AUTO_CLEANUP_ENABLED=1
CLEANUP_INTERVAL_SECONDS=60
UPLOAD_RETENTION_HOURS=24
OUTPUT_RETENTION_HOURS=24
UPLOAD_MAX_FILES=1000
OUTPUT_MAX_FILES=2000
```

How it works:

- Crop node defaults use `CROP_TOP/BOTTOM/LEFT/RIGHT`.
- `GET /api/preview/<file_id>` and TIFF display no longer create temp files on disk.
- Cleanup runs periodically and removes old files + enforces max file counts in `backend/uploads` and `backend/outputs`.

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm start
```

The frontend will be available at `http://localhost:3000`

## Usage

1. **Upload an Image**: Use the file upload in the sidebar
2. **Add Nodes**: Drag nodes from the palette to the canvas
3. **Connect Nodes**: Draw connections between node handles
4. **Configure Parameters**: Click "Config" on nodes to set parameters
5. **Execute Pipeline**: Click "Execute Pipeline" to process the image
6. **View Results**: Check the status panel for results and download links

### Run backend from repository root

You can start the backend without first changing into the `backend/` directory. Two convenient options are provided:

- Using `make` (preferred if you have `make` installed):

```bash
make backend
```

- Or run the shipped wrapper script:

```bash
bash run-backend.sh
```

Both commands will prefer a virtual environment Python at `.venv/bin/python3` when present, otherwise they use the system `python3`.

## Adding New Processors

To add a new image processing node:

1. Create a new processor class in `backend/app/processors/basic_processors.py`:

```python
class YourProcessor(ImageProcessor):
    def __init__(self):
        super().__init__()
        self.name = "Your Processor"
        self.description = "Description of what it does"
        self.parameters = {
            "param_name": {"type": "number", "default": 10, "min": 1, "max": 100}
        }

    def process(self, image_path, **kwargs):
        image = self.load_image(image_path)
        # Your processing logic here
        return processed_image
```

2. Register it in `backend/app/node_registry.py`:

```python
from app.processors.basic_processors import YourProcessor

# In __init__ method:
self.processors = {
    # ... existing processors
    'your_processor': YourProcessor(),
}
```

## API Endpoints

- `GET /api/nodes` - Get available nodes
- `POST /api/upload` - Upload image file
- `POST /api/execute-pipeline` - Execute processing pipeline
- `GET /api/image/<file_id>` - Get processed image

## WebSocket Events

- `pipeline_progress` - Progress updates during execution
- `pipeline_error` - Error notifications

## Technologies Used

### Backend

- Flask (Web framework)
- OpenCV (Image processing)
- PIL/Pillow (Image handling)
- Flask-SocketIO (WebSocket support)

### Frontend

- React (UI framework)
- React Flow (Node-based editor)
- Axios (HTTP client)
- Socket.IO (WebSocket client)

## Project Structure

```
IPApp/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── app/
│   │   ├── base_processor.py     # Base processor class
│   │   ├── node_registry.py      # Node registry
│   │   ├── pipeline_executor.py  # Pipeline execution engine
│   │   └── processors/
│   │       └── basic_processors.py  # Image processing nodes
│   ├── uploads/              # Uploaded images
│   └── outputs/              # Processed images
└── frontend/
    ├── package.json          # Node.js dependencies
    ├── src/
    │   ├── App.js           # Main application component
    │   ├── components/      # React components
    │   └── services/        # API and socket services
    └── public/
        └── index.html       # HTML template
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add your image processing nodes
4. Test your changes
5. Submit a pull request

## License

MIT License
