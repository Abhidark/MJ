/**
 * AICoreCard — AI Core Overview with subsystem status indicators.
 */
import { useState, useEffect } from 'react';

const SUBSYSTEMS = [
  { key: 'ai', icon: '💬', name: 'AI Core', defaultState: 'Online' },
  { key: 'memory', icon: '🧠', name: 'Memory', defaultState: 'Standby' },
  { key: 'voice', icon: '🎤', name: 'Voice', defaultState: 'Online' },
  { key: 'modules', icon: '⚡', name: 'Modules', defaultState: '21 Active' },
  { key: 'system', icon: '💻', name: 'System', defaultState: 'Normal' },
];

const MODULE_LIST = [
  'Chat Engine', 'Voice TTS', 'OCR Engine', 'PC Control', 'App Tracker',
  'Zeus Router', 'Live Data', 'Smart Suggest', 'Git Engine', 'Wake Word',
  'Gesture Ctrl', 'Holo FX', 'Memory', 'Self-Learn', 'Error Handler',
  'Clipboard', 'Screenshot', 'System Stats', 'Weather', 'Cricket Live', 'File Manager',
];

export default function AICoreCard() {
  const [expanded, setExpanded] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(d => setStats(d)).catch(() => {});
  }, []);

  const getState = (key) => {
    if (!stats) return SUBSYSTEMS.find(s => s.key === key)?.defaultState;
    if (key === 'ai') return stats.status === 'ok' ? 'Online' : 'Offline';
    if (key === 'memory') return stats.memory_facts ? `${stats.memory_facts} facts` : 'Standby';
    if (key === 'modules') return `${stats.active_modules || 21} Active`;
    if (key === 'system') return stats.status === 'ok' ? 'Normal' : 'Error';
    return SUBSYSTEMS.find(s => s.key === key)?.defaultState;
  };

  const isOnline = (key) => {
    const st = getState(key);
    return st && !['Offline', 'Error', 'Standby'].includes(st);
  };

  return (
    <div className="aicore-card">
      <div className="aicore-header" onClick={() => setExpanded(e => !e)}>
        <span>AI Core Overview</span>
        <span className={`expand-arrow ${expanded ? 'open' : ''}`}>▶</span>
      </div>
      <div className="aicore-list">
        {SUBSYSTEMS.map(s => (
          <div key={s.key} className="aicore-item">
            <span className="aicore-icon">{s.icon}</span>
            <div className="aicore-info">
              <div className="aicore-name">{s.name}</div>
              <div className={`aicore-state ${isOnline(s.key) ? 'online' : ''}`}>
                {getState(s.key)}
              </div>
            </div>
          </div>
        ))}
      </div>
      {expanded && (
        <div className="aicore-detail">
          <div className="aicore-detail-grid">
            <div className="aicore-detail-row">
              <span className="aicore-dl">Version</span><span className="aicore-dv">MJ v1.0</span>
            </div>
            <div className="aicore-detail-row">
              <span className="aicore-dl">Build</span><span className="aicore-dv">2026.06</span>
            </div>
            <div className="aicore-detail-row">
              <span className="aicore-dl">Active Modules</span><span className="aicore-dv">{stats?.active_modules || 21}</span>
            </div>
            <div className="aicore-detail-row">
              <span className="aicore-dl">Memory Bank</span><span className="aicore-dv">{stats?.memory_facts || 0} facts</span>
            </div>
          </div>
          <div className="aicore-module-title">Module List</div>
          <div className="aicore-modules">
            {MODULE_LIST.map(m => <span key={m} className="aicore-mod-tag">{m}</span>)}
          </div>
        </div>
      )}
    </div>
  );
}
