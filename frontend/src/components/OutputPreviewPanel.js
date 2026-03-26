import { useEffect, useRef, useState } from 'react';
import api from '../services/api';

const OutputPreviewPanel = ({ nodes, processingStatus }) => {
  const [inputImageId, setInputImageId] = useState(null);
  const [outputImageIds, setOutputImageIds] = useState([]);
  const [expandedItems, setExpandedItems] = useState([]);
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
        timestampRef.current = Date.now();
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
        output_name: status.output_name,
      }));
    const outputKey = outputs.map((item) => `${item.output_id}:${item.output_ext}`).join('|');
    setOutputImageIds(outputs);
    if (outputKeyRef.current !== outputKey) {
      outputKeyRef.current = outputKey;
      if (outputs.length) {
        timestampRef.current = Date.now();
        // Auto-expand newly added outputs
        setExpandedItems((prev) => {
          const newIds = outputs.map((o) => o.output_id).filter((id) => !prev.includes(id));
          return newIds.length ? [...prev, ...newIds] : prev;
        });
      }
    }
  }, [processingStatus]);

  const toggleItem = (key) => {
    setExpandedItems((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  if (!inputImageId && outputImageIds.length === 0) {
    return null;
  }

  const t = timestampRef.current;

  // Build unified list
  const allItems = [
    ...(inputImageId ? [{ type: 'input', id: 'input', label: 'Input Image', ext: null }] : []),
    ...outputImageIds.map((o, i) => ({
      type: o.output_ext === '.npz' ? 'artifact' : 'image',
      id: o.output_id,
      label:
        o.output_name ||
        (o.output_ext === '.npz'
          ? `Calibration Artifact${outputImageIds.length > 1 ? ` ${i + 1}` : ''}`
          : `Output${outputImageIds.length > 1 ? ` ${i + 1}` : ''}`),
      ext: o.output_ext,
      output_id: o.output_id,
      index: i,
    })),
  ];

  return (
    <div className="image-preview-panel">
      <h4>
        Output Preview{' '}
        <span className="preview-panel-count">
          {allItems.length} item{allItems.length !== 1 ? 's' : ''}
        </span>
      </h4>

      <div className="output-list">
        {allItems.map((item) => {
          const isExpanded = expandedItems.includes(item.id);
          const isNpz = item.ext === '.npz';
          const isInput = item.type === 'input';

          return (
            <div className="output-list-item" key={item.id}>
              <button
                className={`output-list-header${isExpanded ? ' expanded' : ''}`}
                onClick={() => toggleItem(item.id)}
              >
                <span className={`output-type-icon ${item.type}`}>
                  {isInput ? '📥' : isNpz ? '📦' : '🖼️'}
                </span>
                <span className="output-item-label">{item.label}</span>
                {item.ext && <span className="output-item-ext">{item.ext}</span>}
                <span className="output-toggle-arrow">{isExpanded ? '▲' : '▼'}</span>
              </button>

              {isExpanded && (
                <div className="output-list-content">
                  {isInput ? (
                    <img
                      key={inputImageId}
                      src={`${api.imageUrl(inputImageId)}?t=${t}`}
                      alt="Input"
                      className="output-preview-img"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : isNpz ? (
                    <div className="npz-preview-content">
                      <div className="npz-icon-area">📊</div>
                      <div className="npz-details">
                        <div className="npz-title">NumPy Archive (.npz)</div>
                        <div className="npz-desc">
                          Camera calibration data — berisi matrix kalibrasi, koefisien distorsi, dan
                          parameter kalibrasi lainnya.
                        </div>
                      </div>
                      <a
                        href={api.outputUrl(item.output_id)}
                        download={`output_${item.index + 1}_${item.output_id}${item.ext}`}
                        className="preview-button"
                      >
                        💾 Download NPZ
                      </a>
                    </div>
                  ) : (
                    <>
                      <img
                        src={`${api.imageUrl(item.output_id)}?t=${t}`}
                        alt={item.label}
                        className="output-preview-img"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                      <div className="preview-actions">
                        <a
                          href={api.imageUrl(item.output_id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="preview-button"
                        >
                          🔍 View Full Size
                        </a>
                        <a
                          href={api.outputUrl(item.output_id)}
                          download={`output_${item.index + 1}_${item.output_id}${item.ext}`}
                          className="preview-button"
                        >
                          💾 Download
                        </a>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default OutputPreviewPanel;
