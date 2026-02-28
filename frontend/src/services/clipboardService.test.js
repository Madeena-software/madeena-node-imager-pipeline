import ClipboardService from './clipboardService';

// clipboardService is a singleton, so we test the exported instance
const clipboardService = ClipboardService;

describe('clipboardService', () => {
  beforeEach(() => {
    clipboardService.clear();
  });

  it('starts with no data', () => {
    expect(clipboardService.hasData()).toBe(false);
    expect(clipboardService.paste()).toBeNull();
  });

  it('copy and paste returns deep clone', () => {
    const data = { nodes: [{ id: '1', position: { x: 0, y: 0 } }], edges: [] };
    clipboardService.copy(data);

    expect(clipboardService.hasData()).toBe(true);

    const pasted = clipboardService.paste();
    expect(pasted).toEqual(data);
    // Must be a deep clone, not the same reference
    expect(pasted).not.toBe(data);
    expect(pasted.nodes[0]).not.toBe(data.nodes[0]);
  });

  it('paste returns a new clone each time', () => {
    clipboardService.copy({ nodes: [], edges: [] });

    const paste1 = clipboardService.paste();
    const paste2 = clipboardService.paste();
    expect(paste1).not.toBe(paste2);
  });

  it('clear removes data', () => {
    clipboardService.copy({ nodes: [] });
    clipboardService.clear();
    expect(clipboardService.hasData()).toBe(false);
  });

  it('generateNewNodeIds creates new IDs and offsets positions', () => {
    const nodes = [
      {
        id: 'old-1',
        data: { nodeType: 'resize' },
        position: { x: 100, y: 200 },
      },
      {
        id: 'old-2',
        data: { nodeType: 'blur' },
        position: { x: 300, y: 400 },
      },
    ];
    const edges = [{ id: 'e1', source: 'old-1', target: 'old-2' }];

    const result = clipboardService.generateNewNodeIds(nodes, edges);

    // New IDs should be different
    expect(result.nodes[0].id).not.toBe('old-1');
    expect(result.nodes[1].id).not.toBe('old-2');

    // Positions should be offset by 50
    expect(result.nodes[0].position.x).toBe(150);
    expect(result.nodes[0].position.y).toBe(250);

    // Edges should use the new IDs
    expect(result.edges[0].source).toBe(result.nodes[0].id);
    expect(result.edges[0].target).toBe(result.nodes[1].id);

    // Pasted nodes should be selected
    expect(result.nodes[0].selected).toBe(true);
  });

  it('generateNewNodeIds drops edges with missing source/target', () => {
    const nodes = [
      { id: 'a', data: { nodeType: 'x' }, position: { x: 0, y: 0 } },
    ];
    // Edge references a node that isn't in the pasted set
    const edges = [{ id: 'e1', source: 'a', target: 'missing' }];

    const result = clipboardService.generateNewNodeIds(nodes, edges);
    expect(result.edges).toHaveLength(0);
  });
});
