import React, { useState, useCallback, useEffect, useRef } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  Panel,
  MarkerType,
  reconnectEdge,
} from 'reactflow';
import 'reactflow/dist/style.css';

import NodePalette from './components/NodePalette';
import CustomNode from './components/CustomNode';
import CustomEdge from './components/CustomEdge';
import StatusPanel from './components/StatusPanel';
import SaveLoadModal from './components/SaveLoadModal';
import NodeGroupPanel from './components/NodeGroupPanel';
import NodePropertiesModal from './components/NodePropertiesModal';
import KeyboardShortcutsPanel from './components/KeyboardShortcutsPanel';
import ImagePreviewPanel from './components/ImagePreviewPanel';
import api from './services/api';
import socketService from './services/socketService';
import clipboardService from './services/clipboardService';
import useUndoRedo from './hooks/useUndoRedo';

const nodeTypes = {
  customNode: CustomNode,
};

const edgeTypes = {
  default: CustomEdge,
};

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [availableNodes, setAvailableNodes] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [processingStatus, setProcessingStatus] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showSaveLoadModal, setShowSaveLoadModal] = useState(false);
  const [showPropertiesModal, setShowPropertiesModal] = useState(false);
  const [selectedNodeForProperties, setSelectedNodeForProperties] = useState(null);
  const [nodeGroups, setNodeGroups] = useState([]);
  const [showShortcutsPanel, setShowShortcutsPanel] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  
  // Reference for edge reconnection
  const edgeReconnectSuccessful = useRef(true);
  
  // Reference for ReactFlow instance (for coordinate conversion)
  const reactFlowInstance = useRef(null);

  // Undo/Redo functionality
  const {
    state: pipelineHistory,
    setState: setPipelineHistory,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory
  } = useUndoRedo({ nodes: [], edges: [] });

  // Initialize theme from localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
      setIsDarkTheme(false);
      document.body.classList.add('light-theme');
    }
  }, []);

  // Toggle theme
  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    if (newTheme) {
      document.body.classList.remove('light-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.add('light-theme');
      localStorage.setItem('theme', 'light');
    }
  };

  // Update history when nodes or edges change (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      setPipelineHistory({ nodes, edges });
    }, 500);
    return () => clearTimeout(timer);
  }, [nodes, edges, setPipelineHistory]);

  useEffect(() => {
    // Load available nodes from backend
    loadAvailableNodes();
    
    // Setup socket listeners
    socketService.connect();

    const handleProgress = (data) => {
      setProcessingStatus(prev => [...prev, data]);
    };

    const handleError = (data) => {
      setProcessingStatus(prev => [...prev, {
        status: 'error',
        message: data.error
      }]);
      setIsProcessing(false);
    };

    socketService.on('pipeline_progress', handleProgress);
    socketService.on('pipeline_error', handleError);

    return () => {
      socketService.off('pipeline_progress', handleProgress);
      socketService.off('pipeline_error', handleError);
      socketService.disconnect();
    };
  }, []);

  // Core node management functions (must be defined first)
  const deleteNode = useCallback((nodeId) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
  }, [setNodes, setEdges]);

  // Handle double clicks on nodes
  const clickCountRef = useRef(0);
  const clickTimerRef = useRef(null);
  
  const handleNodeDoubleClick = useCallback((nodeId) => {
    const node = nodes.find(n => n.id === nodeId);
    if (node) {
      setSelectedNodeForProperties(node);
      setShowPropertiesModal(true);
    }
  }, [nodes]);

  // Undo/Redo handlers
  const handleUndo = useCallback(() => {
    if (canUndo) {
      const previousState = undo();
      setNodes(previousState.nodes);
      setEdges(previousState.edges);
    }
  }, [canUndo, undo, setNodes, setEdges]);

  const handleRedo = useCallback(() => {
    if (canRedo) {
      const nextState = redo();
      setNodes(nextState.nodes);
      setEdges(nextState.edges);
    }
  }, [canRedo, redo, setNodes, setEdges]);

  // Copy/Paste handlers
  const handleCopy = useCallback(() => {
    const selectedNodes = nodes.filter(node => node.selected);
    const selectedNodeIds = selectedNodes.map(node => node.id);
    const selectedEdges = edges.filter(edge => 
      selectedNodeIds.includes(edge.source) || selectedNodeIds.includes(edge.target)
    );

    if (selectedNodes.length > 0) {
      clipboardService.copy({ nodes: selectedNodes, edges: selectedEdges });
    }
  }, [nodes, edges]);

  const handlePaste = useCallback(() => {
    const clipboardData = clipboardService.paste();
    if (clipboardData) {
      const { nodes: newNodes, edges: newEdges } = clipboardService.generateNewNodeIds(
        clipboardData.nodes,
        clipboardData.edges
      );

      // Add delete handlers to pasted nodes
      const nodesWithHandlers = newNodes.map(node => ({
        ...node,
        data: {
          ...node.data,
          onDelete: () => deleteNode(node.id),
          onDoubleClick: () => handleNodeDoubleClick(node.id),
        },
      }));

      setNodes(nds => nds.concat(nodesWithHandlers));
      setEdges(eds => eds.concat(newEdges));
      
      // Update history
      setPipelineHistory({ 
        nodes: nodes.concat(nodesWithHandlers), 
        edges: edges.concat(newEdges) 
      });
    }
  }, [nodes, edges, deleteNode, handleNodeDoubleClick, setNodes, setEdges, setPipelineHistory]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event) => {
      // Check if user is typing in an input field
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
      }

      // Open shortcuts panel with ? or F1
      if ((event.key === '?' || event.key === 'F1') && !event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        setShowShortcutsPanel(true);
        return;
      }

      if (event.ctrlKey || event.metaKey) {
        switch (event.key.toLowerCase()) {
          case 'z':
            if (event.shiftKey) {
              // Ctrl+Shift+Z or Cmd+Shift+Z = Redo
              event.preventDefault();
              handleRedo();
            } else {
              // Ctrl+Z or Cmd+Z = Undo
              event.preventDefault();
              handleUndo();
            }
            break;
          case 'y':
            // Ctrl+Y = Redo (alternative)
            event.preventDefault();
            handleRedo();
            break;
          case 'c':
            // Ctrl+C = Copy selected nodes
            event.preventDefault();
            handleCopy();
            break;
          case 'v':
            // Ctrl+V = Paste nodes
            event.preventDefault();
            handlePaste();
            break;
          case 's':
            // Ctrl+S = Save pipeline
            event.preventDefault();
            setShowSaveLoadModal(true);
            break;
          default:
            break;
        }
      } else if (event.key === 'Delete' || event.key === 'Backspace') {
        // Delete selected nodes and edges
        const selectedNodes = nodes.filter(node => node.selected);
        const selectedEdges = edges.filter(edge => edge.selected);
        
        // Delete selected nodes
        selectedNodes.forEach(node => {
          deleteNode(node.id);
        });
        
        // Delete selected edges
        if (selectedEdges.length > 0) {
          setEdges((eds) => eds.filter(edge => !edge.selected));
          // Update history
          setPipelineHistory({ nodes, edges: edges.filter(edge => !edge.selected) });
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [nodes, edges, handleUndo, handleRedo, handleCopy, handlePaste, setShowSaveLoadModal, setShowShortcutsPanel, deleteNode, setEdges, setPipelineHistory]);

  const loadAvailableNodes = async () => {
    try {
      const response = await api.get('/nodes');
      setAvailableNodes(response.data);
    } catch (error) {
      console.error('Failed to load nodes:', error);
    }
  };

  const deleteEdge = useCallback((edgeId) => {
    setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
    // Update history will be handled by the effect that watches edges changes
  }, [setEdges]);

  const onConnect = useCallback(
    (params) => {
      const newEdge = {
        ...params,
        data: {
          onDelete: deleteEdge,
        },
      };
      setEdges((eds) => addEdge(newEdge, eds));
    },
    [setEdges, deleteEdge]
  );

  // Edge reconnection handlers
  const onReconnectStart = useCallback(() => {
    edgeReconnectSuccessful.current = false;
  }, []);

  const onReconnect = useCallback((oldEdge, newConnection) => {
    edgeReconnectSuccessful.current = true;
    setEdges((els) => reconnectEdge(oldEdge, newConnection, els));
    setPipelineHistory({ nodes, edges: reconnectEdge(oldEdge, newConnection, edges) });
  }, [setEdges, nodes, edges, setPipelineHistory]);

  const onReconnectEnd = useCallback((_, edge) => {
    if (!edgeReconnectSuccessful.current) {
      setEdges((eds) => eds.filter((e) => e.id !== edge.id));
      setPipelineHistory({ nodes, edges: edges.filter((e) => e.id !== edge.id) });
    }
    edgeReconnectSuccessful.current = true;
  }, [setEdges, nodes, edges, setPipelineHistory]);

  const handleNodeClick = useCallback((event, node) => {
    // Clear existing timer
    if (clickTimerRef.current) {
      clearTimeout(clickTimerRef.current);
      clickTimerRef.current = null;
    }
    
    clickCountRef.current += 1;
    
    if (clickCountRef.current === 1) {
      // Start timer for double-click detection
      clickTimerRef.current = setTimeout(() => {
        clickCountRef.current = 0;
      }, 300);
    } else if (clickCountRef.current >= 2) {
      // Double-click detected
      clickCountRef.current = 0;
      handleNodeDoubleClick(node.id);
    }
  }, [handleNodeDoubleClick]);

  const handleUpdateNodeProperties = useCallback((nodeId, newParameters, additionalData = {}) => {
    setNodes((nds) => 
      nds.map((node) => 
        node.id === nodeId 
          ? {
              ...node,
              data: {
                ...node.data,
                ...additionalData,
                parameters: newParameters
              }
            }
          : node
      )
    );
  }, [setNodes]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const nodeType = event.dataTransfer.getData('application/reactflow');
      const nodeData = JSON.parse(event.dataTransfer.getData('application/json'));

      if (!nodeType) {
        return;
      }

      // Convert screen coordinates to flow coordinates for accurate drop position
      let position;
      if (reactFlowInstance.current) {
        position = reactFlowInstance.current.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });
      } else {
        // Fallback if instance not available
        const reactFlowBounds = event.target.getBoundingClientRect();
        position = {
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        };
      }

      const nodeId = `${nodeType}-${Date.now()}`;
      const newNode = {
        id: nodeId,
        type: 'customNode',
        position,
        data: {
          ...nodeData,
          nodeType: nodeType,
          parameters: {},
          onDelete: () => deleteNode(nodeId),
          onDoubleClick: () => handleNodeDoubleClick(nodeId),
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [setNodes, deleteNode, handleNodeDoubleClick]
  );

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const response = await api.uploadImage(file);
      setSelectedFile(response.data);
      
      // Update input nodes with the uploaded file
      setNodes((nds) =>
        nds.map((node) => {
          if (node.data.nodeType === 'input') {
            return {
              ...node,
              data: {
                ...node.data,
                file_id: response.data.file_id,
                filename: response.data.filename,
                // Preserve the handlers
                onDelete: node.data.onDelete,
                onDoubleClick: node.data.onDoubleClick,
              },
            };
          }
          return node;
        })
      );
    } catch (error) {
      console.error('File upload failed:', error);
    }
  };

  // Pipeline management
  const handleSavePipeline = (name) => {
    // Save is handled by SaveLoadModal via pipelineStorage.
    // This callback runs after a successful save for any extra side-effects.
  };

  const handleLoadPipeline = (pipeline) => {
    // Clear current pipeline
    setNodes([]);
    setEdges([]);
    setProcessingStatus([]);
    clearHistory();
    
    // Load pipeline with delete handlers
    const nodesWithHandlers = pipeline.nodes.map(node => ({
      ...node,
      data: {
        ...node.data,
        onDelete: () => deleteNode(node.id),
        onDoubleClick: () => handleNodeDoubleClick(node.id),
      }
    }));

    setTimeout(() => {
      setNodes(nodesWithHandlers);
      setEdges(pipeline.edges);
    }, 100);
  };

  // Node grouping
  const handleCreateGroup = (group) => {
    setNodeGroups(prev => [...prev, group]);
    
    // Apply group styling to nodes
    setNodes(nds => 
      nds.map(node => {
        if (group.nodeIds.includes(node.id)) {
          return {
            ...node,
            className: `${node.className || ''} grouped`.trim(),
            style: {
              ...node.style,
              '--group-color': group.color
            }
          };
        }
        return node;
      })
    );
  };

  const handleDeleteGroup = (groupId) => {
    const group = nodeGroups.find(g => g.id === groupId);
    if (!group) return;

    // Remove group styling from nodes
    setNodes(nds => 
      nds.map(node => {
        if (group.nodeIds.includes(node.id)) {
          return {
            ...node,
            className: node.className?.replace('grouped', '').trim() || undefined,
            style: {
              ...node.style,
              '--group-color': undefined
            }
          };
        }
        return node;
      })
    );

    setNodeGroups(prev => prev.filter(g => g.id !== groupId));
  };

  const handleToggleGroupVisibility = (groupId) => {
    setNodeGroups(prev => 
      prev.map(group => 
        group.id === groupId 
          ? { ...group, collapsed: !group.collapsed }
          : group
      )
    );

    const group = nodeGroups.find(g => g.id === groupId);
    if (!group) return;

    // Toggle node visibility
    setNodes(nds => 
      nds.map(node => {
        if (group.nodeIds.includes(node.id)) {
          return {
            ...node,
            hidden: !group.collapsed ? true : false
          };
        }
        return node;
      })
    );
  };

  const executePipeline = async () => {
    // Check if there's an input node with a file_id
    const inputNode = nodes.find(node => node.data.nodeType === 'input');
    if (!inputNode || !inputNode.data.file_id) {
      alert('Please upload an image to the input node first');
      return;
    }

    setIsProcessing(true);
    setProcessingStatus([]);

    try {
      const pipelineData = {
        nodes: nodes.map(node => {
          // Build input_mapping for multi-input nodes
          const input_mapping = {};
          
          if (node.data.multi_input && node.data.input_slots) {
            // Find all edges targeting this node
            edges
              .filter(edge => edge.target === node.id)
              .forEach(edge => {
                // edge.targetHandle contains the slot name (e.g., 'projection', 'gain', 'dark')
                const slotName = edge.targetHandle || node.data.input_slots[0]; // fallback to first slot
                input_mapping[slotName] = edge.source;
              });
          }
          
          return {
            id: node.id,
            type: node.data.nodeType,
            data: {
              ...node.data.parameters,
              // Include file_id for input nodes
              ...(node.data.nodeType === 'input' && node.data.file_id ? 
                  { file_id: node.data.file_id } : {}),
              // Include input_mapping for multi-input nodes
              ...(Object.keys(input_mapping).length > 0 ? { input_mapping } : {})
            }
          };
        }),
        edges: edges.map(edge => ({
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          targetHandle: edge.targetHandle
        }))
      };

      const response = await api.executePipeline(pipelineData);
      
      if (response.data.result && response.data.result.output_id) {
        const result = response.data.result;
        
        // Check if there are multiple outputs
        if (result.all_outputs && result.all_outputs.length > 0) {
          // Add status for each output
          result.all_outputs.forEach((output, index) => {
            setProcessingStatus(prev => [...prev, {
              status: 'completed',
              message: `Output ${index + 1} completed successfully`,
              output_id: output.output_id
            }]);
          });
        } else {
          // Single output
          setProcessingStatus(prev => [...prev, {
            status: 'completed',
            message: 'Pipeline completed successfully',
            output_id: result.output_id
          }]);
        }
      }
    } catch (error) {
      setProcessingStatus(prev => [...prev, {
        status: 'error',
        message: error.response?.data?.message || 'Pipeline execution failed'
      }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const clearPipeline = () => {
    setNodes([]);
    setEdges([]);
    setProcessingStatus([]);
    setSelectedFile(null);
    setNodeGroups([]);
    clearHistory();
  };

  return (
    <div className="app">
      <div className="toolbar">
        <h1>Image Processing Pipeline</h1>
        
        <div className="toolbar-section">
          <button onClick={executePipeline} disabled={isProcessing}>
            {isProcessing ? 'Processing...' : 'Execute Pipeline'}
          </button>
          <button onClick={clearPipeline}>Clear All</button>
        </div>

        <div className="toolbar-divider"></div>

        <div className="toolbar-section">
          <button onClick={handleUndo} disabled={!canUndo} title="Undo (Ctrl+Z)">
            ↶ Undo
          </button>
          <button onClick={handleRedo} disabled={!canRedo} title="Redo (Ctrl+Shift+Z)">
            ↷ Redo
          </button>
        </div>

        <div className="toolbar-divider"></div>

        <div className="toolbar-section">
          <button onClick={handleCopy} title="Copy selected nodes (Ctrl+C)">
            📋 Copy
          </button>
          <button 
            onClick={handlePaste} 
            disabled={!clipboardService.hasData()}
            title="Paste nodes (Ctrl+V)"
          >
            📄 Paste
          </button>
        </div>

        <div className="toolbar-divider"></div>

        <div className="toolbar-section">
          <button onClick={() => setShowSaveLoadModal(true)} title="Save/Load Pipeline (Ctrl+S)">
            💾 Save/Load
          </button>
          <button 
            onClick={toggleTheme}
            className="theme-toggle"
            title="Toggle Theme"
          >
            {isDarkTheme ? '☀️' : '🌙'}
          </button>
          <button 
            onClick={() => setShowShortcutsPanel(true)}
            title="Keyboard Shortcuts (? or F1)"
          >
            ⌨️ Help
          </button>
        </div>

        <span className="shortcut-hint">
          Shortcuts: ? or F1=Help, Del=Delete, Ctrl+Z=Undo, Ctrl+C/V=Copy/Paste
        </span>
      </div>
      
      <div className="main-content">
        <div className="sidebar">

          
          <NodePalette nodes={availableNodes} />
          
          <NodeGroupPanel
            nodes={nodes}
            groups={nodeGroups}
            onCreateGroup={handleCreateGroup}
            onDeleteGroup={handleDeleteGroup}
            onToggleGroupVisibility={handleToggleGroupVisibility}
          />
        </div>

        <div className="flow-container">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onReconnect={onReconnect}
            onReconnectStart={onReconnectStart}
            onReconnectEnd={onReconnectEnd}
            onNodeClick={handleNodeClick}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onInit={(instance) => { reactFlowInstance.current = instance; }}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            connectionLineStyle={{ stroke: '#4caf50', strokeWidth: 2 }}
            connectionLineType="bezier"
            defaultEdgeOptions={{
              type: 'default',
              animated: false,
              style: { stroke: '#b1b1b7', strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#b1b1b7',
              }
            }}
            selectNodesOnDrag={false}
            snapToGrid={false}
            snapGrid={[15, 15]}
            elevateEdgesOnSelect={true}
            fitView
          >
            <Controls />
            <Background color="#404040" gap={20} />
          </ReactFlow>
        </div>
      </div>

      <StatusPanel status={processingStatus} />

      <ImagePreviewPanel 
        nodes={nodes}
        processingStatus={processingStatus}
      />

      <SaveLoadModal
        isOpen={showSaveLoadModal}
        onClose={() => setShowSaveLoadModal(false)}
        onSave={handleSavePipeline}
        onLoad={handleLoadPipeline}
        currentPipeline={{ nodes, edges }}
      />

      <NodePropertiesModal
        isOpen={showPropertiesModal}
        onClose={() => {
          setShowPropertiesModal(false);
          setSelectedNodeForProperties(null);
        }}
        node={selectedNodeForProperties}
        onUpdateNode={handleUpdateNodeProperties}
        availableNodes={availableNodes}
      />

      <KeyboardShortcutsPanel
        isOpen={showShortcutsPanel}
        onClose={() => setShowShortcutsPanel(false)}
      />
    </div>
  );
}

export default App;