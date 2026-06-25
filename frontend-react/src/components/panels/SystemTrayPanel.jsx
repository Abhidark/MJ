/**
 * SystemTrayPanel — Configure system tray menu, badge, tooltip.
 */
import { useState, useEffect, useCallback } from 'react';

export default function SystemTrayPanel({ onClose }) {
  const [menu, setMenu] = useState([]);
  const [badge, setBadge] = useState({ visible: false, count: 0 });
  const [tooltip, setTooltip] = useState('');
  const [minimized, setMinimized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newItem, setNewItem] = useState({ id: '', label: '', action: '', icon: '' });

  const load = useCallback(() => {
    Promise.all([
      fetch('/jarvis/tray/menu').then(r => r.json()),
      fetch('/jarvis/tray/status').then(r => r.json()),
    ]).then(([mData, sData]) => {
      setMenu(mData.menu || []);
      setTooltip(mData.tooltip || '');
      setBadge(mData.badge || { visible: false, count: 0 });
      setMinimized(sData.minimized || false);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const removeItem = (id) => {
    fetch('/jarvis/tray/menu/remove', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => load());
  };

  const addItem = () => {
    if (!newItem.id || !newItem.label) return;
    fetch('/jarvis/tray/menu/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newItem),
    }).then(() => { setAdding(false); setNewItem({ id: '', label: '', action: '', icon: '' }); load(); });
  };

  const updateTooltip = () => {
    fetch('/jarvis/tray/tooltip', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: tooltip }),
    });
  };

  const toggleBadge = () => {
    const next = { visible: !badge.visible, count: badge.count };
    fetch('/jarvis/tray/badge', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(next),
    }).then(() => setBadge(next));
  };

  const toggleMinimize = () => {
    const endpoint = minimized ? '/jarvis/tray/restore' : '/jarvis/tray/minimize';
    fetch(endpoint, { method: 'POST' }).then(() => setMinimized(!minimized));
  };

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="panel-container panel-md">
        <div className="panel-header">
          <span className="panel-title">System Tray</span>
          <button className="panel-close" onClick={onClose}>x</button>
        </div>

        {loading ? <div className="panel-loading">Loading...</div> : (
          <div className="panel-body">
            <div className="st-status-row">
              <div className="st-stat">
                <span className="st-stat-label">Status</span>
                <span className={`st-stat-val ${minimized ? 'warn' : 'ok'}`}>
                  {minimized ? 'Minimized' : 'Active'}
                </span>
              </div>
              <div className="st-stat">
                <span className="st-stat-label">Badge</span>
                <span className={`st-stat-val ${badge.visible ? 'ok' : ''}`}>
                  {badge.visible ? badge.count : 'Off'}
                </span>
              </div>
              <button className="st-btn" onClick={toggleMinimize}>
                {minimized ? 'Restore' : 'Minimize'}
              </button>
              <button className="st-btn" onClick={toggleBadge}>
                {badge.visible ? 'Hide Badge' : 'Show Badge'}
              </button>
            </div>

            <div className="st-tooltip-row">
              <input value={tooltip} onChange={e => setTooltip(e.target.value)}
                className="st-input" placeholder="Tooltip text..." />
              <button className="st-btn" onClick={updateTooltip}>Set</button>
            </div>

            <div className="st-section-title">
              Menu Items
              <button className="st-btn-sm" onClick={() => setAdding(true)}>+ Add</button>
            </div>

            {adding && (
              <div className="st-add-form">
                <input placeholder="ID" value={newItem.id} onChange={e => setNewItem({ ...newItem, id: e.target.value })} className="st-input" />
                <input placeholder="Label" value={newItem.label} onChange={e => setNewItem({ ...newItem, label: e.target.value })} className="st-input" />
                <input placeholder="Action" value={newItem.action} onChange={e => setNewItem({ ...newItem, action: e.target.value })} className="st-input" />
                <input placeholder="Icon" value={newItem.icon} onChange={e => setNewItem({ ...newItem, icon: e.target.value })} className="st-input" />
                <button className="st-btn" onClick={addItem}>Save</button>
                <button className="st-btn st-btn-dim" onClick={() => setAdding(false)}>Cancel</button>
              </div>
            )}

            <div className="st-menu-list">
              {menu.map((item, i) => (
                <div key={i} className={`st-menu-item ${item.action === 'separator' ? 'sep' : ''}`}>
                  {item.action === 'separator' ? (
                    <span className="st-sep-line">---</span>
                  ) : (
                    <>
                      <span className="st-item-icon">{item.icon || '-'}</span>
                      <span className="st-item-label">{item.label}</span>
                      <span className="st-item-action">{item.action}</span>
                      <button className="st-btn-del" onClick={() => removeItem(item.id)}>x</button>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
