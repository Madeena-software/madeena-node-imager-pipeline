import { useCallback, useEffect, useRef, useState } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MarkerType,
  reconnectEdge,
  useEdgesState,
  useNodesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import CustomEdge from './components/CustomEdge';
import CustomNode from './components/CustomNode';
import KeyboardShortcutsPanel from './components/KeyboardShortcutsPanel';
import NodeGroupPanel from './components/NodeGroupPanel';
import NodePalette from './components/NodePalette';
import NodePropertiesModal from './components/NodePropertiesModal';
import OutputPreviewPanel from './components/OutputPreviewPanel';
import SaveLoadModal from './components/SaveLoadModal';
import StatusPanel from './components/StatusPanel';
import useUndoRedo from './hooks/useUndoRedo';
import api from './services/api';
import clipboardService from './services/clipboardService';
import socketService from './services/socketService';

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
  const [processingStatus, setProcessingStatus] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showSaveLoadModal, setShowSaveLoadModal] = useState(false);
  const [showPropertiesModal, setShowPropertiesModal] = useState(false);
  const [selectedNodeForProperties, setSelectedNodeForProperties] = useState(null);
  const [nodeGroups, setNodeGroups] = useState([]);
  const [showShortcutsPanel, setShowShortcutsPanel] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(window.innerWidth > 768);
  const isBusy = isProcessing || isUploading;

  const toggleSidebar = () => setSidebarOpen((prev) => !prev);

  // Reference for edge reconnection
  const edgeReconnectSuccessful = useRef(true);

  // Reference for ReactFlow instance (for coordinate conversion)
  const reactFlowInstance = useRef(null);

  // Undo/Redo functionality
  const {
    setState: setPipelineHistory,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory,
  } = useUndoRedo({
    nodes: [],
    edges: [],
  });

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
      setPipelineHistory({
        nodes,
        edges,
      });
    }, 500);
    return () => clearTimeout(timer);
  }, [nodes, edges, setPipelineHistory]);

  const loadAvailableNodes = useCallback(async () => {
    try {
      const response = await api.get('/nodes');
      setAvailableNodes(response.data);
    } catch (error) {
      console.error('Failed to load nodes:', error);
    }
  }, [setAvailableNodes]);

  useEffect(() => {
    // Load available nodes from backend
    loadAvailableNodes();

    // Setup socket listeners
    socketService.connect();

    const handleProgress = (data) => {
      setProcessingStatus((prev) => [...prev, data]);
    };

    const handleError = (data) => {
      setProcessingStatus((prev) => [
        ...prev,
        {
          status: 'error',
          message: data.error,
        },
      ]);
      setIsProcessing(false);
    };

    socketService.on('pipeline_progress', handleProgress);
    socketService.on('pipeline_error', handleError);

    return () => {
      socketService.off('pipeline_progress', handleProgress);
      socketService.off('pipeline_error', handleError);
    };
  }, [loadAvailableNodes, setProcessingStatus, setIsProcessing]);

  // Core node management functions (must be defined first)
  const deleteNode = useCallback(
    (nodeId) => {
      setNodes((nds) => nds.filter((node) => node.id !== nodeId));
      setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    },
    [setNodes, setEdges]
  );

  // Handle double clicks on nodes
  const clickCountRef = useRef(0);
  const clickTimerRef = useRef(null);

  const handleNodeDoubleClick = useCallback(
    (nodeId) => {
      const node = nodes.find((n) => n.id === nodeId);
      if (node) {
        setSelectedNodeForProperties(node);
        setShowPropertiesModal(true);
      }
    },
    [nodes]
  );

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
    const selectedNodes = nodes.filter((node) => node.selected);
    const selectedNodeIds = selectedNodes.map((node) => node.id);
    const selectedEdges = edges.filter(
      (edge) => selectedNodeIds.includes(edge.source) || selectedNodeIds.includes(edge.target)
    );

    if (selectedNodes.length > 0) {
      clipboardService.copy({
        nodes: selectedNodes,
        edges: selectedEdges,
      });
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
      const nodesWithHandlers = newNodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onDelete: () => deleteNode(node.id),
          onDoubleClick: () => handleNodeDoubleClick(node.id),
        },
      }));

      setNodes((nds) => nds.concat(nodesWithHandlers));
      setEdges((eds) => eds.concat(newEdges));
    }
  }, [deleteNode, handleNodeDoubleClick, setNodes, setEdges]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event) => {
      if (isBusy) {
        return;
      }

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
        const selectedNodes = nodes.filter((node) => node.selected);
        const selectedEdges = edges.filter((edge) => edge.selected);

        // Delete selected nodes
        selectedNodes.forEach((node) => {
          deleteNode(node.id);
        });

        // Delete selected edges
        if (selectedEdges.length > 0) {
          setEdges((eds) => eds.filter((edge) => !edge.selected));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    isBusy,
    nodes,
    edges,
    handleUndo,
    handleRedo,
    handleCopy,
    handlePaste,
    setShowSaveLoadModal,
    setShowShortcutsPanel,
    deleteNode,
    setEdges,
    setPipelineHistory,
  ]);

  const deleteEdge = useCallback(
    (edgeId) => {
      setEdges((eds) => eds.filter((edge) => edge.id !== edgeId));
      // Update history will be handled by the effect that watches edges changes
    },
    [setEdges]
  );

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

  const onReconnect = useCallback(
    (oldEdge, newConnection) => {
      edgeReconnectSuccessful.current = true;
      setEdges((els) => reconnectEdge(oldEdge, newConnection, els));
    },
    [setEdges]
  );

  const onReconnectEnd = useCallback(
    (_, edge) => {
      if (!edgeReconnectSuccessful.current) {
        setEdges((eds) => eds.filter((e) => e.id !== edge.id));
      }
      edgeReconnectSuccessful.current = true;
    },
    [setEdges]
  );

  const handleNodeClick = useCallback(
    (event, node) => {
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
    },
    [handleNodeDoubleClick]
  );

  const handleUpdateNodeProperties = useCallback(
    (nodeId, newParameters, additionalData = {}) => {
      setNodes((nds) =>
        nds.map((node) =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  ...additionalData,
                  parameters: newParameters,
                },
              }
            : node
        )
      );

      setSelectedNodeForProperties((prev) =>
        prev && prev.id === nodeId
          ? {
              ...prev,
              data: {
                ...prev.data,
                ...additionalData,
                parameters: newParameters,
              },
            }
          : prev
      );
    },
    [setNodes, setSelectedNodeForProperties]
  );

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

  const handleMultipleFileUploads = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const inputNodes = nodes.filter((node) => node.data.nodeType === 'input' && !node.data.file_id);
    if (inputNodes.length < files.length) {
      alert('Not enough empty input nodes for the selected files.');
      return;
    }

    setIsUploading(true);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const inputNode = inputNodes[i];
        const response = await api.uploadImage(file);

        setNodes((nds) =>
          nds.map((n) =>
            n.id === inputNode.id
              ? {
                  ...n,
                  data: {
                    ...n.data,
                    file_id: response.data.file_id,
                    filename: response.data.filename,
                  },
                }
              : n
          )
        );
      }
    } catch (error) {
      console.error('File upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  // Pipeline management
  const handleSavePipeline = useCallback((name) => {
    // Save is handled by SaveLoadModal via pipelineStorage.
    // This callback runs after a successful save for any extra side-effects.
  }, []);

  const handleLoadPipeline = useCallback(
    (pipeline) => {
      // Clear current pipeline
      setNodes([]);
      setEdges([]);
      setProcessingStatus([]);
      clearHistory();

      // Load pipeline with delete handlers
      const nodesWithHandlers = pipeline.nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onDelete: () => deleteNode(node.id),
          onDoubleClick: () => handleNodeDoubleClick(node.id),
        },
      }));

      setTimeout(() => {
        setNodes(nodesWithHandlers);
        setEdges(pipeline.edges);
      }, 100);
    },
    [setNodes, setEdges, setProcessingStatus, clearHistory, deleteNode, handleNodeDoubleClick]
  );

  // Node grouping
  const handleCreateGroup = useCallback(
    (group) => {
      setNodeGroups((prev) => [...prev, group]);

      // Apply group styling to nodes
      setNodes((nds) =>
        nds.map((node) => {
          if (group.nodeIds.includes(node.id)) {
            return {
              ...node,
              className: `${node.className || ''} grouped`.trim(),
              style: {
                ...node.style,
                '--group-color': group.color,
              },
            };
          }
          return node;
        })
      );
    },
    [setNodeGroups, setNodes]
  );

  const handleDeleteGroup = useCallback(
    (groupId) => {
      const group = nodeGroups.find((g) => g.id === groupId);
      if (!group) return;

      // Remove group styling from nodes
      setNodes((nds) =>
        nds.map((node) => {
          if (group.nodeIds.includes(node.id)) {
            return {
              ...node,
              className: node.className
                ? node.className.replace('grouped', '').trim() || undefined
                : undefined,
              style: {
                ...node.style,
                '--group-color': undefined,
              },
            };
          }
          return node;
        })
      );

      setNodeGroups((prev) => prev.filter((g) => g.id !== groupId));
    },
    [nodeGroups, setNodes, setNodeGroups]
  );

  const handleToggleGroupVisibility = useCallback(
    (groupId) => {
      const group = nodeGroups.find((g) => g.id === groupId);
      if (!group) return;

      const newCollapsed = !group.collapsed;

      setNodeGroups((prev) =>
        prev.map((g) =>
          g.id === groupId
            ? {
                ...g,
                collapsed: newCollapsed,
              }
            : g
        )
      );

      setNodes((nds) =>
        nds.map((node) => {
          if (group.nodeIds.includes(node.id)) {
            return {
              ...node,
              hidden: newCollapsed,
            };
          }
          return node;
        })
      );
    },
    [nodeGroups, setNodeGroups, setNodes]
  );

  const executePipeline = useCallback(async () => {
    // Check if there's at least one input node with a file_id
    const hasInputFile = nodes.some((node) => node.data.nodeType === 'input' && node.data.file_id);
    if (!hasInputFile) {
      alert('Please upload an image to an input node first');
      return;
    }

    const missingDicomJson = nodes.some(
      (node) => node.data.nodeType === 'tiff_json_to_dicom' && !node.data.json_file_id
    );
    if (missingDicomJson) {
      alert('Please upload JSON metadata in each TIFF JSON to DICOM node before execution');
      return;
    }

    const missingCalibrationNpz = nodes.some(
      (node) => node.data.nodeType === 'apply_camera_calibration' && !node.data.npz_file_id
    );
    if (missingCalibrationNpz) {
      alert('Please upload a calibration .npz file in each Apply Camera Calibration node before execution');
      return;
    }

    setIsProcessing(true);
    setProcessingStatus([]);

    try {
      const pipelineData = {
        nodes: nodes.map((node) => {
          // Build input_mapping for multi-input nodes
          const input_mapping = {};

          if (node.data.multi_input && node.data.input_slots) {
            // Find all edges targeting this node
            edges
              .filter((edge) => edge.target === node.id)
              .forEach((edge) => {
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
              ...(node.data.nodeType === 'input' && node.data.file_id
                ? {
                    file_id: node.data.file_id,
                  }
                : {}),
              ...(node.data.nodeType === 'tiff_json_to_dicom' && node.data.json_file_id
                ? {
                    json_file_id: node.data.json_file_id,
                  }
                : {}),
              ...(node.data.nodeType === 'apply_camera_calibration' && node.data.npz_file_id
                ? {
                    npz_file_id: node.data.npz_file_id,
                  }
                : {}),
              // Include input_mapping for multi-input nodes
              ...(Object.keys(input_mapping).length > 0
                ? {
                    input_mapping,
                  }
                : {}),
            },
          };
        }),
        edges: edges.map((edge) => ({
          source: edge.source,
          target: edge.target,
          sourceHandle: edge.sourceHandle,
          targetHandle: edge.targetHandle,
        })),
      };

      const response = await api.executePipeline(pipelineData);

      if (response.data.result && response.data.result.output_id) {
        const result = response.data.result;

        const resolveOutputMetadata = (output) => {
          const rawExt = (output?.output_ext || '').trim().toLowerCase();
          const outputType = (output?.output_type || '').trim().toLowerCase();
          let resolvedExt = '.png';

          if (rawExt) {
            resolvedExt = rawExt.startsWith('.') ? rawExt : `.${rawExt}`;
          } else {
            const outputName = (output?.output_name || '').trim().toLowerCase();
            if (outputName.includes('.')) {
              const nameExt = `.${outputName.split('.').pop()}`;
              if (nameExt && nameExt !== '.') {
                resolvedExt = nameExt;
              }
            } else if (outputType === 'artifact') {
              resolvedExt = '.npz';
            } else if (outputType === 'dicom') {
              resolvedExt = '.dcm';
            }
          }

          return {
            outputExt: resolvedExt,
            outputType: outputType || (resolvedExt === '.png' ? 'image' : 'artifact'),
          };
        };

        // Check if there are multiple outputs
        if (result.all_outputs && result.all_outputs.length > 0) {
          // Add status for each output
          result.all_outputs.forEach((output, index) => {
            const { outputExt, outputType } = resolveOutputMetadata(output);
            setProcessingStatus((prev) => [
              ...prev,
              {
                status: 'completed',
                message:
                  outputExt === '.dcm'
                    ? `DICOM output ${index + 1} generated successfully`
                    : outputExt === '.npz'
                      ? `Calibration artifact ${index + 1} generated successfully`
                      : `Output image ${index + 1} completed successfully`,
                output_id: output.output_id,
                output_ext: outputExt,
                output_name: output.output_name,
                output_type: outputType,
              },
            ]);
          });
        } else {
          // Single output
          const singleOutput =
            result.all_outputs && result.all_outputs[0] ? result.all_outputs[0] : null;
          const { outputExt, outputType } = resolveOutputMetadata(singleOutput);
          setProcessingStatus((prev) => [
            ...prev,
            {
              status: 'completed',
              message:
                outputExt === '.dcm'
                  ? 'DICOM output generated successfully'
                  : outputExt === '.npz'
                    ? 'Calibration artifact generated successfully'
                    : 'Pipeline completed successfully',
              output_id: result.output_id,
              output_ext: outputExt,
              output_name: singleOutput?.output_name,
              output_type: outputType,
            },
          ]);
        }
      }
    } catch (error) {
      setProcessingStatus((prev) => [
        ...prev,
        {
          status: 'error',
          message:
            (error.response && error.response.data && error.response.data.message) ||
            'Pipeline execution failed',
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  }, [nodes, edges, setIsProcessing, setProcessingStatus]);

  const clearPipeline = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setProcessingStatus([]);
    setNodeGroups([]);
    clearHistory();
  }, [setNodes, setEdges, setProcessingStatus, setNodeGroups, clearHistory]);

  return (
    <div className="app">
      <div className="toolbar">
        <button
          className="sidebar-toggle"
          onClick={toggleSidebar}
          title="Toggle sidebar"
          aria-label="Toggle sidebar"
        >
          ☰
        </button>
        <h1>Image Processing Pipeline</h1>

        <div className="toolbar-section">
          <input
            type="file"
            multiple
            onChange={handleMultipleFileUploads}
            style={{ display: 'none' }}
            id="file-upload"
            accept="image/*"
          />
          <label htmlFor="file-upload" className="toolbar-button" disabled={isBusy}>
            Upload Images
          </label>
          <button onClick={executePipeline} disabled={isBusy}>
            {isProcessing ? 'Processing...' : 'Execute Pipeline'}
          </button>
          <button onClick={clearPipeline} disabled={isBusy}>
            Clear All
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-section">
          <button onClick={handleUndo} disabled={!canUndo || isBusy} title="Undo (Ctrl+Z)">
            ↶Undo
          </button>
          <button onClick={handleRedo} disabled={!canRedo || isBusy} title="Redo (Ctrl+Shift+Z)">
            ↷Redo
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-section">
          <button onClick={handleCopy} title="Copy selected nodes (Ctrl+C)" disabled={isBusy}>
            📋Copy
          </button>
          <button
            onClick={handlePaste}
            disabled={!clipboardService.hasData() || isBusy}
            title="Paste nodes (Ctrl+V)"
          >
            📄Paste
          </button>
        </div>

        <div className="toolbar-divider" />

        <div className="toolbar-section">
          <button
            onClick={() => setShowSaveLoadModal(true)}
            title="Save/Load Pipeline (Ctrl+S)"
            disabled={isBusy}
          >
            💾Save/Load
          </button>
          <button
            onClick={toggleTheme}
            className="theme-toggle"
            title="Toggle Theme"
            disabled={isBusy}
          >
            {isDarkTheme ? '☀️' : '🌙'}
          </button>
          <button
            onClick={() => setShowShortcutsPanel(true)}
            title="Keyboard Shortcuts (? or F1)"
            disabled={isBusy}
          >
            ⌨️Help
          </button>
        </div>

        <span className="shortcut-hint">
          Shortcuts: ? or F1 = Help, Del = Delete, Ctrl+Z = Undo, Ctrl+C/V = Copy/Paste
        </span>
      </div>

      <div className="main-content">
        {sidebarOpen && (
          <div className="sidebar-overlay" onClick={toggleSidebar} aria-hidden="true" />
        )}
        <div className={`sidebar${sidebarOpen ? ' sidebar-open' : ''}`}>
          <button
            className="sidebar-close"
            onClick={toggleSidebar}
            title="Close sidebar"
            aria-label="Close sidebar"
            disabled={isBusy}
          >
            ✕
          </button>
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
            onInit={(instance) => {
              reactFlowInstance.current = instance;
            }}
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
              },
            }}
            selectNodesOnDrag={false}
            snapToGrid={false}
            snapGrid={[15, 15]}
            elevateEdgesOnSelect={true}
            nodesDraggable={!isBusy}
            nodesConnectable={!isBusy}
            elementsSelectable={!isBusy}
            panOnDrag={!isBusy}
            zoomOnScroll={!isBusy}
            fitView
          >
            <Controls />
            <Background color="#404040" gap={20} />
          </ReactFlow>
        </div>
      </div>

      <StatusPanel status={processingStatus} />

      <OutputPreviewPanel nodes={nodes} processingStatus={processingStatus} />

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
        onUploadingChange={setIsUploading}
      />

      {isBusy && (
        <div className="app-loading-overlay" role="status" aria-live="polite">
          <div className="app-loading-content">
            <div className="loading-spinner" />
            <span>{isUploading ? 'Uploading image...' : 'Executing pipeline...'}</span>
          </div>
        </div>
      )}

      <KeyboardShortcutsPanel
        isOpen={showShortcutsPanel}
        onClose={() => setShowShortcutsPanel(false)}
      />
    </div>
  );
}

export default App;
