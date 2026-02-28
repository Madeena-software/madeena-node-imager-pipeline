import React from 'react';

const KeyboardShortcutsPanel = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  const shortcuts = [
    { key: 'Ctrl + Z', description: 'Undo last action' },
    { key: 'Ctrl + Shift + Z', description: 'Redo action' },
    { key: 'Ctrl + Y', description: 'Redo action (alternative)' },
    { key: 'Ctrl + C', description: 'Copy selected nodes' },
    { key: 'Ctrl + V', description: 'Paste copied nodes' },
    { key: 'Ctrl + S', description: 'Save/Load pipeline' },
    { key: 'Delete / Backspace', description: 'Delete selected nodes/edges' },
    { key: 'Double-click node', description: 'Open node properties' },
    { key: 'Double-click canvas', description: 'Deselect all' },
    { key: 'Drag from palette', description: 'Add new node' },
    { key: 'Drag from handle', description: 'Create connection' },
    { key: 'Click edge + Delete', description: 'Delete connection' },
    { key: 'Hover edge', description: 'Show delete button' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content shortcuts-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>⌨️ Keyboard Shortcuts</h3>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="shortcuts-list">
          {shortcuts.map((shortcut, index) => (
            <div key={index} className="shortcut-item">
              <div className="shortcut-key">{shortcut.key}</div>
              <div className="shortcut-description">{shortcut.description}</div>
            </div>
          ))}
        </div>
        
        <div className="modal-footer">
          <button className="close-button" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
};

export default KeyboardShortcutsPanel;
