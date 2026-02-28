import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

const ImagePreviewPanel = ({ nodes, processingStatus }) => {
  const [inputImageId, setInputImageId] = useState(null);
  const [outputImageIds, setOutputImageIds] = useState([]);
  const timestampRef = useRef(Date.now());

  // Get input image from nodes
  useEffect(() => {
    const inputNode = nodes.find(node => node.data.nodeType === 'input');
    if (inputNode?.data?.file_id) {
      setInputImageId(inputNode.data.file_id);
      timestampRef.current = Date.now(); // refresh cache on change
    } else {
      setInputImageId(null);
    }
  }, [nodes]);

  // Get all output images from processing status
  useEffect(() => {
    const outputs = processingStatus
      .filter(status => status.output_id)
      .map(status => status.output_id);
    setOutputImageIds(outputs);
    if (outputs.length) timestampRef.current = Date.now();
  }, [processingStatus]);

  if (!inputImageId && outputImageIds.length === 0) {
    return null;
  }

  const t = timestampRef.current;

  return (
    <div className="image-preview-panel">
      <h4>Image Preview</h4>
      
      <div className="preview-container">
        {inputImageId && (
          <div className="preview-item">
            <h5>Input Image</h5>
            <img 
              key={inputImageId}
              src={`${api.imageUrl(inputImageId)}?t=${t}`}
              alt="Input"
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}

        {outputImageIds.map((outputId, index) => (
          <div className="preview-item" key={outputId}>
            <h5>Output Image {outputImageIds.length > 1 ? `${index + 1}` : ''}</h5>
            <img 
              src={`${api.imageUrl(outputId)}?t=${t}`}
              alt={`Output ${index + 1}`}
              onError={(e) => {
                e.target.style.display = 'none';
              }}
            />
            <div className="preview-actions">
              <a
                href={api.imageUrl(outputId)}
                target="_blank"
                rel="noopener noreferrer"
                className="preview-button"
              >
                🔍 View Full Size
              </a>
              <a
                href={api.imageUrl(outputId)}
                download={`output_${index + 1}_${outputId}.png`}
                className="preview-button"
              >
                💾 Download
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ImagePreviewPanel;
