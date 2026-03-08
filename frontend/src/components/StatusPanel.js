import { useState } from 'react';
import api from '../services/api';

const LogItem = ({ item }) => {
  const [expanded, setExpanded] = useState(false);
  const lines = item.message ? item.message.split('\n') : [];
  const preview = lines.slice(0, 3).join('\n');
  const hasMore = lines.length > 3;

  return (
    <div className="status-item status-log">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <span style={{ fontSize: '11px', color: '#888', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          {item.node_id ? `Node Log` : 'Log'}
        </span>
        {hasMore && (
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{ fontSize: '11px', background: 'none', border: 'none', color: '#007acc', cursor: 'pointer', padding: '0' }}
          >
            {expanded ? 'Collapse' : `+${lines.length - 3} more lines`}
          </button>
        )}
      </div>
      <pre style={{
        margin: 0,
        fontSize: '11px',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        background: 'rgba(0,0,0,0.2)',
        padding: '6px 8px',
        borderRadius: '4px',
        maxHeight: expanded ? 'none' : undefined,
        overflowY: expanded ? 'auto' : 'hidden',
        color: '#ccc',
      }}>
        {expanded ? item.message : preview}
        {!expanded && hasMore && <span style={{ color: '#666' }}>…</span>}
      </pre>
    </div>
  );
};

const StatusPanel = ({ status }) => {
  if (!status || status.length === 0) return null;

  return (
    <div className="status-panel">
      <h4>Processing Status</h4>
      {status.map((item, index) => {
        if (item.status === 'log') {
          return <LogItem key={`log-${index}`} item={item} />;
        }

        // Skip rendering completed/status items that have no message or output
        if (!item.message && !item.output_id) return null;

        const outputExt = item.output_ext || '.png';
        const outputType = item.output_type || (outputExt === '.png' ? 'image' : 'artifact');
        const isImage = outputType === 'image';
        const downloadLabel =
          outputExt === '.dcm'
            ? 'Download DICOM'
            : outputExt === '.npz'
              ? 'Download NPZ'
              : 'Download';
        const typeLabel =
          outputExt === '.dcm'
            ? 'Type: DICOM Output'
            : outputExt === '.npz'
              ? 'Type: Calibration Artifact'
              : 'Type: Image Output';

        return (
          <div
            key={item.output_id || `status-${index}`}
            className={`status-item status-${item.status}`}
          >
            {item.message && <div>{item.message}</div>}
            {item.output_id && (
              <div>
                <div style={{ color: '#666', fontSize: '12px', marginBottom: '6px' }}>
                  {typeLabel}
                  {item.output_name ? ` • File: ${item.output_name}` : ''}
                </div>
                {isImage && (
                  <>
                    <a
                      href={api.imageUrl(item.output_id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#007acc' }}
                    >
                      View Result
                    </a>
                    <span style={{ margin: '0 10px', color: '#888' }}>|</span>
                  </>
                )}
                <a
                  href={api.outputUrl(item.output_id)}
                  download={`output_${item.output_id}${outputExt}`}
                  style={{ color: '#007acc' }}
                >
                  {downloadLabel}
                </a>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default StatusPanel;
