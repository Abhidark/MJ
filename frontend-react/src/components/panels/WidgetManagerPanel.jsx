/**
 * WidgetManagerPanel — Browse widget registry, manage dashboard layout.
 */
import { useState, useEffect, useCallback } from 'react';

export default function WidgetManagerPanel({ onClose }) {
  const [registry, setRegistry] = useState({});
  const [layout, setLayout] = useState([]);
  const [savedLayouts, setSavedLayouts] = useState({});
  const [loading, setLoading] = useState(true);
  const [layoutName, setLayoutName] = useState('');
  const [tab, setTab] = useState('registry');

  const load = useCallback(() => {
    Promise.all([
      fetch('/jarvis/widgets/registry').then(r => r.json()),
      fetch('/jarvis/widgets/layout').then(r => r.json()),
      fetch('/jarvis/widgets/layouts').then(r => r.json()),
    ]).then(([reg, lay, saved]) => {
      setRegistry(reg.widgets || {});
      setLayout(lay.layout || []);
      setSavedLayouts(saved.layouts || {});
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const activeIds = new Set(layout.map(w => w.widget_id));

  const addWidget = (id) => {
    fetch('/jarvis/widgets/add', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ widget_id: id }),
    }).then(() => load());
  };

  const removeWidget = (id) => {
    fetch('/jarvis/widgets/remove', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ widget_id: id }),
    }).then(() => load());
  };

  const saveLayout = () => {
    if (!layoutName) return;
    fetch('/jarvis/widgets/layout/save', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: layoutName }),
    }).then(() => { setLayoutName(''); load(); });
  };

  const loadLayout = (name) => {
    fetch('/jarvis/widgets/layout/load', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).then(() => load());
  };

  const categories = {};
  Object.values(registry).forEach(w => {
    const cat = w.category || 'other';
    if (!categories[cat]) categories[cat] = [];
    categories[cat].push(w);
  });

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="panel-container panel-lg">
        <div className="panel-header">
          <span className="panel-title">Widget Manager</span>
          <button className="panel-close" onClick={onClose}>x</button>
        </div>

        {loading ? <div className="panel-loading">Loading...</div> : (
          <div className="panel-body">
            <div className="wm-tabs">
              <button className={`wm-tab ${tab === 'registry' ? 'active' : ''}`} onClick={() => setTab('registry')}>Registry</button>
              <button className={`wm-tab ${tab === 'active' ? 'active' : ''}`} onClick={() => setTab('active')}>Active ({layout.length})</button>
              <button className={`wm-tab ${tab === 'layouts' ? 'active' : ''}`} onClick={() => setTab('layouts')}>Layouts</button>
            </div>

            {tab === 'registry' && (
              <div className="wm-registry">
                {Object.entries(categories).map(([cat, widgets]) => (
                  <div key={cat} className="wm-category">
                    <div className="wm-cat-title">{cat.toUpperCase()}</div>
                    <div className="wm-grid">
                      {widgets.map(w => (
                        <div key={w.id} className={`wm-card ${activeIds.has(w.id) ? 'active' : ''}`}>
                          <div className="wm-card-name">{w.name}</div>
                          <div className="wm-card-size">{w.default_w}x{w.default_h}</div>
                          {activeIds.has(w.id)
                            ? <button className="wm-btn-remove" onClick={() => removeWidget(w.id)}>Remove</button>
                            : <button className="wm-btn-add" onClick={() => addWidget(w.id)}>+ Add</button>
                          }
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tab === 'active' && (
              <div className="wm-active">
                {layout.length === 0 && <div className="wm-empty">No widgets on dashboard</div>}
                {layout.map((w, i) => (
                  <div key={i} className="wm-active-row">
                    <span className="wm-active-name">{w.widget_id}</span>
                    <span className="wm-active-pos">({w.x},{w.y})</span>
                    <span className="wm-active-size">{w.w}x{w.h}</span>
                    <button className="wm-btn-remove" onClick={() => removeWidget(w.widget_id)}>x</button>
                  </div>
                ))}
              </div>
            )}

            {tab === 'layouts' && (
              <div className="wm-layouts">
                <div className="wm-save-row">
                  <input placeholder="Layout name..." value={layoutName}
                    onChange={e => setLayoutName(e.target.value)} className="wm-input" />
                  <button className="wm-btn-add" onClick={saveLayout} disabled={!layoutName}>Save Current</button>
                </div>
                {Object.entries(savedLayouts).length === 0 && <div className="wm-empty">No saved layouts</div>}
                {Object.entries(savedLayouts).map(([name, count]) => (
                  <div key={name} className="wm-layout-row">
                    <span className="wm-layout-name">{name}</span>
                    <span className="wm-layout-count">{count} widgets</span>
                    <button className="wm-btn-add" onClick={() => loadLayout(name)}>Load</button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
