import React, { useState, useEffect } from 'react';
import pipelineStorage from '../services/pipelineStorage';

const SaveLoadModal = ({ isOpen, onClose, onSave, onLoad, currentPipeline }) => {
  const [mode, setMode] = useState('save'); // 'save' or 'load'
  const [pipelineName, setPipelineName] = useState('');
  const [savedPipelines, setSavedPipelines] = useState({});
  const [selectedPipeline, setSelectedPipeline] = useState('');

  useEffect(() => {
    if (isOpen) {
      setSavedPipelines(pipelineStorage.getAllPipelines());
    }
  }, [isOpen]);

  const handleSave = () => {
    if (!pipelineName.trim()) {
      alert('Please enter a pipeline name');
      return;
    }

    const success = pipelineStorage.savePipeline(
      pipelineName.trim(),
      currentPipeline.nodes,
      currentPipeline.edges,
      { description: 'User saved pipeline' }
    );

    if (success) {
      onSave(pipelineName.trim());
      onClose();
      setPipelineName('');
    } else {
      alert('Failed to save pipeline');
    }
  };

  const handleLoad = () => {
    if (!selectedPipeline) {
      alert('Please select a pipeline to load');
      return;
    }

    const pipeline = pipelineStorage.loadPipeline(selectedPipeline);
    if (pipeline) {
      onLoad(pipeline);
      onClose();
    } else {
      alert('Failed to load pipeline');
    }
  };

  const handleDelete = (name) => {
    if (window.confirm(`Are you sure you want to delete "${name}"?`)) {
      pipelineStorage.deletePipeline(name);
      setSavedPipelines(pipelineStorage.getAllPipelines());
    }
  };

  const handleExport = (name) => {
    pipelineStorage.exportPipeline(name);
  };

  const handleImport = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    pipelineStorage.importPipeline(file)
      .then(pipeline => {
        const name = pipeline.name || file.name.replace('.json', '');
        pipelineStorage.savePipeline(name, pipeline.nodes, pipeline.edges, pipeline.metadata);
        setSavedPipelines(pipelineStorage.getAllPipelines());
        alert(`Pipeline "${name}" imported successfully`);
      })
      .catch(error => {
        alert('Failed to import pipeline: ' + error.message);
      });
    
    event.target.value = ''; // Reset file input
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h3>Pipeline Management</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="modal-tabs">
          <button 
            className={mode === 'save' ? 'tab active' : 'tab'}
            onClick={() => setMode('save')}
          >
            Save Pipeline
          </button>
          <button 
            className={mode === 'load' ? 'tab active' : 'tab'}
            onClick={() => setMode('load')}
          >
            Load Pipeline
          </button>
        </div>

        <div className="modal-content">
          {mode === 'save' && (
            <div className="save-section">
              <label>Pipeline Name:</label>
              <input
                type="text"
                value={pipelineName}
                onChange={(e) => setPipelineName(e.target.value)}
                placeholder="Enter pipeline name..."
                className="pipeline-input"
              />
              <div className="button-group">
                <button className="save-button" onClick={handleSave}>
                  Save Pipeline
                </button>
              </div>
            </div>
          )}

          {mode === 'load' && (
            <div className="load-section">
              <div className="import-section">
                <label htmlFor="import-file">Import Pipeline:</label>
                <input
                  id="import-file"
                  type="file"
                  accept=".json"
                  onChange={handleImport}
                  className="file-input"
                />
              </div>

              <div className="pipeline-list">
                <h4>Saved Pipelines:</h4>
                {Object.keys(savedPipelines).length === 0 ? (
                  <p className="no-pipelines">No saved pipelines found</p>
                ) : (
                  Object.entries(savedPipelines).map(([name, pipeline]) => (
                    <div key={name} className="pipeline-item">
                      <div className="pipeline-info">
                        <input
                          type="radio"
                          name="selectedPipeline"
                          value={name}
                          checked={selectedPipeline === name}
                          onChange={(e) => setSelectedPipeline(e.target.value)}
                        />
                        <span className="pipeline-name">{name}</span>
                        <span className="pipeline-date">
                          {new Date(pipeline.metadata?.createdAt || Date.now()).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="pipeline-actions">
                        <button
                          className="export-button"
                          onClick={() => handleExport(name)}
                          title="Export pipeline"
                        >
                          📁
                        </button>
                        <button
                          className="delete-button"
                          onClick={() => handleDelete(name)}
                          title="Delete pipeline"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {Object.keys(savedPipelines).length > 0 && (
                <div className="button-group">
                  <button 
                    className="load-button" 
                    onClick={handleLoad}
                    disabled={!selectedPipeline}
                  >
                    Load Selected Pipeline
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SaveLoadModal;