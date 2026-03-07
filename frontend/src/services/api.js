import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || `http://${window.location.hostname}:5000/api`;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120_000, // 2 min — pipeline execution may be slow
});

// Response interceptor for consistent error logging
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.message || error.response?.data?.error || error.message;
    console.error(`[API] ${error.config?.method?.toUpperCase()} ${error.config?.url} — ${message}`);
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
