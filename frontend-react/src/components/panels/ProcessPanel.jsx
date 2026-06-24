/**
 * ProcessPanel — Sortable process table with Name, PID, CPU, RAM, Kill action.
 */
import { useState, useEffect, useCallback } from 'react';

export default function ProcessPanel({ onClose }) {
  const [procs, setProcs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState('name');
  const [sortDir, setSortDir] = useState('asc');

  const load = useCallback(() => {
    fetch('/top-processes')
      .then(r => r.json())
      .then(d => { setProcs(d.processes || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 5000); return () => clearInterval(iv); }, [load]);

  const sorted = [...procs].sort((a, b) => {
    let va = a[sortKey], vb = b[sortKey];
    if (typeof va === 'string') va = va.toLowerCase();
    if (typeof vb === 'string') vb = vb.toLowerCase();
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const toggleSort = (key) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('asc'); }
  };

  const arrow = (key) => sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : '';

  const killProc = (pid) => {
    fetch('/kill-process', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pid }),
    }).then(() => load()).catch(() => {});
  };

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="proc-panel">
        <div className="proc-panel-header">
          <span className="proc-panel-title">▦ Running Processes</span>
          <button className="panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="proc-table-head">
          <button className={`proc-sort-btn${sortKey === 'name' ? ' active' : ''}`} onClick={() => toggleSort('name')}>Name{arrow('name')}</button>
          <span>PID</span>
          <button className={`proc-sort-btn${sortKey === 'cpu' ? ' active' : ''}`} onClick={() => toggleSort('cpu')}>CPU (%){arrow('cpu')}</button>
          <button className={`proc-sort-btn${sortKey === 'memory' ? ' active' : ''}`} onClick={() => toggleSort('memory')}>RAM (MB){arrow('memory')}</button>
          <span>Actions</span>
        </div>
        <div className="proc-list">
          {loading ? <div className="proc-loading">Loading processes...</div> :
            sorted.length === 0 ? <div className="proc-loading">No processes found</div> :
            sorted.map((p, i) => (
              <div key={i} className="proc-row">
                <span className="proc-name">{p.name}</span>
                <span className="proc-pid">{p.pid}</span>
                <span className="proc-cpu">{p.cpu}%</span>
                <span className="proc-ram">{p.memory} MB</span>
                <button className="proc-kill-btn" onClick={() => killProc(p.pid)} title="Kill process">✕</button>
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}
