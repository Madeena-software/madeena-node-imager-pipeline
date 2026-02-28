import PipelineStorage from './pipelineStorage';

// pipelineStorage is a singleton
const storage = PipelineStorage;

describe('pipelineStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('getAllPipelines returns empty object by default', () => {
    expect(storage.getAllPipelines()).toEqual({});
  });

  it('savePipeline and loadPipeline round-trip', () => {
    const nodes = [{ id: '1' }];
    const edges = [{ source: '1', target: '2' }];

    const saved = storage.savePipeline('test-pipe', nodes, edges);
    expect(saved).toBe(true);

    const loaded = storage.loadPipeline('test-pipe');
    expect(loaded).not.toBeNull();
    expect(loaded.name).toBe('test-pipe');
    expect(loaded.nodes).toEqual(nodes);
    expect(loaded.edges).toEqual(edges);
    expect(loaded.metadata.createdAt).toBeDefined();
  });

  it('deletePipeline removes pipeline', () => {
    storage.savePipeline('to-delete', [], []);
    expect(storage.loadPipeline('to-delete')).not.toBeNull();

    storage.deletePipeline('to-delete');
    expect(storage.loadPipeline('to-delete')).toBeNull();
  });

  it('getAllPipelines lists all saved', () => {
    storage.savePipeline('p1', [], []);
    storage.savePipeline('p2', [], []);

    const all = storage.getAllPipelines();
    expect(Object.keys(all)).toEqual(expect.arrayContaining(['p1', 'p2']));
  });

  it('loadPipeline returns null for non-existent', () => {
    expect(storage.loadPipeline('no-such-pipeline')).toBeNull();
  });

  it('handles corrupted localStorage gracefully', () => {
    localStorage.setItem('image_processing_pipelines', 'not-json');
    expect(storage.getAllPipelines()).toEqual({});
  });

  it('importPipeline rejects invalid JSON', async () => {
    const badFile = new Blob(['not valid json'], { type: 'text/plain' });
    await expect(storage.importPipeline(badFile)).rejects.toThrow('Invalid pipeline file');
  });

  it('importPipeline parses valid JSON', async () => {
    const pipeline = { name: 'imported', nodes: [], edges: [] };
    const file = new Blob([JSON.stringify(pipeline)], { type: 'application/json' });

    const result = await storage.importPipeline(file);
    expect(result.name).toBe('imported');
  });
});
