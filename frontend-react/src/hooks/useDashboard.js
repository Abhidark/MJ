import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useDashboard — manages card layout positions, drag-to-reorder, edit mode
 *
 * Saves/loads layout from localStorage (v4 format matching original).
 * 12-column CSS grid with explicit col/row/w/h per card.
 */

const STORAGE_KEY = 'mj-dash-layout-v4';

const DEFAULT_LAYOUT = {
  'orb':           { col: 1,  row: 1,  w: 5,  h: 6 },
  'sys-monitor':   { col: 6,  row: 1,  w: 4,  h: 6 },
  'model-selector':{ col: 10, row: 1,  w: 3,  h: 6 },
  'quick-actions': { col: 1,  row: 7,  w: 12, h: 3 },
};

function loadLayout() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_LAYOUT };
    const parsed = JSON.parse(raw);
    if (parsed.v === 4 && parsed.layout) return parsed.layout;
    return { ...DEFAULT_LAYOUT };
  } catch {
    return { ...DEFAULT_LAYOUT };
  }
}

function saveLayout(layout) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ layout, v: 4 }));
  } catch {}
}

export function useDashboard() {
  const [layout, setLayout] = useState(loadLayout);
  const [editing, setEditing] = useState(false);
  const [dragId, setDragId] = useState(null);
  const preEditRef = useRef(null);

  // Save whenever layout changes (outside edit mode)
  useEffect(() => {
    if (!editing) saveLayout(layout);
  }, [layout, editing]);

  const enterEdit = useCallback(() => {
    preEditRef.current = { ...layout };
    setEditing(true);
  }, [layout]);

  const saveEdit = useCallback(() => {
    saveLayout(layout);
    setEditing(false);
    preEditRef.current = null;
  }, [layout]);

  const cancelEdit = useCallback(() => {
    if (preEditRef.current) setLayout(preEditRef.current);
    setEditing(false);
    preEditRef.current = null;
  }, []);

  const resetLayout = useCallback(() => {
    setLayout({ ...DEFAULT_LAYOUT });
    saveLayout(DEFAULT_LAYOUT);
    setEditing(false);
    preEditRef.current = null;
  }, []);

  // ─── Drag handlers ───
  const onDragStart = useCallback((cardId) => {
    if (!editing) return;
    setDragId(cardId);
  }, [editing]);

  const onDragOver = useCallback((targetId) => {
    if (!editing || !dragId || dragId === targetId) return;
    // Swap positions
    setLayout(prev => {
      const next = { ...prev };
      const dragPos = { ...next[dragId] };
      const targetPos = { ...next[targetId] };
      next[dragId] = targetPos;
      next[targetId] = dragPos;
      return next;
    });
    setDragId(targetId); // follow the dragged card
  }, [editing, dragId]);

  const onDragEnd = useCallback(() => {
    setDragId(null);
  }, []);

  // Card style from layout
  const getCardStyle = useCallback((cardId) => {
    const pos = layout[cardId];
    if (!pos) return {};
    return {
      gridColumn: `${pos.col} / span ${pos.w}`,
      gridRow: `${pos.row} / span ${pos.h}`,
    };
  }, [layout]);

  return {
    layout,
    editing,
    dragId,
    enterEdit,
    saveEdit,
    cancelEdit,
    resetLayout,
    onDragStart,
    onDragOver,
    onDragEnd,
    getCardStyle,
  };
}
