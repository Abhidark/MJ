import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useDashboard -- manages card layout positions, edit mode, save/load/reset.
 *
 * v7 format: { layout: { cardId: { col, row, w, h, bg?, minH? } }, v: 7 }
 * 12-column CSS grid with explicit col/row/w/h per card.
 */

const STORAGE_KEY = 'mj-dash-layout-v7';

const DEFAULT_LAYOUT = {
  'ai-core':       { col: 1,  row: 1,  w: 4,  h: 5 },
  'live-intel':    { col: 5,  row: 1,  w: 4,  h: 5 },
  'quick-cmd':     { col: 9,  row: 1,  w: 4,  h: 5 },
  'sys-monitor':   { col: 1,  row: 6,  w: 3,  h: 7 },
  'orb':           { col: 4,  row: 6,  w: 5,  h: 7 },
  'sys-stats':     { col: 9,  row: 6,  w: 4,  h: 4 },
  'smart-suggest': { col: 9,  row: 10, w: 4,  h: 3 },
  'model-selector':{ col: 1,  row: 13, w: 5,  h: 4 },
  'quick-actions': { col: 6,  row: 13, w: 7,  h: 4 },
  'memory-graph':  { col: 1,  row: 17, w: 4,  h: 5 },
  'timeline':      { col: 5,  row: 17, w: 4,  h: 5 },
  'agent-network': { col: 9,  row: 17, w: 4,  h: 5 },
  'gesture-ctrl':  { col: 1,  row: 22, w: 3,  h: 4 },
  'voice-lang':    { col: 4,  row: 22, w: 3,  h: 4 },
};

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function loadLayout() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return deepClone(DEFAULT_LAYOUT);
    const parsed = JSON.parse(raw);
    if (parsed.v === 7 && parsed.layout) return parsed.layout;
    return deepClone(DEFAULT_LAYOUT);
  } catch {
    return deepClone(DEFAULT_LAYOUT);
  }
}

function saveLayout(layout) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ layout, v: 7 }));
  } catch { /* silent */ }
}

export function useDashboard() {
  const [layout, setLayout] = useState(loadLayout);
  const [editing, setEditing] = useState(false);
  const preEditRef = useRef(null);

  // Persist layout when not editing
  useEffect(() => {
    if (!editing) saveLayout(layout);
  }, [layout, editing]);

  const enterEdit = useCallback(() => {
    preEditRef.current = deepClone(layout);
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
    const def = deepClone(DEFAULT_LAYOUT);
    setLayout(def);
    saveLayout(def);
    setEditing(false);
    preEditRef.current = null;
  }, []);

  /** Update a single card's position/style */
  const updateCardPos = useCallback((cardId, changes) => {
    setLayout(prev => ({
      ...prev,
      [cardId]: { ...prev[cardId], ...changes },
    }));
  }, []);

  /** Get default position for a card (for per-card reset) */
  const getDefaultPos = useCallback((cardId) => {
    return DEFAULT_LAYOUT[cardId] || null;
  }, []);

  /** Build inline style for a card from its layout entry */
  const getCardStyle = useCallback((cardId) => {
    const pos = layout[cardId];
    if (!pos) return {};
    const style = {
      gridColumn: `${pos.col} / span ${pos.w}`,
      gridRow: `${pos.row} / span ${pos.h}`,
    };
    if (pos.bg) style.background = pos.bg;
    if (pos.minH) style.minHeight = pos.minH;
    return style;
  }, [layout]);

  return {
    layout,
    editing,
    enterEdit,
    saveEdit,
    cancelEdit,
    resetLayout,
    updateCardPos,
    getDefaultPos,
    getCardStyle,
  };
}
