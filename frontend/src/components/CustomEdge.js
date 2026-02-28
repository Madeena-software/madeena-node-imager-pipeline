import React from 'react';
import { getBezierPath, EdgeLabelRenderer } from 'reactflow';

const CustomEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
  selected,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const onEdgeClick = (event) => {
    event.stopPropagation();
    if (data && data.onDelete) {
      data.onDelete(id);
    }
  };

  // Enhanced edge style with selection state
  const edgeStyle = {
    ...style,
    strokeWidth: selected ? 3 : 2,
    stroke: selected ? '#4caf50' : (style.stroke || '#b1b1b7'),
  };

  return (
    <>
      {/* Invisible wider path for easier clicking */}
      <path
        d={edgePath}
        fill="none"
        strokeWidth={20}
        stroke="transparent"
        className="react-flow__edge-interaction"
      />
      
      {/* Visible edge path */}
      <path
        id={id}
        style={edgeStyle}
        className="react-flow__edge-path custom-edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />

      {/* Delete button in the middle of the edge */}
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <button
            onClick={onEdgeClick}
            className="edge-delete-button"
            style={{
              width: '20px',
              height: '20px',
              background: '#ff4444',
              border: '2px solid white',
              borderRadius: '50%',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '14px',
              fontWeight: 'bold',
              color: 'white',
              opacity: selected ? 1 : 0,
              transition: 'opacity 0.2s ease',
              padding: 0,
            }}
            title="Delete connection (or press Delete)"
          >
            ×
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
};

export default CustomEdge;