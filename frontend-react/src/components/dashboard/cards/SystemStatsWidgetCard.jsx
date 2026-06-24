/**
 * SystemStatsWidgetCard — 6 mini status tiles: Voice, Memory, Chats, Model, Health, Modules.
 */
import { useState, useEffect } from 'react';

const WIDGETS = [
  { key: 'voice', icon: '🎤', title: 'Voice', defaultVal: 'Ready' },
  { key: 'memory', icon: '🧠', title: 'Memory', defaultVal: '0 facts' },
  { key: 'chats', icon: '💬', title: 'Chats', defaultVal: '0' },
  { key: 'model', icon: '🤖', title: 'Model', defaultVal: 'Zeus Auto' },
  { key: 'health', icon: '💚', title: 'Health', defaultVal: 'OK' },
  { key: 'modules', icon: '⚡', title: 'Modules', defaultVal: '21' },
];

export default function SystemStatsWidgetCard() {
  const [data, setData] = useState({});

  useEffect(() => {
    fetch('/health').then(r => r.json()).then(d => {
      setData({
        voice: d.voice_ready ? 'Active' : 'Ready',
        memory: `${d.memory_facts || 0} facts`,
        chats: String(d.total_chats || 0),
        model: d.active_model || 'Zeus Auto',
        health: d.status === 'ok' ? 'OK' : 'Error',
        modules: String(d.active_modules || 21),
      });
    }).catch(() => {});
  }, []);

  return (
    <div className="sysstats-card">
      <div className="sysstats-header">System Stats</div>
      <div className="sysstats-grid">
        {WIDGETS.map(w => (
          <div key={w.key} className="sysstats-tile">
            <div className="sysstats-icon">{w.icon}</div>
            <div className="sysstats-title">{w.title}</div>
            <div className="sysstats-value">{data[w.key] || w.defaultVal}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
