import React, { useCallback } from 'react';
import { Handle, Position } from 'reactflow';

const CustomNode = ({ data, isConnectable }) => {
  const handleDelete = useCallback((event) => {
    event.stopPropagation(); // Prevent double-click from firing
    if (data.onDelete) {
      data.onDelete();
    }
  }, [data]);

  const handleDoubleClick = useCallback((event) => {
    console.log('Double click detected on node:', data); // Debug log
    event.stopPropagation(); // Prevent React Flow from handling the event
    if (data.onDoubleClick) {
      data.onDoubleClick();
    }
  }, [data]);

  const getNodeColor = () => {
    switch (data.type) {
      case 'input': return '#4caf50';
      case 'output': return '#f44336';
      default: return '#007acc';
    }
  };

  return (
    <div 
      style={{
        background: '#2d2d2d',
        border: `2px solid ${getNodeColor()}`,
        borderRadius: '8px',
        padding: '10px',
        minWidth: '150px',
        color: 'white',
        position: 'relative',
        cursor: 'pointer'
      }}
      onDoubleClick={handleDoubleClick}
      title="Double-click to edit properties"
    >
      {/* Delete Button */}
      <button
        onClick={handleDelete}
        className="node-delete-button"
        title="Delete node"
      >
        ×
      </button>
      
      {/* Input handles - multiple if multi-input node */}
      {data.inputs > 0 && (
        <>
          {data.multi_input && data.input_slots ? (
            // Multi-input node: create labeled handles for each slot
            data.input_slots.map((slot, index) => {
              const totalSlots = data.input_slots.length;
              const verticalSpacing = 80 / (totalSlots + 1);
              const topPosition = verticalSpacing * (index + 1);
              
              return (
                <React.Fragment key={slot}>
                  <Handle
                    type="target"
                    position={Position.Left}
                    id={slot}
                    isConnectable={isConnectable}
                    style={{
                      top: `${topPosition}%`,
                      background: '#ff9800',
                    }}
                  />
                  <div style={{
                    position: 'absolute',
                    left: '8px',
                    top: `${topPosition}%`,
                    transform: 'translateY(-50%)',
                    fontSize: '8px',
                    color: '#ff9800',
                    fontWeight: 'bold',
                    pointerEvents: 'none',
                    textShadow: '1px 1px 2px black'
                  }}>
                    {slot}
                  </div>
                </React.Fragment>
              );
            })
          ) : (
            // Single input node: one handle
            <Handle
              type="target"
              position={Position.Left}
              isConnectable={isConnectable}
            />
          )}
        </>
      )}
      
      <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
        {data.name}
      </div>
      
      {data.filename && (
        <div style={{ fontSize: '10px', color: '#4caf50', marginBottom: '5px' }}>
          📁 {data.filename}
        </div>
      )}

      {/* Show parameter count if any */}
      {data.parameters && Object.keys(data.parameters).length > 0 && (
        <div style={{ fontSize: '9px', color: '#888', marginBottom: '5px' }}>
          ⚙️ {Object.keys(data.parameters).length} parameter(s)
        </div>
      )}

      {/* Current parameter values preview */}
      {data.parameters && Object.keys(data.parameters).length > 0 && (
        <div style={{ fontSize: '8px', color: '#666' }}>
          Double-click to configure
        </div>
      )}
      
      {data.outputs > 0 && (
        <Handle
          type="source"
          position={Position.Right}
          isConnectable={isConnectable}
        />
      )}
    </div>
  );
};

export default CustomNode;