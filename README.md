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