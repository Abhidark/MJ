/**
 * MemoryGraphCard — visualizes memory usage: chat history, KB docs, notes, core memory.
 * Fetches from backend APIs; shows placeholder bars when offline.
 */
import { useState, useEffect, useRef } from 'react';
import { chatAPI, knowledgeAPI, memoryAPI } from '@/services/api';

const CATEGORIES = [
  { key: 'chats', label: 'Chat Sessions', icon: '💬', color: '#00d4ff' },
  { key: 'kb', label: 'KB Documents', icon: '📚', color: '#00ff88' },
  { key: 'core', label: 'Core Memories', icon: '🧠', color: '#c8a0ff' },
  { key: 'context', label: 'Context Memory', icon: '📋', color: '#ffaa00' },
];

function MiniBar({ value, max, color }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="memgraph-bar">
      <div className="memgraph-bar-fill" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

function NodeGraph({ data }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const total = data.reduce((s, d) => s + d.value, 0);
    if (total === 0) return;

    const cx = W / 2;
    const cy = H / 2;
    const R = 40;

    // Draw center node
    ctx.beginPath();
    ctx.arc(cx, cy, 14, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0,212,255,0.15)';
    ctx.fill();
    ctx.strokeStyle = 'rgba(0,212,255,0.5)';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = '#00d4ff';
    ctx.font = '8px Orbitron, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('MJ', cx, cy);

    // Draw satellite nodes
    data.forEach((d, i) => {
      const angle = (Math.PI * 2 * i) / data.length - Math.PI / 2;
      const nx = cx + Math.cos(angle) * R;
      const ny = cy + Math.sin(angle) * R;
      const size = Math.max(6, Math.min(16, (d.value / Math.max(total, 1)) * 40));

      // Connection line
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(nx, ny);
      ctx.strokeStyle = d.color + '40';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Node circle
      ctx.beginPath();
      ctx.arc(nx, ny, size, 0, Math.PI * 2);
      ctx.fillStyle = d.color + '25';
      ctx.fill();
      ctx.strokeStyle = d.color + '80';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Value text
      ctx.fillStyle = d.color;
      ctx.font = 'bold 7px JetBrains Mono, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(d.value), nx, ny);
    });
  }, [data]);

  return <canvas ref={canvasRef} width={120} height={120} className="memgraph-canvas" />;
}

export default function MemoryGraphCard() {
  const [data, setData] = useState({
    chats: 0,
    kb: 0,
    core: 0,
    context: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function fetchAll() {
      try {
        const results = await Promise.allSettled([
          chatAPI.getChats(),
          knowledgeAPI.getStats(),
          memoryAPI.getCoreMemory(),
          memoryAPI.getContextMemory(),
        ]);

        if (!mounted) return;

        const chats = results[0].status === 'fulfilled'
          ? (results[0].value?.data?.chats?.length || results[0].value?.data?.length || 0)
          : 0;
        const kb = results[1].status === 'fulfilled'
          ? (results[1].value?.data?.total_documents || results[1].value?.data?.count || 0)
          : 0;
        const core = results[2].status === 'fulfilled'
          ? (results[2].value?.data?.memories?.length || results[2].value?.data?.length || 0)
          : 0;
        const context = results[3].status === 'fulfilled'
          ? (results[3].value?.data?.entries?.length || results[3].value?.data?.length || 0)
          : 0;

        setData({ chats, kb, core, context });
      } catch {
        // Offline — keep zeros
      }
      setLoading(false);
    }
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const maxVal = Math.max(...Object.values(data), 1);
  const totalItems = Object.values(data).reduce((a, b) => a + b, 0);

  const graphData = CATEGORIES.map(c => ({
    ...c,
    value: data[c.key],
  }));

  if (loading) {
    return <div className="memgraph-loading">Connecting to memory...</div>;
  }

  return (
    <div className="memgraph-content">
      <div className="memgraph-top">
        <NodeGraph data={graphData} />
        <div className="memgraph-total">
          <div className="memgraph-total-num">{totalItems}</div>
          <div className="memgraph-total-label">TOTAL ENTRIES</div>
        </div>
      </div>

      <div className="memgraph-rows">
        {CATEGORIES.map(cat => (
          <div key={cat.key} className="memgraph-row">
            <span className="memgraph-row-icon">{cat.icon}</span>
            <span className="memgraph-row-label">{cat.label}</span>
            <MiniBar value={data[cat.key]} max={maxVal} color={cat.color} />
            <span className="memgraph-row-val" style={{ color: cat.color }}>{data[cat.key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
