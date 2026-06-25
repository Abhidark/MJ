/**
 * HotkeysPanel — View/edit global hotkey bindings, switch profiles.
 */
import { useState, useEffect, useCallback } from 'react';

export default function HotkeysPanel({ onClose }) {
  const [bindings, setBindings] = useState({});
  const [profiles, setProfiles] = useState([]);
  const [activeProfile, setActiveProfile] = useState('default');
  const [enabled, setEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [newHk, setNewHk] = useState({ id: '', keys: '', action: '', label: '' });
  const [profileName, setProfileName] = useState('');

  const load = useCallback(() => {
    Promise.all([
      fetch('/jarvis/hotkeys/bindings').then(r => r.json()),
      fetch('/jarvis/hotkeys/profiles').then(r => r.json()),
    ]).then(([bData, pData]) => {
      setBindings(bData.bindings || {});
      setEnabled(bData.enabled !== false);
      setProfiles(pData.profiles || []);
      setActiveProfile(pData.active || 'default');
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = (id) => {
    fetch('/jarvis/hotkeys/unregister', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id }),
    }).then(() => load());
  };

  const addHotkey = () => {
    if (!newHk.id || !newHk.keys) return;
    fetch('/jarvis/hotkeys/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newHk),
    }).then(() => { setAdding(false); setNewHk({ id: '', keys: '', action: '', label: '' }); load(); });
  };

  const toggleEnabled = () => {
    fetch('/jarvis/hotkeys/enabled', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: !enabled }),
    }).then(() => { setEnabled(!enabled); });
  };

  const switchProfile = (name) => {
    fetch('/jarvis/hotkeys/profile/load', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).then(() => load());
  };

  const saveProfile = () => {
    if (!profileName) return;
    fetch('/jarvis/hotkeys/profile/save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: profileName }),
    }).then(() => { setProfileName(''); load(); });
  };

  const resetDefaults = () => {
    fetch('/jarvis/hotkeys/reset', { method: 'POST' }).then(() => load());
  };

  const entries = Object.entries(bindings);

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="panel-container panel-lg">
        <div className="panel-header">
          <span className="panel-title">Global Hotkeys</span>
          <button className="panel-close" onClick={onClose}>x</button>
        </div>

        {loading ? <div className="panel-loading">Loading...</div> : (
          <div className="panel-body">
            <div className="hk-toolbar">
              <label className="hk-toggle">
                <input type="checkbox" checked={enabled} onChange={toggleEnabled} />
                <span>{enabled ? 'Enabled' : 'Disabled'}</span>
              </label>
              <select value={activeProfile} onChange={e => switchProfile(e.target.value)} className="hk-select">
                {profiles.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <button className="hk-btn" onClick={() => setAdding(true)}>+ Add</button>
              <button className="hk-btn hk-btn-dim" onClick={resetDefaults}>Reset</button>
            </div>

            <div className="hk-save-row">
              <input placeholder="Profile name..." value={profileName}
                onChange={e => setProfileName(e.target.value)} className="hk-input" />
              <button className="hk-btn" onClick={saveProfile} disabled={!profileName}>Save Profile</button>
            </div>

            {adding && (
              <div className="hk-add-form">
                <input placeholder="ID" value={newHk.id} onChange={e => setNewHk({ ...newHk, id: e.target.value })} className="hk-input" />
                <input placeholder="Keys (Ctrl+Shift+X)" value={newHk.keys} onChange={e => setNewHk({ ...newHk, keys: e.target.value })} className="hk-input" />
                <input placeholder="Action" value={newHk.action} onChange={e => setNewHk({ ...newHk, action: e.target.value })} className="hk-input" />
                <input placeholder="Label" value={newHk.label} onChange={e => setNewHk({ ...newHk, label: e.target.value })} className="hk-input" />
                <button className="hk-btn" onClick={addHotkey}>Save</button>
                <button className="hk-btn hk-btn-dim" onClick={() => setAdding(false)}>Cancel</button>
              </div>
            )}

            <div className="hk-list">
              {entries.length === 0 && <div className="hk-empty">No hotkeys configured</div>}
              {entries.map(([id, hk]) => (
                <div key={id} className="hk-row">
                  <span className="hk-keys">{hk.keys}</span>
                  <span className="hk-label">{hk.label || id}</span>
                  <span className="hk-action">{hk.action}</span>
                  <button className="hk-btn-del" onClick={() => remove(id)}>x</button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
