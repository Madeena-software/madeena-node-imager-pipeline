import { renderHook, act } from '@testing-library/react';
import useUndoRedo from './useUndoRedo';

describe('useUndoRedo', () => {
  const initial = { value: 0 };

  it('returns initial state', () => {
    const { result } = renderHook(() => useUndoRedo(initial));
    expect(result.current.state).toEqual(initial);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });

  it('pushes new states', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    act(() => {
      result.current.setState({ value: 1 });
    });

    expect(result.current.state).toEqual({ value: 1 });
    expect(result.current.canUndo).toBe(true);
    expect(result.current.canRedo).toBe(false);
  });

  it('undo returns to previous state', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    act(() => {
      result.current.setState({ value: 1 });
    });

    let undone;
    act(() => {
      undone = result.current.undo();
    });

    expect(undone).toEqual(initial);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(true);
  });

  it('redo restores undone state', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    act(() => {
      result.current.setState({ value: 1 });
    });
    act(() => {
      result.current.undo();
    });

    let redone;
    act(() => {
      redone = result.current.redo();
    });

    expect(redone).toEqual({ value: 1 });
    expect(result.current.canRedo).toBe(false);
  });

  it('new state after undo discards redo history', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    act(() => {
      result.current.setState({ value: 1 });
    });
    act(() => {
      result.current.setState({ value: 2 });
    });
    act(() => {
      result.current.undo();
    });
    // Now at value: 1, redo would go to value: 2
    act(() => {
      result.current.setState({ value: 99 });
    });

    // Redo should no longer be possible
    expect(result.current.canRedo).toBe(false);
    expect(result.current.state).toEqual({ value: 99 });
  });

  it('clearHistory resets to initial', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    act(() => {
      result.current.setState({ value: 1 });
      result.current.setState({ value: 2 });
    });

    act(() => {
      result.current.clearHistory();
    });

    expect(result.current.state).toEqual(initial);
    expect(result.current.canUndo).toBe(false);
    expect(result.current.canRedo).toBe(false);
  });

  it('respects max history size (50)', () => {
    const { result } = renderHook(() => useUndoRedo(initial));

    // Push 60 states
    for (let i = 1; i <= 60; i++) {
      act(() => {
        result.current.setState({ value: i });
      });
    }

    // Should still be at value: 60
    expect(result.current.state).toEqual({ value: 60 });

    // Undo should work up to the cap, not all 60
    let undoCount = 0;
    while (result.current.canUndo) {
      act(() => {
        result.current.undo();
      });
      undoCount++;
    }
    // max 50 entries -> 49 undos max
    expect(undoCount).toBeLessThanOrEqual(49);
  });
});
