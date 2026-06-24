/**
 * DashboardGrid — 12-column CSS grid layout for dashboard cards.
 * Houses the Orb + all dashboard cards with edit mode toolbar.
 */
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDashboard } from '@/hooks/useDashboard';
import { useVoice } from '@/hooks/useVoice';
import DashboardCard from './DashboardCard';
import SystemStatsCard from './cards/SystemStatsCard';
import QuickActionsCard from './cards/QuickActionsCard';
import ModelSelectorCard from './cards/ModelSelectorCard';
import MemoryGraphCard from './cards/MemoryGraphCard';
import TimelineCard from './cards/TimelineCard';
import AgentNetworkCard from './cards/AgentNetworkCard';
import Orb from '@/components/orb/Orb';
import StatusDisplay from '@/components/orb/StatusDisplay';

export default function DashboardGrid() {
  const navigate = useNavigate();
  const dashboard = useDashboard();

  // Voice system
  const handleTranscript = useCallback((text) => {
    navigate('/chat', { state: { voiceMessage: text } });
  }, [navigate]);

  const handleWake = useCallback(() => {
    console.log('[MJ] Wake word detected — first activation');
  }, []);

  const voice = useVoice({ onTranscript: handleTranscript, onWake: handleWake });

  // Quick action → send as chat
  const handleQuickAction = useCallback((cmd) => {
    navigate('/chat', { state: { voiceMessage: cmd } });
  }, [navigate]);

  return (
    <div className="dashboard-wrapper">
      {/* Edit mode toolbar */}
      <div className={`dash-toolbar${dashboard.editing ? ' active' : ''}`}>
        {!dashboard.editing ? (
          <button className="dash-edit-btn" onClick={dashboard.enterEdit} title="Edit layout">
            ✎ Edit
          </button>
        ) : (
          <>
            <button className="dash-save-btn" onClick={dashboard.saveEdit}>✓ Save</button>
            <button className="dash-cancel-btn" onClick={dashboard.cancelEdit}>✕ Cancel</button>
            <button className="dash-reset-btn" onClick={dashboard.resetLayout}>↺ Reset</button>
          </>
        )}
      </div>

      {/* Grid */}
      <div className={`dash-grid${dashboard.editing ? ' editing' : ''}`}>
        {/* Orb Card */}
        <DashboardCard
          id="orb"
          style={dashboard.getCardStyle('orb')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'orb'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
          collapsible={false}
        >
          <div className="orb-section">
            <Orb state={voice.orbState} onClick={voice.handleOrbClick} />
            <StatusDisplay
              orbState={voice.orbState}
              micStatus={voice.micStatus}
              waveState={voice.waveState}
              listening={voice.listening}
              onMicToggle={voice.toggleListening}
            />
          </div>
        </DashboardCard>

        {/* System Monitor */}
        <DashboardCard
          id="sys-monitor"
          title="System Monitor"
          icon="⚡"
          style={dashboard.getCardStyle('sys-monitor')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'sys-monitor'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <SystemStatsCard />
        </DashboardCard>

        {/* Model Selector */}
        <DashboardCard
          id="model-selector"
          title="LLM Status"
          icon="🧠"
          style={dashboard.getCardStyle('model-selector')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'model-selector'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <ModelSelectorCard />
        </DashboardCard>

        {/* Quick Actions */}
        <DashboardCard
          id="quick-actions"
          title="Quick Actions"
          icon="⚡"
          style={dashboard.getCardStyle('quick-actions')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'quick-actions'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <QuickActionsCard onAction={handleQuickAction} />
        </DashboardCard>

        {/* Memory Graph */}
        <DashboardCard
          id="memory-graph"
          title="Memory Graph"
          icon="🧠"
          style={dashboard.getCardStyle('memory-graph')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'memory-graph'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <MemoryGraphCard />
        </DashboardCard>

        {/* Timeline */}
        <DashboardCard
          id="timeline"
          title="Activity Timeline"
          icon="📋"
          style={dashboard.getCardStyle('timeline')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'timeline'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <TimelineCard />
        </DashboardCard>

        {/* Agent Network */}
        <DashboardCard
          id="agent-network"
          title="Agent Network"
          icon="⚡"
          style={dashboard.getCardStyle('agent-network')}
          editing={dashboard.editing}
          dragging={dashboard.dragId === 'agent-network'}
          onDragStart={dashboard.onDragStart}
          onDragOver={dashboard.onDragOver}
          onDragEnd={dashboard.onDragEnd}
        >
          <AgentNetworkCard />
        </DashboardCard>
      </div>
    </div>
  );
}
