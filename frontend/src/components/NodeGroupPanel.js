import React, { useState } from 'react';

const NodeGroupPanel = ({ 
  nodes, 
  onCreateGroup, 
  onDeleteGroup, 
  onToggleGroupVisibility,
  groups = []
}) => {
  const [groupName, setGroupName] = useState('');

  const selectedNodesFromFlow = nodes.filter(node => node.selected);

  const handleCreateGroup = () => {
    if (!groupName.trim()) {
      alert('Please enter a group name');
      return;
    }

    if (selectedNodesFromFlow.length === 0) {
      alert('Please select nodes to group');
      return;
    }

    const newGroup = {
      id: `group-${Date.now()}`,
      name: groupName.trim(),
      nodeIds: selectedNodesFromFlow.map(node => node.id),
      color: `hsl(${Math.random() * 360}, 70%, 50%)`,
      visible: true,
      collapsed: false
    };

    onCreateGroup(newGroup);
    setGroupName('');
  };

  const handleToggleCollapse = (groupId) => {
    // This will be handled in the parent component
    onToggleGroupVisibility(groupId);
  };

  return (
    <div className="node-group-panel">
      <h4>Node Groups</h4>
      
      <div className="create-group-section">
        <input
          type="text"
          value={groupName}
          onChange={(e) => setGroupName(e.target.value)}
          placeholder="Group name..."
          className="group-input"
        />
        <button 
          onClick={handleCreateGroup}
          disabled={selectedNodesFromFlow.length === 0 || !groupName.trim()}
          className="create-group-button"
        >
          Create Group ({selectedNodesFromFlow.length} nodes)
        </button>
      </div>

      <div className="groups-list">
        {groups.map(group => (
          <div key={group.id} className="group-item">
            <div className="group-header">
              <div 
                className="group-color" 
                style={{ backgroundColor: group.color }}
              ></div>
              <span className="group-name">{group.name}</span>
              <span className="group-count">({group.nodeIds.length})</span>
            </div>
            <div className="group-actions">
              <button
                className="toggle-button"
                onClick={() => handleToggleCollapse(group.id)}
                title={group.collapsed ? "Expand group" : "Collapse group"}
              >
                {group.collapsed ? '👁️' : '👁️‍🗨️'}
              </button>
              <button
                className="delete-group-button"
                onClick={() => onDeleteGroup(group.id)}
                title="Delete group"
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
        {groups.length === 0 && (
          <p className="no-groups">No groups created. Select nodes and create a group.</p>
        )}
      </div>
    </div>
  );
};

export default NodeGroupPanel;