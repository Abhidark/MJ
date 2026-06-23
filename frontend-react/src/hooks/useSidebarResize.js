import { useState, useEffect, useCallback, useRef } from 'react';

const MIN_WIDTH = 80;
const MAX_WIDTH = 380;
const ICONS_ONLY_THRESHOLD = 120;

export function useSidebarResize(initialWidth = 210) {
  const saved = parseInt(localStorage.getItem('mj-sidebar-width'), 10);
  const [width, setWidth] = useState(
    saved >= MIN_WIDTH && saved <= MAX_WIDTH ? saved : initialWidth
  );
  const [isResizing, setIsResizing] = useState(false);
  const startX = useRef(0);
  const startW = useRef(0);

  const iconsOnly = width < ICONS_ONLY_THRESHOLD;

  const onMouseDown = useCallback((e) => {
    e.preventDefault();
    startX.current = e.clientX;
    startW.current = width;
    setIsResizing(true);
  }, [width]);

  useEffect(() => {
    if (!isResizing) return;

    const onMouseMove = (e) => {
      const delta = e.clientX - startX.current;
      const newW = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startW.current + delta));
      setWidth(newW);
      document.documentElement.style.setProperty('--sidebar-w', newW + 'px');
    };

    const onMouseUp = () => {
      setIsResizing(false);
      localStorage.setItem('mj-sidebar-width', String(width));
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, [isResizing, width]);

  // Sync CSS var on mount
  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-w', width + 'px');
  }, [width]);

  return { width, isResizing, iconsOnly, onMouseDown };
}
