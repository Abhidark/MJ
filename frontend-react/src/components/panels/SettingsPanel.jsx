import { useState, useEffect, useCallback } from 'react';
import { voiceAPI, modelAPI } from '@/services/api';

// ─── Orb color presets ───
const ORB_COLORS = [
  { name: 'Cyan', value: '#00d4ff' },
  { name: 'Purple', value: '#a855f7' },
  { name: 'Green', value: '#00e676' },
  { name: 'Orange', value: '#ff9100' },
  { name: 'Red', value: '#ff1744' },
  { name: 'Gold', value: '#ffd700' },
  { name: 'Pink', value: '#ff4081' },
  { name: 'White', value: '#ffffff' },
];

const ANIM_SPEEDS = [
  { label: 'Slow', value: 0.5 },
  { label: 'Normal', value: 1 },
  { label: 'Fast', value: 2 },
  { label: 'Ultra', value: 3 },
];

export default function SettingsPanel({ onClose }) {
  // Orb settings (stored in localStorage)
  const [orbColor, setOrbColor] = useState(() => localStorage.getItem('mj_orb_color') || '#00d4ff');
  const [orbSpeed, setOrbSpeed] = useState(() => parseFloat(localStorage.getItem('mj_orb_speed')) || 1);

  // Voice settings from backend
  const [voices, setVoices] = useState([]);
  const [voiceSettings, setVoiceSettings] = useState(null);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [voiceSpeed, setVoiceSpeed] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saveMsg, setSaveMsg] = useState('');

  // Provider
  const [provider, setProvider] = useState('');

  // Load voice settings + provider on mount
  useEffect(() => {
    async function load() {
      try {
        const [vRes, pRes] = await Promise.all([
          voiceAPI.getSettings(),
          modelAPI.getProvider(),
        ]);
        const data = vRes.data;
        setVoiceSettings(data.settings || {});
        setVoices(data.available_voices || []);
        setSelectedVoice(data.settings?.voice || '');
        setVoiceSpeed(data.settings?.speed || 1);
        setProvider(pRes.data?.provider || 'ollama');
      } catch (e) {
        console.error('[SettingsPanel] load error:', e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Orb color change
  const handleOrbColor = useCallback((color) => {
    setOrbColor(color);
    localStorage.setItem('mj_orb_color', color);
    // Dispatch custom event so orb component can listen
    window.dispatchEvent(new CustomEvent('orb:color', { detail: color }));
  }, []);

  // Orb speed change
  const handleOrbSpeed = useCallback((speed) => {
    setOrbSpeed(speed);
    localStorage.setItem('mj_orb_speed', String(speed));
    window.dispatchEvent(new CustomEvent('orb:speed', { detail: speed }));
  }, []);

  // Save voice settings
  const handleSaveVoice = useCallback(async () => {
    try {
      await voiceAPI.updateSettings({
        ...voiceSettings,
        voice: selectedVoice,
        speed: voiceSpeed,
      });
      setSaveMsg('Saved!');
      setTimeout(() => setSaveMsg(''), 2000);
    } catch (e) {
      setSaveMsg('Error saving');
    }
  }, [voiceSettings, selectedVoice, voiceSpeed]);

  // Provider switch
  const handleProvider = useCallback(async (p) => {
    try {
      await modelAPI.setProvider(p);
      setProvider(p);
    } catch (e) {
      console.error('[SettingsPanel] provider switch error:', e);
    }
  }, []);

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        <div className="settings-header">
          <span className="settings-title">{'⚙'} Settings</span>
          <button className="panel-close" onClick={onClose}>{'✕'}</button>
        </div>

        <div className="settings-body">
          {/* Orb Color */}
          <div className="settings-section">
            <div className="settings-label">ORB COLOR</div>
            <div className="settings-colors">
              {ORB_COLORS.map(c => (
                <button
                  key={c.value}
                  className={`settings-color-btn${orbColor === c.value ? ' active' : ''}`}
                  style={{ '--swatch': c.value }}
                  onClick={() => handleOrbColor(c.value)}
                  title={c.name}
                />
              ))}
            </div>
            <div className="settings-color-custom">
              <label className="settings-sublabel">Custom:</label>
              <input
                type="color"
                value={orbColor}
                onChange={e => handleOrbColor(e.target.value)}
                className="settings-color-picker"
              />
              <span className="settings-color-hex">{orbColor}</span>
            </div>
          </div>

          {/* Orb Animation Speed */}
          <div className="settings-section">
            <div className="settings-label">ANIMATION SPEED</div>
            <div className="settings-speed-btns">
              {ANIM_SPEEDS.map(s => (
                <button
                  key={s.value}
                  className={`settings-speed-btn${orbSpeed === s.value ? ' active' : ''}`}
                  onClick={() => handleOrbSpeed(s.value)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Provider */}
          <div className="settings-section">
            <div className="settings-label">AI PROVIDER</div>
            <div className="settings-provider-btns">
              <button
                className={`settings-provider-btn${provider === 'ollama' ? ' active' : ''}`}
                onClick={() => handleProvider('ollama')}
              >
                Ollama (Local)
              </button>
              <button
                className={`settings-provider-btn${provider === 'groq' ? ' active' : ''}`}
                onClick={() => handleProvider('groq')}
              >
                Groq (Cloud)
              </button>
            </div>
          </div>

          {/* Voice Selection */}
          <div className="settings-section">
            <div className="settings-label">VOICE</div>
            {loading ? (
              <div className="settings-loading">Loading voices...</div>
            ) : voices.length === 0 ? (
              <div className="settings-loading">No voices available (Kokoro not running?)</div>
            ) : (
              <>
                <select
                  className="settings-select"
                  value={selectedVoice}
                  onChange={e => setSelectedVoice(e.target.value)}
                >
                  {voices.map(v => (
                    <option key={typeof v === 'string' ? v : v.id} value={typeof v === 'string' ? v : v.id}>
                      {typeof v === 'string' ? v : v.name || v.id}
                    </option>
                  ))}
                </select>

                <div className="settings-sublabel" style={{ marginTop: 8 }}>Speed: {voiceSpeed.toFixed(1)}x</div>
                <input
                  type="range"
                  min="0.5"
                  max="2"
                  step="0.1"
                  value={voiceSpeed}
                  onChange={e => setVoiceSpeed(parseFloat(e.target.value))}
                  className="settings-range"
                />

                <button className="settings-save-btn" onClick={handleSaveVoice}>
                  SAVE VOICE SETTINGS
                </button>
                {saveMsg && <div className="settings-save-msg">{saveMsg}</div>}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
