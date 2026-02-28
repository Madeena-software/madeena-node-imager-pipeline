import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export default {
  // Get available nodes
  get: (url) => api.get(url),
  
  // Upload image
  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    return api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  // Execute pipeline
  executePipeline: (pipelineData) => {
    return api.post('/execute-pipeline', pipelineData);
  },
};