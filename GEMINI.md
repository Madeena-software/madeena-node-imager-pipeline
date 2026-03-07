# Gemini Project: Image Processing Pipeline App

This document provides a comprehensive overview of the Image Processing Pipeline App project, intended to be used as a context for interacting with the Gemini AI assistant.

## Project Overview

The project is a full-stack web application that provides a visual, node-based editor for creating and executing image processing pipelines. It is similar in style to Node-RED, but specifically designed for image processing workflows.

### Key Features

- **Visual Node Editor:** A drag-and-drop interface for building image processing pipelines.
- **Real-time Processing:** Live updates and progress feedback during pipeline execution.
- **Configurable Nodes:** Each processing node has a set of parameters that can be configured by the user.
- **Extensible Architecture:** New image processing nodes can be easily added to the backend.

### Architecture

- **Frontend:** A React application built with `create-react-app`. It uses the `reactflow` library for the node-based editor, `axios` for REST API communication, and `socket.io-client` for real-time updates via WebSockets.
- **Backend:** A Python Flask application that provides a REST API and WebSocket server. It uses `OpenCV` and `Pillow` for image processing.
- **Imager Pipeline:** A separate collection of Python scripts in the `imager-pipeline` directory. These scripts provide advanced image processing capabilities, including camera calibration and a complete X-ray image processing pipeline.

## Building and Running

### Backend

To set up and run the backend server:

1.  Navigate to the `backend` directory.
2.  Create and activate a Python virtual environment.
3.  Install the required dependencies: `pip install -r requirements.txt`
4.  Run the Flask server: `python app.py`

The backend will be available at `http://localhost:5000`.

### Frontend

To set up and run the frontend development server:

1.  Navigate to the `frontend` directory.
2.  Install the required dependencies: `npm install`
3.  Start the development server: `npm start`

The frontend will be available at `http://localhost:3000`.

### Running Tests

- **Backend:** `pytest`
- **Frontend:** `npm test`

## Development Conventions

### Backend

- **Testing:** `pytest` is used for testing. Tests are located in the `tests` directory.
- **Linting and Formatting:** `ruff` is used for linting and formatting. The configuration is in `pyproject.toml`.
- **Code Coverage:** `coverage.py` is used to measure code coverage.

### Frontend

- **Linting:** `eslint` is used for linting. The configuration is in `package.json`.
- **Testing:** React Testing Library is used for testing components.

## Imager Pipeline

The `imager-pipeline` directory contains a set of Python scripts for advanced image processing, particularly for X-ray images.

- **`complete_pipeline.py`:** A highly configurable script that orchestrates a complete X-ray image processing pipeline. It includes steps like denoising, flat-field correction, and contrast enhancement. It can be accelerated with a GPU.
- **`camera_calibration.py`:** A script for calibrating a camera to correct for fish-eye lens distortion. It generates a calibration file that can be used by the `complete_pipeline.py` script.
- **Other Scripts:** The directory also contains other scripts for tasks like wavelet denoising and replicating ImageJ functionality.

These scripts appear to be a separate but related project that can be used in conjunction with the main application to provide advanced image processing capabilities.
