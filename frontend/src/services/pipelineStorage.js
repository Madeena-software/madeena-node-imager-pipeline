class PipelineStorage {
  constructor() {
    this.storageKey = 'image_processing_pipelines';
  }

  // Get all saved pipelines
  getAllPipelines() {
    try {
      const pipelines = localStorage.getItem(this.storageKey);
      return pipelines ? JSON.parse(pipelines) : {};
    } catch (error) {
      console.error('Error loading pipelines:', error);
      return {};
    }
  }

  // Save a pipeline
  savePipeline(name, nodes, edges, metadata = {}) {
    try {
      const pipelines = this.getAllPipelines();
      const existing = pipelines[name];
      const pipeline = {
        name,
        nodes,
        edges,
        metadata: {
          createdAt: existing?.metadata?.createdAt || new Date().toISOString(),
          ...metadata,
          updatedAt: new Date().toISOString()
        }
      };

      pipelines[name] = pipeline;
      localStorage.setItem(this.storageKey, JSON.stringify(pipelines));
      return true;
    } catch (error) {
      console.error('Error saving pipeline:', error);
      return false;
    }
  }

  // Load a pipeline
  loadPipeline(name) {
    try {
      const pipelines = this.getAllPipelines();
      return pipelines[name] || null;
    } catch (error) {
      console.error('Error loading pipeline:', error);
      return null;
    }
  }

  // Delete a pipeline
  deletePipeline(name) {
    try {
      const pipelines = this.getAllPipelines();
      delete pipelines[name];
      localStorage.setItem(this.storageKey, JSON.stringify(pipelines));
      return true;
    } catch (error) {
      console.error('Error deleting pipeline:', error);
      return false;
    }
  }

  // Export pipeline to JSON file
  exportPipeline(name) {
    const pipeline = this.loadPipeline(name);
    if (!pipeline) return false;

    const dataStr = JSON.stringify(pipeline, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const objectUrl = URL.createObjectURL(dataBlob);

    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `${name}_pipeline.json`;
    link.click();
    URL.revokeObjectURL(objectUrl);
    
    return true;
  }

  // Import pipeline from JSON file
  importPipeline(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const pipeline = JSON.parse(e.target.result);
          if (
            !pipeline ||
            !Array.isArray(pipeline.nodes) ||
            !Array.isArray(pipeline.edges) ||
            typeof pipeline.name !== 'string'
          ) {
            reject(new Error('Invalid pipeline structure'));
            return;
          }
          resolve(pipeline);
        } catch (error) {
          reject(new Error('Invalid pipeline file'));
        }
      };
      reader.onerror = () => reject(new Error('Error reading file'));
      reader.readAsText(file);
    });
  }
}

const pipelineStorage = new PipelineStorage();

export default pipelineStorage;