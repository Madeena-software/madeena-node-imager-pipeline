import axios from 'axios';

// Determine API base URL dynamically:
// - If REACT_APP_API_URL is set, use it (explicit override)
// - If running via React dev server (default port 3000), talk to backend on :5000
// - Otherwise assume same-origin and use relative `/api` path so static builds work
const isDevServer = window.location.port === '3000' || window.location.hostname === 'localhost';
const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  (isDevServer ? `http://${window.location.hostname}:5000/api` : '/api');

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // 2 min — pipeline execution may be slow
});

// Response interceptor for consistent error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.message ||
      error.response?.data?.error ||
      error.message ||
      'Unknown error';
    const method = error.config?.method ? error.config.method.toUpperCase() : 'UNKNOWN';
    const url = error.config?.url || error.request?.responseURL || 'unknown-url';
    console.error(`[API] ${method} ${url} — ${message}`);
    return Promise.reject(error);
  }
);

const apiService = {
  /** Generic GET wrapper */
  get: (url) => api.get(url),

  /** Upload an image file via multipart form-data */
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  /** Upload JSON metadata for node-specific processing */
  uploadJson: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload-json', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /** Execute a processing pipeline */
  executePipeline: (pipelineData) => api.post('/execute-pipeline', pipelineData),

  /** Build a full image URL for a given file_id */
  imageUrl: (fileId) => `${API_BASE_URL}/image/${fileId}`,

  /** Build a preview thumbnail URL for a given file_id */
  previewUrl: (fileId) => `${API_BASE_URL}/preview/${fileId}`,

  /** Build an output artifact URL for a given output_id (supports npz and images) */
  outputUrl: (outputId) => `${API_BASE_URL}/output/${outputId}`,
};

export default apiService;
