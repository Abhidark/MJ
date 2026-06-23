import { useState, useRef, useCallback, useEffect } from 'react';

// ─── AI Processing Flow Visualization ───
// Resizable right panel showing live AI pipeline stages

const FLOW_STAGES = [
  { id: 'input', label: 'INPUT', icon: '📝', desc: 'User message received' },
  { id: 'intent', label: 'INTENT', icon: '🧠', desc: 'Zeus analyzes intent & selects agent' },
  { id: 'memory', label: 'MEMORY', icon: '💾', desc: 'Context + memory retrieval' },
  { id: 'routing', label: 'ROUTING', icon: '🔀', desc: 'Model selection & task routing' },
  { id: 'inference', label: 'INFERENCE', icon: '⚡', desc: 'LLM processes the query' },
  { id: 'tools', label: 'TOOLS', icon: '🔧', desc: 'Tool execution if needed' },
  { id: 'response', label: 'RESPONSE', icon: '💬', desc: 'Stream tokens to UI' },
  { id: 'learn', label: 'LEARN', icon: '📚', desc: 'Auto-memory + reflection' },
];

function FlowNode({ stage, active, completed, data }) {
  const cls = completed ? 'completed' : active ? 'active' : 'pending';
  return (
    <div className={`flow-node ${cls}`}>
      <div className="flow-node-icon">{stage.icon}</div>
      <div className="flow-node-info">
        <div className="flow-node-label">{stage.label}</div>
        <div className="flow-node-desc">{stage.desc}</div>
        {data && <div className="flow-node-data">{data}</div>}
      </div>
      <div className={`flow-node-status ${cls}`}>
        {completed ? '✓' : active ? '...' : '○'}
      </div>
    </div>
  );
}

export default function AIFlowPanel({ onClose, modelInfo, chatStage }) {
  const [width, setWidth] = useState(() => parseInt(localStorage.getItem('mj_aiflow_width')) || 320);
  const resizeRef = useRef(null);
  const startXRef = useRef(0);
  const startWRef = useRef(0);

  // Resize handlers
  const onMouseDown = useCallback((e) => {
    e.preventDefault();
    startXRef.current = e.clientX;
    startWRef.current = width;
    resizeRef.current = true;

    const onMove = (ev) => {
      if (!resizeRef.current) return;
      const diff = startXRef.current - ev.clientX;
      const newW = Math.max(260, Math.min(600, startWRef.current + diff));
      setWidth(newW);
    };
    const onUp = () => {
      resizeRef.current = false;
      localStorage.setItem('mj_aiflow_width', String(width));
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [width]);

  // Determine active stage from chatStage/modelInfo
  const activeStageIdx = (() => {
    if (!chatStage) return -1;
    if (chatStage === 'understanding') return 1; // intent
    if (chatStage === 'calling_ai') return 4;    // inference
    if (chatStage === 'streaming') return 6;     // response
    return -1;
  })();

  // Recent flow logs
  const [logs, setLogs] = useState([]);
  useEffect(() => {
    if (modelInfo?.model) {
      setLogs(prev => [
        { time: new Date().toLocaleTimeString(), text: `Model: ${modelInfo.model} via ${modelInfo.provider}` },
        ...prev.slice(0, 19),
      ]);
    }
  }, [modelInfo?.model, modelInfo?.provider]);

  return (
    <div className="aiflow-panel" style={{ width }}>
      <div className="aiflow-resize" onMouseDown={onMouseDown} />

      <div className="aiflow-header">
        <span className="aiflow-title">{'⚡'} AI FLOW</span>
        <button className="panel-close" onClick={onClose}>{'✕'}</button>
      </div>

      {/* Live status */}
      <div className="aiflow-status">
        <div className={`aiflow-status-dot ${activeStageIdx >= 0 ? 'active' : ''}`} />
        <span>{activeStageIdx >= 0 ? 'PROCESSING' : 'IDLE'}</span>
        {modelInfo && (
          <span className="aiflow-provider-badge">
            {modelInfo.provider?.toUpperCase()}
          </span>
        )}
      </div>

      {/* Flow pipeline */}
      <div className="aiflow-pipeline">
        {FLOW_STAGES.map((stage, i) => (
          <div key={stage.id}>
            <FlowNode
              stage={stage}
              active={i === activeStageIdx}
              completed={activeStageIdx > i}
              data={
                i === 3 && modelInfo?.model ? modelInfo.model.split(':')[0] :
                i === 3 && modelInfo?.provider ? modelInfo.provider : null
              }
            />
            {i < FLOW_STAGES.length - 1 && (
              <div className={`flow-connector ${activeStageIdx > i ? 'active' : ''}`} />
            )}
          </div>
        ))}
      </div>

      {/* Recent logs */}
      <div className="aiflow-logs">
        <div className="aiflow-logs-title">RECENT ACTIVITY</div>
        {logs.length === 0 && (
          <div className="aiflow-logs-empty">No activity yet — send a message.</div>
        )}
        {logs.map((log, i) => (
          <div key={i} className="aiflow-log-item">
            <span className="aiflow-log-time">{log.time}</span>
            <span className="aiflow-log-text">{log.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
