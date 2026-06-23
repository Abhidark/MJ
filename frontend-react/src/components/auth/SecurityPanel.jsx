import { useState } from 'react';
import { useAuth } from '@/context/AuthContext';

export default function SecurityPanel({ onClose }) {
  const { authEnabled, toggleAuth, changePassword, logout } = useAuth();

  const [authToggle, setAuthToggle] = useState(authEnabled ?? false);
  const [togglePwd, setTogglePwd] = useState('');
  const [toggleMsg, setToggleMsg] = useState({ text: '', type: '' });

  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [changePwdMsg, setChangePwdMsg] = useState({ text: '', type: '' });

  const [loading, setLoading] = useState(false);

  // Toggle auth on/off
  const handleToggle = async () => {
    if (!togglePwd.trim()) {
      setToggleMsg({ text: 'Password required', type: 'error' });
      return;
    }
    setLoading(true);
    try {
      const newState = !authToggle;
      const result = await toggleAuth(newState, togglePwd);
      if (result.success) {
        setAuthToggle(newState);
        setToggleMsg({ text: newState ? 'Auth enabled' : 'Auth disabled', type: 'success' });
        setTogglePwd('');
      } else {
        setToggleMsg({ text: result.message || 'Failed', type: 'error' });
      }
    } catch (err) {
      setToggleMsg({ text: err.response?.data?.message || 'Error', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Change password
  const handleChangePassword = async () => {
    if (!oldPwd.trim() || !newPwd.trim()) {
      setChangePwdMsg({ text: 'Both fields required', type: 'error' });
      return;
    }
    if (newPwd.length < 4) {
      setChangePwdMsg({ text: 'Min 4 characters', type: 'error' });
      return;
    }
    setLoading(true);
    try {
      const result = await changePassword(oldPwd, newPwd);
      if (result.success) {
        setChangePwdMsg({ text: 'Password changed! Please re-login.', type: 'success' });
        setOldPwd('');
        setNewPwd('');
      } else {
        setChangePwdMsg({ text: result.message || 'Failed', type: 'error' });
      }
    } catch (err) {
      setChangePwdMsg({ text: err.response?.data?.message || 'Error', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  // Logout
  const handleLogout = async () => {
    await logout();
    onClose();
  };

  return (
    <div className="security-panel-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="security-panel">
        <div className="security-panel-header">
          <span className="security-panel-title">{'\u{1F512}'} Security Settings</span>
          <button className="security-panel-close" onClick={onClose}>{'✕'}</button>
        </div>

        <div className="security-panel-body">
          {/* Password Lock Toggle */}
          <div className="sec-section">
            <div className="sec-toggle-row">
              <div className="sec-toggle-info">
                <div className="sec-toggle-title">PASSWORD LOCK</div>
                <div className="sec-toggle-desc">Require password on startup</div>
              </div>
              <label className="sec-toggle-switch">
                <input
                  type="checkbox"
                  checked={authToggle}
                  onChange={() => {
                    if (togglePwd.trim()) handleToggle();
                    else setToggleMsg({ text: 'Enter password below first', type: 'error' });
                  }}
                />
                <span className="sec-toggle-track" />
                <span className="sec-toggle-thumb" />
              </label>
            </div>
            <input
              type="password"
              className="sec-input"
              placeholder="Current password to toggle"
              value={togglePwd}
              onChange={(e) => setTogglePwd(e.target.value)}
              style={{ marginTop: 12 }}
            />
            <div className={`sec-msg ${toggleMsg.type}`}>{toggleMsg.text}</div>
          </div>

          {/* Change Password */}
          {authToggle && (
            <div className="sec-section">
              <div className="sec-section-label" style={{ color: 'var(--accent)' }}>CHANGE PASSWORD</div>
              <div className="sec-toggle-desc" style={{ marginBottom: 8 }}>Default password: jarvis</div>
              <input
                type="password"
                className="sec-input"
                placeholder="Current Password"
                value={oldPwd}
                onChange={(e) => setOldPwd(e.target.value)}
              />
              <input
                type="password"
                className="sec-input"
                placeholder="New Password (min 4 chars)"
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
              />
              <button
                className="sec-btn sec-btn-primary"
                onClick={handleChangePassword}
                disabled={loading}
              >
                UPDATE PASSWORD
              </button>
              <div className={`sec-msg ${changePwdMsg.type}`}>{changePwdMsg.text}</div>
            </div>
          )}

          {/* Logout */}
          <div className="sec-section sec-divider">
            <div className="sec-section-label" style={{ color: '#ff6b6b' }}>LOGOUT</div>
            <button
              className="sec-btn sec-btn-danger"
              onClick={handleLogout}
              disabled={loading}
            >
              LOGOUT FROM MJ
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
