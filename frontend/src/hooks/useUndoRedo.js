import { useCallback, useRef, useState } from 'react';

const MAX_HISTORY_SIZE = 50;

/**
 * Generic undo/redo hook.
 *
 * Uses a ref for the history stack so that `setState`, `undo`, and `redo`
 * always see the latest values — avoiding the stale-closure issue that
 * occurs when depending on `history` / `currentIndex` state directly
 * inside `useCallback`.
 */
const useUndoRedo = (initialState) => {
  const historyRef = useRef([initialState]);
  const indexRef = useRef(0);

  // A counter that forces a re-render whenever we touch the timeline.
  const [, setTick] = useState(0);
  const bump = () => setTick((t) => t + 1);

  const setState = useCallback((newState) => {
    const h = historyRef.current.slice(0, indexRef.current + 1);
    h.push(newState);

    // Cap history size
    if (h.length > MAX_HISTORY_SIZE) {
      h.splice(0, h.length - MAX_HISTORY_SIZE);
    }

    historyRef.current = h;
    indexRef.current = h.length - 1;
    bump();
  }, []);

  const undo = useCallback(() => {
    if (indexRef.current > 0) {
      indexRef.current -= 1;
      bump();
      return historyRef.current[indexRef.current];
    }
    return historyRef.current[indexRef.current];
  }, []);

  const redo = useCallback(() => {
    if (indexRef.current < historyRef.current.length - 1) {
      indexRef.current += 1;
      bump();
      return historyRef.current[indexRef.current];
    }
    return historyRef.current[indexRef.current];
  }, []);

  const clearHistory = useCallback(() => {
    historyRef.current = [initialState];
    indexRef.current = 0;
    bump();
  }, [initialState]);

  const canUndo = indexRef.current > 0;
  const canRedo = indexRef.current < historyRef.current.length - 1;
  const state = historyRef.current[indexRef.current];

  return { state, setState, undo, redo, canUndo, canRedo, clearHistory };
};

export default useUndoRedo;