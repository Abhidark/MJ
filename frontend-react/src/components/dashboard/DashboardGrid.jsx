/**
 * DashboardGrid -- 12-column CSS grid layout for dashboard cards.
 * Houses the Orb + all dashboard cards with edit mode toolbar.
 * Manages drag-to-reposition (mouse-based, grid-snapping) and
 * corner-drag resize + toolbar button resize.
 */
import { useCallback, useRef, useState } from 'react';
import { useApp } from '@/context/AppContext';
import { useDashboard } from '@/hooks/useDashboard';
import { useVoice } from '@/hooks/useVoice';
import DashboardCard from './DashboardCard';
import SystemStatsCard from './cards/SystemStatsCard';
import QuickActionsCard from './cards/QuickActionsCard';
import ModelSelectorCard from './cards/ModelSelectorCard';
import MemoryGraphCard from './cards/MemoryGraphCard';
import TimelineCard from './cards/TimelineCard';
import AgentNetworkCard from './cards/AgentNetworkCard';
import AICoreCard from './cards/AICoreCard';
import LiveIntelCard from './cards/LiveIntelCard';
import QuickCommandsCard from './cards/QuickCommandsCard';
import SystemStatsWidgetCard from './cards/SystemStatsWidgetCard';
import SmartSuggestionsCard from './cards/SmartSuggestionsCard';
import GestureControlCard from './cards/GestureControlCard';
import HoloToggle from './cards/HoloToggle';
import VoiceLangSelector from './cards/VoiceLangSelector';
import Orb from '@/components/orb/Orb';
import StatusDisplay from '@/components/orb/StatusDisplay';

export default function DashboardGrid() {
  const { dispatch } = useApp();
  const dashboard = useDashboard();
  const gridRef = useRef(null);

  // Drag state: tracks which card is being dragged and placeholder position
  const [dragState, setDragState] = useState(null);

  // --- Voice ---
  const handleTranscript = useCallback((text) => {
    dispatch({ type: 'OPEN_CHAT_PANEL', payload: text });
  }, [dispatch]);

  const handleWake = useCallback(() => {
    console.log('[MJ] Wake word detected -- first activation');
  }, []);

  const voice = useVoice({ onTranscript: handleTranscript, onWake: handleWake });

  const handleQuickAction = useCallback((cmd) => {
    dispatch({ type: 'OPEN_CHAT_PANEL', payload: cmd });
  }, [dispatch]);

  // --- Grid cell calculation (matches old UI getGridCell) ---
  const getGridCell = useCallback((clientX, clientY) => {
    const grid = gridRef.current;
    if (!grid) return { col: 1, row: 1 };
    const rect = grid.getBoundingClientRect();
    const cs = getComputedStyle(grid);
    const padL = parseFloat(cs.paddingLeft);
    const padR = parseFloat(cs.paddingRight);
    const padT = parseFloat(cs.paddingTop);
    const gap = 12;
    const x = clientX - rect.left - padL;
    const y = clientY - rect.top - padT;
    const colW = (rect.width - padL - padR - 11 * gap) / 12;
    const col = Math.max(1, Math.min(12, Math.floor(x / (colW + gap)) + 1));
    const rowH = 40 + gap;
    const row = Math.max(1, Math.floor(y / rowH) + 1);
    return { col, row };
  }, []);

  // --- Drag: mouse-based with ghost + grid-snapping placeholder ---
  const handleDragStart = useCallback((cardId, e) => {
    if (!dashboard.editing) return;
    e.preventDefault();
    e.stopPropagation();

    const cardEl = e.target.closest('.dash-card');
    if (!cardEl) return;
    const rect = cardEl.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const offsetY = e.clientY - rect.top;
    const pos = dashboard.layout[cardId];
    if (!pos) return;

    // Create ghost element imperatively for smooth 60fps tracking
    const ghost = document.createElement('div');
    ghost.className = 'drag-ghost-el';
    ghost.style.cssText =
      `position:fixed;pointer-events:none;z-index:99999;opacity:0.7;` +
      `width:${rect.width}px;height:${rect.height}px;` +
      `left:${rect.left}px;top:${rect.top}px;` +
      `border:2px solid #ffd900;border-radius:12px;` +
      `box-shadow:0 0 30px rgba(255,217,0,0.3);` +
      `background:rgba(2,12,25,0.5);transition:none;`;
    document.body.appendChild(ghost);

    // Set placeholder at current position
    setDragState({
      cardId,
      col: pos.col,
      row: pos.row,
      w: pos.w,
      h: pos.h,
    });

    const onMove = (ev) => {
      // Ghost follows mouse (imperative for smoothness)
      ghost.style.left = (ev.clientX - offsetX) + 'px';
      ghost.style.top = (ev.clientY - offsetY) + 'px';

      // Snap placeholder to grid cell
      const cell = getGridCell(ev.clientX, ev.clientY);
      const newCol = Math.max(1, Math.min(13 - pos.w, cell.col));
      const newRow = Math.max(1, cell.row);
      setDragState(prev => prev ? { ...prev, col: newCol, row: newRow } : null);
    };

    const onUp = (ev) => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);

      // Apply final position
      const cell = getGridCell(ev.clientX, ev.clientY);
      const newCol = Math.max(1, Math.min(13 - pos.w, cell.col));
      const newRow = Math.max(1, cell.row);
      dashboard.updateCardPos(cardId, { col: newCol, row: newRow });

      // Cleanup
      ghost.remove();
      setDragState(null);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [dashboard.editing, dashboard.layout, dashboard.updateCardPos, getGridCell]);

  // --- Resize: corner drag handle ---
  const handleResizeStart = useCallback((cardId, e) => {
    if (!dashboard.editing) return;
    e.preventDefault();
    e.stopPropagation();

    const pos = dashboard.layout[cardId];
    if (!pos) return;
    const startX = e.clientX;
    const startY = e.clientY;

    const grid = gridRef.current;
    if (!grid) return;
    const cs = getComputedStyle(grid);
    const padL = parseFloat(cs.paddingLeft);
    const padR = parseFloat(cs.paddingRight);
    const gap = 12;
    const colW = (grid.getBoundingClientRect().width - padL - padR - 11 * gap) / 12;
    const rowH = 40 + gap;

    const onMove = (ev) => {
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;
      const newW = Math.max(1, Math.min(13 - pos.col, pos.w + Math.round(dx / (colW + gap))));
      const newH = Math.max(1, pos.h + Math.round(dy / rowH));
      dashboard.updateCardPos(cardId, { w: newW, h: newH });
    };

    const onUp = () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [dashboard.editing, dashboard.layout, dashboard.updateCardPos]);

  // --- Toolbar resize buttons ---
  const handleWider = useCallback((cardId) => {
    const p = dashboard.layout[cardId];
    if (p && p.col + p.w <= 12) dashboard.updateCardPos(cardId, { w: p.w + 1 });
  }, [dashboard.layout, dashboard.updateCardPos]);

  const handleNarrower = useCallback((cardId) => {
    const p = dashboard.layout[cardId];
    if (p && p.w > 1) dashboard.updateCardPos(cardId, { w: p.w - 1 });
  }, [dashboard.layout, dashboard.updateCardPos]);

  const handleTaller = useCallback((cardId) => {
    const p = dashboard.layout[cardId];
    if (p) dashboard.updateCardPos(cardId, { h: p.h + 1 });
  }, [dashboard.layout, dashboard.updateCardPos]);

  const handleShorter = useCallback((cardId) => {
    const p = dashboard.layout[cardId];
    if (p && p.h > 1) dashboard.updateCardPos(cardId, { h: p.h - 1 });
  }, [dashboard.layout, dashboard.updateCardPos]);

  const handleResetCard = useCallback((cardId) => {
    const def = dashboard.getDefaultPos(cardId);
    if (def) dashboard.updateCardPos(cardId, { ...def, bg: '', minH: '' });
  }, [dashboard.getDefaultPos, dashboard.updateCardPos]);

  const handleColorChange = useCallback((cardId, color) => {
    dashboard.updateCardPos(cardId, { bg: color });
  }, [dashboard.updateCardPos]);

  // --- Edit actions object passed to every DashboardCard ---
  const editActions = {
    onDragStart: handleDragStart,
    onResizeStart: handleResizeStart,
    onWider: handleWider,
    onNarrower: handleNarrower,
    onTaller: handleTaller,
    onShorter: handleShorter,
    onResetCard: handleResetCard,
    onColorChange: handleColorChange,
  };

  // --- Helper: common props for every card ---
  const cp = (id) => ({
    id,
    style: dashboard.getCardStyle(id),
    editing: dashboard.editing,
    dragHidden: dragState?.cardId === id,
    pos: dashboard.layout[id],
    editActions,
  });

  return (
    <div className="dashboard-wrapper">
      {/* Edit mode toolbar */}
      <div className={`dash-toolbar${dashboard.editing ? ' active' : ''}`}>
        {!dashboard.editing ? (
          <button className="dash-edit-btn" onClick={dashboard.enterEdit} title="Edit layout">
            {'✎'} Edit
          </button>
        ) : (
          <>
            <button className="dash-save-btn" onClick={dashboard.saveEdit}>{'✓'} Save</button>
            <button className="dash-cancel-btn" onClick={dashboard.cancelEdit}>x Cancel</button>
            <button className="dash-reset-btn" onClick={dashboard.resetLayout}>{'↺'} Reset</button>
          </>
        )}
      </div>

      {/* Grid */}
      <div ref={gridRef} className={`dash-grid${dashboard.editing ? ' editing' : ''}`}>

        {/* -- Orb Card -- */}
        <DashboardCard {...cp('orb')} collapsible={false}>
          <div className="orb-section">
            <Orb state={voice.orbState} onClick={voice.handleOrbClick} />
            <StatusDisplay
              orbState={voice.orbState}
              micStatus={voice.micStatus}
              waveState={voice.waveState}
              listening={voice.listening}
              onMicToggle={voice.toggleListening}
            />
            <HoloToggle />
          </div>
        </DashboardCard>

        {/* -- AI Core Overview -- */}
        <DashboardCard {...cp('ai-core')}>
          <AICoreCard />
        </DashboardCard>

        {/* -- Live Intelligence -- */}
        <DashboardCard {...cp('live-intel')}>
          <LiveIntelCard />
        </DashboardCard>

        {/* -- Quick Commands -- */}
        <DashboardCard {...cp('quick-cmd')}>
          <QuickCommandsCard onAction={handleQuickAction} />
        </DashboardCard>

        {/* -- System Monitor -- */}
        <DashboardCard {...cp('sys-monitor')} title="System Monitor" icon="⚡">
          <SystemStatsCard />
        </DashboardCard>

        {/* -- Model Selector -- */}
        <DashboardCard {...cp('model-selector')} title="LLM Status" icon="🧠">
          <ModelSelectorCard />
        </DashboardCard>

        {/* -- Quick Actions -- */}
        <DashboardCard {...cp('quick-actions')} title="Quick Actions" icon="⚡">
          <QuickActionsCard onAction={handleQuickAction} />
        </DashboardCard>

        {/* -- System Stats Widget -- */}
        <DashboardCard {...cp('sys-stats')}>
          <SystemStatsWidgetCard />
        </DashboardCard>

        {/* -- Smart Suggestions -- */}
        <DashboardCard {...cp('smart-suggest')}>
          <SmartSuggestionsCard onAction={handleQuickAction} />
        </DashboardCard>

        {/* -- Memory Graph -- */}
        <DashboardCard {...cp('memory-graph')} title="Memory Graph" icon="🧠">
          <MemoryGraphCard />
        </DashboardCard>

        {/* -- Timeline -- */}
        <DashboardCard {...cp('timeline')} title="Activity Timeline" icon="📋">
          <TimelineCard />
        </DashboardCard>

        {/* -- Agent Network -- */}
        <DashboardCard {...cp('agent-network')} title="Agent Network" icon="⚡">
          <AgentNetworkCard />
        </DashboardCard>

        {/* -- Gesture Control -- */}
        <DashboardCard {...cp('gesture-ctrl')}>
          <GestureControlCard />
        </DashboardCard>

        {/* -- Voice Language Selector -- */}
        <DashboardCard {...cp('voice-lang')}>
          <VoiceLangSelector />
        </DashboardCard>

        {/* -- Drag placeholder (grid-snapped) -- */}
        {dragState && (
          <div
            className="drag-placeholder"
            style={{
              gridColumn: `${dragState.col} / span ${dragState.w}`,
              gridRow: `${dragState.row} / span ${dragState.h}`,
            }}
          />
        )}
      </div>
    </div>
  );
}
