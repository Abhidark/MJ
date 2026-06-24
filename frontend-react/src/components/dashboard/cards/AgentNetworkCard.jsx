/**
 * AgentNetworkCard — shows all 10 agents with status, connections, and activity.
 * Visual node network of Zeus → specialized agents.
 */
import { useState, useEffect, useRef } from 'react';
import { zeusAPI } from '@/services/api';

const AGENTS = [
  { id: 'zeus', name: 'Zeus', role: 'Master Brain', icon: '⚡', color: '#00d4ff', pct: 60 },
  { id: 'hermes', name: 'Hermes', role: 'Communication', icon: '📨', color: '#00ff88', pct: 15 },
  { id: 'athena', name: 'Athena', role: 'Knowledge', icon: '📖', color: '#c8a0ff', pct: 50 },
  { id: 'hephaestus', name: 'Hephaestus', role: 'Developer', icon: '🔨', color: '#ffaa00', pct: 45 },
  { id: 'apollo', name: 'Apollo', role: 'Creative', icon: '🎨', color: '#ff6b9d', pct: 30 },
  { id: 'ares', name: 'Ares', role: 'Execution', icon: '🖥️', color: '#00ffcc', pct: 70 },
  { id: 'argus', name: 'Argus', role: 'Vision', icon: '👁️', color: '#44aaff', pct: 25 },
  { id: 'mnemosyne', name: 'Mnemosyne', role: 'Memory', icon: '🧠', color: '#ff88cc', pct: 40 },
  { id: 'chronos', name: 'Chronos', role: 'Time', icon: '⏰', color: '#88ff00', pct: 40 },
  { id: 'sentinel', name: 'Sentinel', role: 'Security', icon: '🛡️', color: '#ff4444', pct: 20 },
];

function statusLabel(pct) {
  if (pct >= 70) return 'ACTIVE';
  if (pct >= 40) return 'PARTIAL';
  if (pct > 0) return 'BASIC';
  return 'OFFLINE';
}

function statusColor(pct) {
  if (pct >= 70) return '#00ff88';
  if (pct >= 40) return '#ffaa00';
  if (pct > 0) return '#ff6644';
  return '#666';
}

function NetworkCanvas({ agents }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const cx = W / 2;
    const cy = H / 2;
    const R = Math.min(W, H) * 0.36;

    // Zeus center
    const zeus = agents[0];

    // Draw connections from Zeus to each agent
    agents.slice(1).forEach((agent, i) => {
      const angle = (Math.PI * 2 * i) / (agents.length - 1) - Math.PI / 2;
      const nx = cx + Math.cos(angle) * R;
      const ny = cy + Math.sin(angle) * R;

      // Connection line
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.strokeStyle = agent.color + '30';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Pulse dot on line (animated position)
      const t = 0.4 + (agent.pct / 100) * 0.3;
      const px = cx + (nx - cx) * t;
      const py = cy + (ny - cy) * t;
      ctx.beginPath();
      ctx.arc(px, py, 2, 0, Math.PI * 2);
      ctx.fillStyle = agent.color + '60';
      ctx.fill();

      // Agent node
      const nodeR = 8 + (agent.pct / 100) * 6;
      ctx.beginPath();
      ctx.arc(nx, ny, nodeR, 0, Math.PI * 2);
      ctx.fillStyle = agent.color + '20';
      ctx.fill();
      ctx.strokeStyle = agent.color + '80';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Agent icon text
      ctx.fillStyle = agent.color;
      ctx.font = '10px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(agent.icon, nx, ny);
    });

    // Zeus center node (larger)
    ctx.beginPath();
    ctx.arc(cx, cy, 16, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,212,255,0.15)';
    ctx.fill();
    ctx.strokeStyle = zeus.color + '80';
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.fillStyle = zeus.color;
    ctx.font = '14px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(zeus.icon, cx, cy);

  }, [agents]);

  return <canvas ref={canvasRef} width={200} height={200} className="agentnet-canvas" />;
}

function AgentRow({ agent }) {
  const stColor = statusColor(agent.pct);
  const stLabel = statusLabel(agent.pct);

  return (
    <div className="agentnet-row">
      <span className="agentnet-row-icon">{agent.icon}</span>
      <div className="agentnet-row-info">
        <span className="agentnet-row-name">{agent.name}</span>
        <span className="agentnet-row-role">{agent.role}</span>
      </div>
      <div className="agentnet-row-status">
        <span className="agentnet-row-pct" style={{ color: agent.color }}>{agent.pct}%</span>
        <span className="agentnet-status-pill" style={{ color: stColor, borderColor: stColor + '40' }}>
          {stLabel}
        </span>
      </div>
    </div>
  );
}

export default function AgentNetworkCard() {
  const [agents, setAgents] = useState(AGENTS);
  const [view, setView] = useState('graph');

  useEffect(() => {
    // Try to fetch live agent status from Zeus API
    let mounted = true;
    async function fetchAgentStatus() {
      try {
        const res = await zeusAPI.getModules();
        const modules = res?.data?.modules || res?.data || [];
        if (Array.isArray(modules) && modules.length > 0 && mounted) {
          setAgents(prev => prev.map(agent => {
            const mod = modules.find(m =>
              m.name?.toLowerCase().includes(agent.id) ||
              m.id?.toLowerCase().includes(agent.id)
            );
            if (mod && typeof mod.progress === 'number') {
              return { ...agent, pct: mod.progress };
            }
            return agent;
          }));
        }
      } catch { /* offline — use defaults */ }
    }
    fetchAgentStatus();
    return () => { mounted = false; };
  }, []);

  const activeCount = agents.filter(a => a.pct >= 70).length;
  const partialCount = agents.filter(a => a.pct >= 40 && a.pct < 70).length;

  return (
    <div className="agentnet-content">
      {/* Summary */}
      <div className="agentnet-summary">
        <span className="agentnet-stat">
          <span style={{ color: '#00ff88' }}>{activeCount}</span> active
        </span>
        <span className="agentnet-stat">
          <span style={{ color: '#ffaa00' }}>{partialCount}</span> partial
        </span>
        <span className="agentnet-stat">
          <span style={{ color: '#ff4444' }}>{10 - activeCount - partialCount}</span> basic
        </span>
      </div>

      {/* View toggle */}
      <div className="agentnet-toggle">
        <button
          className={`agentnet-toggle-btn${view === 'graph' ? ' active' : ''}`}
          onClick={() => setView('graph')}
        >◉ Graph</button>
        <button
          className={`agentnet-toggle-btn${view === 'list' ? ' active' : ''}`}
          onClick={() => setView('list')}
        >☰ List</button>
      </div>

      {/* Content */}
      {view === 'graph' ? (
        <div className="agentnet-graph-wrap">
          <NetworkCanvas agents={agents} />
        </div>
      ) : (
        <div className="agentnet-list">
          {agents.map(a => <AgentRow key={a.id} agent={a} />)}
        </div>
      )}
    </div>
  );
}
