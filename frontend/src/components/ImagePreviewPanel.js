import React, { useState, useEffect } from 'react';

const ImagePreviewPanel = ({ nodes, processingStatus }) => {
  const [inputImageId, setInputImageId] = useState(null);
  const [outputImageIds, setOutputImageIds] = useState([]);

  // Get input image from nodes
  useEffect(() => {
    const inputNode = nodes.find(node => node.data.nodeType === 'input');
    if (inputNode && inputNode.data.file_id) {
      setInputImageId(inputNode.data.file_id);
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
  }, [processingStatus]);

  if (!inputImageId && outputImageIds.length === 0) {
    return null;
  }

  return (
    <div className="image-preview-panel">
      <h4>Image Preview</h4>
      
      <div className="preview-container">
        {inputImageId && (
          <div className="preview-item">
            <h5>Input Image</h5>
            <img 
              key={inputImageId}
              src={`http://localhost:5000/api/image/${inputImageId}?t=${Date.now()}`}
              alt="Input"
              onError={(e) => {
                console.error('Failed to load input image:', inputImageId);
                e.target.style.display = 'none';
              }}
            />
          </div>
        )}

        {outputImageIds.map((outputId, index) => (
          <div className="preview-item" key={outputId}>
            <h5>Output Image {outputImageIds.length > 1 ? `${index + 1}` : ''}</h5>
            <img 
              src={`http://localhost:5000/api/image/${outputId}?t=${Date.now()}`}
              alt={`Output ${index + 1}`}
              onError={(e) => {
                console.error('Failed to load output image:', outputId);
                e.target.style.display = 'none';
              }}
            />
            <div className="preview-actions">
              <a
                href={`http://localhost:5000/api/image/${outputId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="preview-button"
              >
                🔍 View Full Size
              </a>
              <a
                href={`http://localhost:5000/api/image/${outputId}`}
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
