class ClipboardService {
  constructor() {
    this.clipboard = null;
  }

  copy(data) {
    // Create a deep copy to prevent reference issues
    this.clipboard = JSON.parse(JSON.stringify(data));
  }

  paste() {
    return this.clipboard ? JSON.parse(JSON.stringify(this.clipboard)) : null;
  }

  hasData() {
    return this.clipboard !== null;
  }

  clear() {
    this.clipboard = null;
  }

  // Generate new IDs for pasted nodes to avoid conflicts
  generateNewNodeIds(nodes, edges) {
    const idMapping = {};
    const newNodes = nodes.map(node => {
      const newId = `${node.data.nodeType || 'node'}-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
      idMapping[node.id] = newId;
      return {
        ...node,
        id: newId,
        selected: true, // Select pasted nodes
        position: {
          x: node.position.x + 50, // Offset to avoid overlapping
          y: node.position.y + 50
        }
      };
    });

    const newEdges = edges
      .filter(edge => idMapping[edge.source] && idMapping[edge.target])
      .map(edge => ({
        ...edge,
        id: `${idMapping[edge.source]}-${idMapping[edge.target]}`,
        source: idMapping[edge.source],
        target: idMapping[edge.target]
      }));

    return { nodes: newNodes, edges: newEdges };
  }
}

export default new ClipboardService();