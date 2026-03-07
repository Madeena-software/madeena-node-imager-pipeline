import { useEffect, useState } from 'react';
import api from '../services/api';

const NodePropertiesModal = ({
  isOpen,
  onClose,
  node,
  onUpdateNode,
  availableNodes,
  onUploadingChange,
}) => {
  const [parameters, setParameters] = useState({});
  const [nodeInfo, setNodeInfo] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  useEffect(() => {
    if (isOpen && node) {
      // Initialize parameters with current values or defaults
      setParameters(node.data.parameters || {});

      // Get node definition from available nodes
      const nodeDefinition = availableNodes.find((n) => n.id === node.data.nodeType);
      setNodeInfo(nodeDefinition);
    }
  }, [isOpen, node, availableNodes]);

  const handleParameterChange = (paramName, value) => {
    setParameters((prev) => ({
      ...prev,
      [paramName]: value,
    }));
  };

  const handleSave = () => {
    if (onUpdateNode && node) {
      onUpdateNode(node.id, parameters, {});
    }
    onClose();
  };

  const handleReset = () => {
    if (nodeInfo && nodeInfo.parameters) {
      const defaultParams = {};
      Object.entries(nodeInfo.parameters).forEach(([key, config]) => {
        defaultParams[key] = config.default;
      });
      setParameters(defaultParams);
    }
  };

  const renderParameterInput = (paramName, paramConfig) => {
    const value = parameters[paramName] ?? paramConfig.default ?? '';

    switch (paramConfig.type) {
      case 'number':
        return (
          <div className="parameter-input-group">
            <input
              type="number"
              value={value}
              min={paramConfig.min}
              max={paramConfig.max}
              step={paramConfig.step || 1}
              onChange={(e) => handleParameterChange(paramName, parseFloat(e.target.value) || 0)}
              className="parameter-input number-input"
            />
            {(paramConfig.min !== undefined || paramConfig.max !== undefined) && (
              <div className="parameter-range">
                Range: {paramConfig.min ?? 'No min'} - {paramConfig.max ?? 'No max'}
              </div>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div className="parameter-input-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={value}
                onChange={(e) => handleParameterChange(paramName, e.target.checked)}
                className="parameter-checkbox"
              />
              <span className="checkbox-text">{value ? 'Enabled' : 'Disabled'}</span>
            </label>
          </div>
        );

      case 'select':
        return (
          <div className="parameter-input-group">
            <select
              value={value}
              onChange={(e) => handleParameterChange(paramName, e.target.value)}
              className="parameter-input select-input"
            >
              {paramConfig.options?.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>
        );

      case 'string':
        return (
          <div className="parameter-input-group">
            <input
              type="text"
              value={value}
              onChange={(e) => handleParameterChange(paramName, e.target.value)}
              placeholder={paramConfig.placeholder || ''}
              className="parameter-input text-input"
            />
          </div>
        );

      case 'range':
        return (
          <div className="parameter-input-group">
            <input
              type="range"
              value={value}
              min={paramConfig.min || 0}
              max={paramConfig.max || 100}
              step={paramConfig.step || 1}
              onChange={(e) => handleParameterChange(paramName, parseFloat(e.target.value))}
              className="parameter-range-slider"
            />
            <div className="range-value">
              Value: {value} {paramConfig.unit || ''}
            </div>
          </div>
        );

      case 'color':
        return (
          <div className="parameter-input-group">
            <div className="color-input-wrapper">
              <input
                type="color"
                value={value}
                onChange={(e) => handleParameterChange(paramName, e.target.value)}
                className="parameter-color-input"
              />
              <input
                type="text"
                value={value}
                onChange={(e) => handleParameterChange(paramName, e.target.value)}
                placeholder="#FFFFFF"
                className="parameter-input color-text-input"
              />
            </div>
          </div>
        );

      default:
        return (
          <div className="parameter-input-group">
            <input
              type="text"
              value={value}
              onChange={(e) => handleParameterChange(paramName, e.target.value)}
              className="parameter-input text-input"
            />
          </div>
        );
    }
  };

  if (!isOpen || !node || !nodeInfo) return null;

  return (
    <div className="modal-overlay properties-modal-overlay">
      <div className="modal properties-modal">
        <div className="modal-header">
          <div className="node-header">
            <div
              className="node-type-indicator"
              style={{
                backgroundColor:
                  nodeInfo.type === 'input'
                    ? '#4caf50'
                    : nodeInfo.type === 'output'
                      ? '#f44336'
                      : '#007acc',
              }}
            ></div>
            <div>
              <h3>{nodeInfo.name} Properties</h3>
              <p className="node-description">{nodeInfo.description}</p>
            </div>
          </div>
          <button className="close-button" onClick={onClose} disabled={isUploading}>
            ×
          </button>
        </div>

        <div className="modal-content properties-content">
          <div className="node-info-section">
            <div className="info-item">
              <strong>Node ID:</strong> {node.id}
            </div>
            <div className="info-item">
              <strong>Type:</strong> {nodeInfo.type}
            </div>
            <div className="info-item">
              <strong>Inputs:</strong> {nodeInfo.inputs} | <strong>Outputs:</strong>{' '}
              {nodeInfo.outputs}
            </div>
          </div>

          {nodeInfo.parameters && Object.keys(nodeInfo.parameters).length > 0 ? (
            <div className="parameters-section">
              <h4>Parameters</h4>
              <div className="parameters-grid">
                {Object.entries(nodeInfo.parameters).map(([paramName, paramConfig]) => (
                  <div key={paramName} className="parameter-item">
                    <div className="parameter-header">
                      <label className="parameter-label">
                        {paramName.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                        {paramConfig.required && <span className="required-indicator">*</span>}
                      </label>
                      {paramConfig.description && (
                        <div className="parameter-description">{paramConfig.description}</div>
                      )}
                    </div>
                    {renderParameterInput(paramName, paramConfig)}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-parameters">
              <p>This node has no configurable parameters.</p>
            </div>
          )}

          {/* Special handling for input nodes */}
          {nodeInfo.type === 'input' && (
            <div className="input-node-section">
              <h4>Input File</h4>
              {node.data.filename ? (
                <div className="current-file">
                  <strong>Current file:</strong> {node.data.filename}
                  <div className="file-info">File ID: {node.data.file_id}</div>
                </div>
              ) : (
                <div className="no-file">No file selected.</div>
              )}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <div className="button-group">
            <button
              className="reset-button"
              onClick={handleReset}
              disabled={isUploading}
              title="Reset to default values"
            >
              Reset to Defaults
            </button>
            <button className="cancel-button" onClick={onClose} disabled={isUploading}>
              Cancel
            </button>
            <button className="save-button" onClick={handleSave} disabled={isUploading}>
              Apply Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NodePropertiesModal;
