import React from 'react';
import api from '../services/api';

const StatusPanel = ({ status }) => {
  if (!status || status.length === 0) return null;

  return (
    <div className="status-panel">
      <h4>Processing Status</h4>
      {status.map((item, index) => (
        <div
          key={item.output_id || `status-${index}`}
          className={`status-item status-${item.status}`}
        >
          {item.message && <div>{item.message}</div>}
          {item.output_id && (
            <div>
              <a
                href={api.imageUrl(item.output_id)}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#007acc' }}
              >
                View Result
              </a>
              <span style={{ margin: '0 10px', color: '#888' }}>|</span>
              <a
                href={api.imageUrl(item.output_id)}
                download={`output_${item.output_id}.png`}
                style={{ color: '#007acc' }}
              >
                Download
              </a>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default StatusPanel;