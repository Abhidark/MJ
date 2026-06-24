/**
 * ErrorPanel — System errors display with Auto Fix All and Clear buttons.
 */
import { useState, useEffect, useCallback } from 'react';

export default function ErrorPanel({ onClose }) {
  const [errors, setErrors] = useState([]);
  const [fixing, setFixing] = useState(false);

  const load = useCallback(() => {
    fetch('/system-errors')
      .then(r => r.json())
      .then(d => setErrors(d.errors || []))
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleFixAll = async () => {
    setFixing(true);
    try {
      await fetch('/auto-fix-errors', { method: 'POST' });
      load();
    } catch { /* silent */ }
    setFixing(false);
  };

  const handleClear = () => {
    fetch('/clear-errors', { method: 'POST' }).then(() => setErrors([])).catch(() => {});
  };

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="error-panel">
        <div className="error-panel-header">
          <span>SYSTEM ERRORS</span>
          <div className="error-panel-actions">
            <button className="err-btn" onClick={handleFixAll} disabled={fixing}>
              {fixing ? 'Fixing...' : 'Auto Fix All'}
            </button>
            <button className="err-btn" onClick={handleClear}>Clear</button>
            <button className="err-btn" onClick={onClose}>✕</button>
          </div>
        </div>
        <div className="error-list">
          {errors.length === 0 ? (
            <div className="error-empty">No errors — system healthy</div>
          ) : (
            errors.map((err, i) => (
              <div key={i} className="error-item">
                <span className="error-time">{err.time || '--'}</span>
                <span className="error-module">{err.module || 'System'}</span>
                <span className="error-msg">{err.message || err}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
