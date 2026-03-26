import { useMemo, useState } from 'react';

// Static ordering — defined outside the component to avoid re-creation on every render
const CATEGORY_ORDER = [
  'Basic',
  'Transform',
  'Color',
  'Filter',
  'Enhancement',
  'Pipeline',
  'Math',
  'Morphological',
  'Detection',
  'Other',
];

const NodePalette = ({ nodes }) => {
  const [expandedCategories, setExpandedCategories] = useState({});

  const onDragStart = (event, nodeType, nodeData) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/json', JSON.stringify(nodeData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const toggleCategory = (category) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  // Group nodes by category — recomputes only when `nodes` changes
  const groupedNodes = useMemo(
    () =>
      nodes.reduce((acc, node) => {
        const category = node.category || 'Other';
        if (!acc[category]) {
          acc[category] = [];
        }
        acc[category].push(node);
        return acc;
      }, {}),
    [nodes]
  );

  // Derive sorted category keys from the already-grouped map
  const sortedCategories = useMemo(
    () =>
      Object.keys(groupedNodes).sort((a, b) => {
        const indexA = CATEGORY_ORDER.indexOf(a);
        const indexB = CATEGORY_ORDER.indexOf(b);
        if (indexA === -1) return 1;
        if (indexB === -1) return -1;
        return indexA - indexB;
      }),
    [groupedNodes]
  );

  return (
    <div className="node-palette">
      <h3>Available Nodes</h3>

      {sortedCategories.map((category) => (
        <div key={category} className="node-category-group">
          <div className="category-header" onClick={() => toggleCategory(category)}>
            <span className="category-icon">{expandedCategories[category] ? '▼' : '▶'}</span>
            <span className="category-name">{category}</span>
            <span className="category-count">({groupedNodes[category].length})</span>
          </div>

          {expandedCategories[category] && (
            <div className="category-items">
              {groupedNodes[category].map((node) => (
                <div
                  key={node.id}
                  className="node-item"
                  draggable
                  onDragStart={(event) => onDragStart(event, node.id, node)}
                >
                  <h4>{node.name}</h4>
                  <p>{node.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

export default NodePalette;
