import { useEffect, useRef, useState } from 'react';
import api from '../services/api';

const ImagePreviewPanel = ({ nodes, processingStatus }) => {
  const [inputImageId, setInputImageId] = useState(null);
  const [outputImageIds, setOutputImageIds] = useState([]);
  const timestampRef = useRef(Date.now());
  const inputKeyRef = useRef('');
  const outputKeyRef = useRef('');

  // Get input image from nodes
  useEffect(() => {
    const inputNode = nodes.find((node) => node.data.nodeType === 'input');
    if (inputNode?.data?.file_id) {
      setInputImageId(inputNode.data.file_id);
      if (inputKeyRef.current !== inputNode.data.file_id) {
        inputKeyRef.current = inputNode.data.file_id;
        timestampRef.current = Date.now(); // refresh cache only when input changes
      }
    } else {
      inputKeyRef.current = '';
      setInputImageId(null);
    }
  }, [nodes]);

  // Get all output images from processing status
  useEffect(() => {
    const outputs = processingStatus
      .filter((status) => status.output_id)
      .map((status) => ({
        output_id: status.output_id,
        output_ext: status.output_ext || (status.output_type === 'artifact' ? '.npz' : '.png'),
        output_type: status.output_type,
      }));
    const outputKey = outputs.map((item) => `${item.output_id}:${item.output_ext}`).join('|');
    setOutputImageIds(outputs);
    if (outputKeyRef.current !== outputKey) {
      outputKeyRef.current = outputKey;
      if (outputs.length) timestampRef.current = Date.now();
    }
  }, [processingStatus]);

  if (!inputImageId && outputImageIds.length === 0) {
    return null;
  }

  const t = timestampRef.current;

  return (
    <div className="image-preview-panel">
      <h4>Output Preview</h4>

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

        {outputImageIds.map((output, index) => (
          <div className="preview-item" key={output.output_id}>
            <h5>
              {output.output_ext === '.npz'
                ? `Calibration Artifact (.npz)${outputImageIds.length > 1 ? ` ${index + 1}` : ''}`
                : `Output Image${outputImageIds.length > 1 ? ` ${index + 1}` : ''}`}
            </h5>
            {output.output_ext === '.npz' && (
              <div style={{ color: '#666', fontSize: '12px', marginBottom: '8px' }}>
                Download this artifact to reuse in the Apply Camera Calibration node.
              </div>
            )}
            {output.output_ext !== '.npz' && (
              <img
                src={`${api.imageUrl(output.output_id)}?t=${t}`}
                alt={`Output ${index + 1}`}
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
            <div className="preview-actions">
              {output.output_ext !== '.npz' && (
                <a
                  href={api.imageUrl(output.output_id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="preview-button"
                >
                  🔍 View Full Size
                </a>
              )}
              <a
                href={api.outputUrl(output.output_id)}
                download={`output_${index + 1}_${output.output_id}${output.output_ext}`}
                className="preview-button"
              >
                {output.output_ext === '.npz' ? '💾 Download NPZ' : '💾 Download'}
              </a>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ImagePreviewPanel;
