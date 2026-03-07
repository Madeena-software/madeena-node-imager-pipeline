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
          {(() => {
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
              <>
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
              </>
            );
          })()}
        </div>
      ))}
    </div>
  );
};

export default StatusPanel;
