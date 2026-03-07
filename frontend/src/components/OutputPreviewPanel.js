import { useEffect, useRef, useState } from 'react';
import api from '../services/api';

const OutputPreviewPanel = ({ nodes, processingStatus }) => {
  const [inputImageIds, setInputImageIds] = useState([]);
  const [outputImageIds, setOutputImageIds] = useState([]);
  const [expandedItems, setExpandedItems] = useState(new Set());
  const timestampRef = useRef(Date.now());
  const inputKeyRef = useRef('');
  const outputKeyRef = useRef('');

  // Get input images from nodes
  useEffect(() => {
    const inputNodes = nodes.filter((node) => node.data.nodeType === 'input' && node.data.file_id);
    const newImageIds = inputNodes.map((node) => ({
      id: node.data.file_id,
      filename: node.data.filename || 'Input Image',
    }));
    const newIdsKey = newImageIds.map((img) => img.id).join(',');

    if (inputKeyRef.current !== newIdsKey) {
      inputKeyRef.current = newIdsKey;
      setInputImageIds(newImageIds);
      if (newImageIds.length) {
        timestampRef.current = Date.now();
      }
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
      }
    }
  }, [processingStatus]);

  const toggleItem = (key) => {
    setExpandedItems((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (inputImageIds.length === 0 && outputImageIds.length === 0) {
    return null;
  }

  const t = timestampRef.current;

  // Build unified list
  const allItems = [
    ...inputImageIds.map((img, i) => ({
      type: 'input',
      id: `input-${img.id}`,
      label: img.filename,
      file_id: img.id,
      ext: null,
      index: i,
    })),
    ...outputImageIds.map((o, i) => ({
      type: o.output_type === 'image' ? 'image' : 'artifact',
      id: o.output_id,
      label:
        o.output_name ||
        (o.output_ext === '.dcm'
          ? `DICOM Output${outputImageIds.length > 1 ? ` ${i + 1}` : ''}`
          : o.output_ext === '.npz'
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
          const isExpanded = expandedItems.has(item.id);
          const isInput = item.type === 'input';
          const isImage = item.type === 'image';
          const artifactLabel =
            item.ext === '.dcm'
              ? 'DICOM File (.dcm)'
              : item.ext === '.npz'
                ? 'NumPy Archive (.npz)'
                : `Artifact (${item.ext || 'file'})`;
          const artifactDescription =
            item.ext === '.dcm'
              ? 'Medical imaging output generated from the current pipeline image and uploaded JSON metadata.'
              : item.ext === '.npz'
                ? 'Camera calibration data — berisi matrix kalibrasi, koefisien distorsi, dan parameter kalibrasi lainnya.'
                : 'Download the generated pipeline artifact.';
          const downloadLabel = item.ext === '.dcm' ? '💾 Download DICOM' : '💾 Download';

          return (
            <div className="output-list-item" key={item.id}>
              <button
                className={`output-list-header${isExpanded ? ' expanded' : ''}`}
                onClick={() => toggleItem(item.id)}
              >
                <span className={`output-type-icon ${item.type}`}>
                  {isInput ? '📥' : isImage ? '🖼️' : item.ext === '.dcm' ? '🩻' : '📦'}
                </span>
                <span className="output-item-label">{item.label}</span>
                {item.ext && <span className="output-item-ext">{item.ext}</span>}
                <span className="output-toggle-arrow">{isExpanded ? '▲' : '▼'}</span>
              </button>

              {isExpanded && (
                <div className="output-list-content">
                  {isInput ? (
                    <img
                      key={item.file_id}
                      src={`${api.imageUrl(item.file_id)}?t=${t}`}
                      alt={item.label}
                      className="output-preview-img"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : isNpz ? (
                  ) : !isImage ? (
                    <div className="npz-preview-content">
                      <div className="npz-icon-area">{item.ext === '.dcm' ? '🩻' : '📊'}</div>
                      <div className="npz-details">
                        <div className="npz-title">{artifactLabel}</div>
                        <div className="npz-desc">{artifactDescription}</div>
                      </div>
                      <a
                        href={api.outputUrl(item.output_id)}
                        download={`output_${item.index + 1}_${item.output_id}${item.ext}`}
                        className="preview-button"
                      >
                        {downloadLabel}
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
