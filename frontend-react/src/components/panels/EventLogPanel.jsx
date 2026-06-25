/**
 * EventLogPanel — System event log viewer with severity filters and search.
 */
import { useState, useEffect, useCallback } from 'react';

const SEVERITIES = ['debug', 'info', 'warning', 'error', 'critical'];
const SEV_COLORS = { debug: '#666', info: '#4fc3f7', warning: '#ffb74d', error: '#ef5350', critical: '#ff1744' };

export default function EventLogPanel({ onClose }) {
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState({});
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('events');

  const load = useCallback(() => {
    const params = new URLSearchParams();
    if (filter) params.set('severity', filter);
    if (search) params.set('search', search);
    params.set('limit', '100');

    Promise.all([
      fetch(`/os/events/query?${params}`).then(r => r.json()),
      fetch('/os/events/stats').then(r => r.json()),
      fetch('/os/events/sources').then(r => r.json()),
    ]).then(([eData, sData, srcData]) => {
      setEvents(eData.events || []);
      setStats({ ...sData, sources: srcData.sources || {} });
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [filter, search]);

  useEffect(() => { load(); }, [load]);

  const clearEvents = () => {
    fetch('/os/events/clear', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }).then(() => load());
  };

  const logTest = (severity) => {
    fetch('/os/events/log', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: `Test ${severity} event`, severity, source: 'ui-test' }),
    }).then(() => load());
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    const d = new Date(ts);
    return d.toLocaleTimeString();
  };

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="panel-container panel-xl">
        <div className="panel-header">
          <span className="panel-title">System Event Log</span>
          <button className="panel-close" onClick={onClose}>x</button>
        </div>

        {loading ? <div className="panel-loading">Loading...</div> : (
          <div className="panel-body">
            <div className="el-tabs">
              <button className={`el-tab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>Events</button>
              <button className={`el-tab ${tab === 'stats' ? 'active' : ''}`} onClick={() => setTab('stats')}>Stats</button>
            </div>

            {tab === 'events' && (
              <>
                <div className="el-toolbar">
                  <div className="el-filters">
                    <button className={`el-sev-btn ${filter === '' ? 'active' : ''}`}
                      onClick={() => setFilter('')}>All</button>
                    {SEVERITIES.map(s => (
                      <button key={s} className={`el-sev-btn ${filter === s ? 'active' : ''}`}
                        style={{ borderColor: SEV_COLORS[s] }}
                        onClick={() => setFilter(f => f === s ? '' : s)}>{s}</button>
                    ))}
                  </div>
                  <input className="el-search" placeholder="Search events..."
                    value={search} onChange={e => setSearch(e.target.value)} />
                  <button className="el-btn-clear" onClick={clearEvents}>Clear All</button>
                </div>

                <div className="el-event-list">
                  {events.length === 0 && <div className="el-empty">No events found</div>}
                  {[...events].reverse().map((evt, i) => (
                    <div key={i} className="el-event-row">
                      <span className="el-time">{formatTime(evt.ts)}</span>
                      <span className="el-sev" style={{ color: SEV_COLORS[evt.severity] || '#aaa' }}>
                        {evt.severity}
                      </span>
                      <span className="el-source">[{evt.source}]</span>
                      <span className="el-msg">{evt.message}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {tab === 'stats' && (
              <div className="el-stats">
                <div className="el-stat-grid">
                  <div className="el-stat-card">
                    <div className="el-stat-num">{stats.total_events || 0}</div>
                    <div className="el-stat-lbl">Total Events</div>
                  </div>
                  <div className="el-stat-card">
                    <div className="el-stat-num">{stats.retention_days || 30}</div>
                    <div className="el-stat-lbl">Retention (days)</div>
                  </div>
                  <div className="el-stat-card">
                    <div className="el-stat-num">{stats.sources ? Object.keys(stats.sources).length : 0}</div>
                    <div className="el-stat-lbl">Sources</div>
                  </div>
                </div>

                <div className="el-section-title">By Severity</div>
                <div className="el-sev-bars">
                  {SEVERITIES.map(s => {
                    const count = stats.severities?.[s] || 0;
                    const max = Math.max(...SEVERITIES.map(sv => stats.severities?.[sv] || 0), 1);
                    return (
                      <div key={s} className="el-bar-row">
                        <span className="el-bar-label" style={{ color: SEV_COLORS[s] }}>{s}</span>
                        <div className="el-bar-track">
                          <div className="el-bar-fill" style={{
                            width: `${(count / max) * 100}%`,
                            backgroundColor: SEV_COLORS[s],
                          }} />
                        </div>
                        <span className="el-bar-count">{count}</span>
                      </div>
                    );
                  })}
                </div>

                <div className="el-section-title">Test Events</div>
                <div className="el-test-btns">
                  {SEVERITIES.map(s => (
                    <button key={s} className="el-test-btn" style={{ borderColor: SEV_COLORS[s] }}
                      onClick={() => logTest(s)}>Log {s}</button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
