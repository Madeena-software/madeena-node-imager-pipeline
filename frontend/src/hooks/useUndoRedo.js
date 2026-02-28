import { useCallback, useState } from 'react';

const MAX_HISTORY_SIZE = 50;

const useUndoRedo = (initialState) => {
  const [history, setHistory] = useState([initialState]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const setState = useCallback((newState) => {
    const newHistory = history.slice(0, currentIndex + 1);
    newHistory.push(newState);
    
    // Cap history size to prevent memory leaks
    if (newHistory.length > MAX_HISTORY_SIZE) {
      const trimCount = newHistory.length - MAX_HISTORY_SIZE;
      newHistory.splice(0, trimCount);
    }
    
    setHistory(newHistory);
    setCurrentIndex(newHistory.length - 1);
  }, [history, currentIndex]);

  const undo = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
      return history[currentIndex - 1];
    }
    return history[currentIndex];
  }, [currentIndex, history]);

  const redo = useCallback(() => {
    if (currentIndex < history.length - 1) {
      setCurrentIndex(currentIndex + 1);
      return history[currentIndex + 1];
    }
    return history[currentIndex];
  }, [currentIndex, history]);

  const canUndo = currentIndex > 0;
  const canRedo = currentIndex < history.length - 1;

  const currentState = history[currentIndex];

  return {
    state: currentState,
    setState,
    undo,
    redo,
    canUndo,
    canRedo,
    clearHistory: () => {
      setHistory([initialState]);
      setCurrentIndex(0);
    }
  };
};

export default useUndoRedo;