import { useState, useEffect, useCallback } from 'react';
import { voiceAPI, modelAPI } from '@/services/api';

// ─── Orb Energy Presets (matches old UI) ───
const ENERGY_PRESETS = [
  { key: 'emerald', name: 'JARVIS', color: '#00d4ff', shadow: 'rgba(0,212,255,0.6)' },
  { key: 'cyan', name: 'Cyan', color: '#00f0ff', shadow: 'rgba(0,240,255,0.6)' },
  { key: 'violet', name: 'Violet', color: '#b92eff', shadow: 'rgba(185,46,255,0.6)' },
  { key: 'solar', name: 'Solar', color: '#ff5900', shadow: 'rgba(255,89,0,0.6)' },
  { key: 'gold', name: 'Gold', color: '#ffd900', shadow: 'rgba(255,217,0,0.6)' },
];

// ─── Interaction Modes ───
const INTERACTION_MODES = [
  { key: 'repel', label: 'Repel', desc: 'Disperses particles' },
  { key: 'attract', label: 'Attract', desc: 'Pulls to cursor' },
  { key: 'vortex', label: 'Vortex', desc: 'Orbital swirl' },
  { key: 'ripple', label: 'Ripple', desc: 'Elastic wave' },
];

// ─── Dashboard Themes ───
const DASH_THEMES = [
  { key: 'default', name: 'JARVIS', bg: 'linear-gradient(135deg,#020c19,#0a1628)', accent: '#00d4ff' },
  { key: 'emerald', name: 'EMERALD', bg: 'linear-gradient(135deg,#021910,#0a2818)', accent: '#00ff88' },
  { key: 'crimson', name: 'CRIMSON', bg: 'linear-gradient(135deg,#190205,#280a0f)', accent: '#ff3b5c' },
  { key: 'violet', name: 'VIOLET', bg: 'linear-gradient(135deg,#0f0219,#1a0a28)', accent: '#b92eff' },
  { key: 'solar', name: 'SOLAR', bg: 'linear-gradient(135deg,#191002,#281a0a)', accent: '#ffa500' },
  { key: 'midnight', name: 'MIDNIGHT', bg: 'linear-gradient(135deg,#000,#111)', accent: '#888' },
];

export default function SettingsPanel({ onClose }) {
  const [tab, setTab] = useState('orb'); // orb | dashboard | voice | provider

  // ── Orb settings ──
  const [orbPreset, setOrbPreset] = useState(() => localStorage.getItem('mj_orb_preset') || 'emerald');
  const [orbMode, setOrbMode] = useState(() => localStorage.getItem('mj_orb_mode') || 'repel');
  const [orbCount, setOrbCount] = useState(() => parseInt(localStorage.getItem('mj_orb_count')) || 3500);
  const [orbSize, setOrbSize] = useState(() => parseFloat(localStorage.getItem('mj_orb_size')) || 1.2);
  const [orbPulse, setOrbPulse] = useState(() => parseFloat(localStorage.getItem('mj_orb_pulse')) || 2);
  const [orbRot, setOrbRot] = useState(() => parseInt(localStorage.getItem('mj_orb_rot')) || 5);
  const [orbVolFill, setOrbVolFill] = useState(() => localStorage.getItem('mj_orb_vol') === 'true');
  const [orbHyperGlow, setOrbHyperGlow] = useState(() => localStorage.getItem('mj_orb_glow') === 'true');
  const [orbHoloFX, setOrbHoloFX] = useState(() => localStorage.getItem('mj_orb_holo') !== 'false');

  // ── Dashboard settings ──
  const [dashTheme, setDashTheme] = useState(() => localStorage.getItem('mj_dash_theme') || 'default');
  const [accentColor, setAccentColor] = useState(() => localStorage.getItem('mj_accent') || '#00d4ff');
  const [cardOpacity, setCardOpacity] = useState(() => parseInt(localStorage.getItem('mj_opacity')) || 75);
  const [fontSize, setFontSize] = useState(() => parseInt(localStorage.getItem('mj_fontsize')) || 11);
  const [bgParticles, setBgParticles] = useState(() => parseInt(localStorage.getItem('mj_particles')) || 50);
  const [animations, setAnimations] = useState(() => localStorage.getItem('mj_anims') !== 'false');
  const [blurEffects, setBlurEffects] = useState(() => localStorage.getItem('mj_blur') !== 'false');
  const [compactMode, setCompactMode] = useState(() => localStorage.getItem('mj_compact') === 'true');
  const [showSeconds, setShowSeconds] = useState(() => localStorage.getItem('mj_seconds') !== 'false');

  // ── Voice / Provider ──
  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState('');
  const [voiceSpeed, setVoiceSpeed] = useState(1);
  const [voiceSettings, setVoiceSettings] = useState(null);
  const [provider, setProvider] = useState('');
  const [loading, setLoading] = useState(true);
  const [saveMsg, setSaveMsg] = useState('');

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
      } catch { /* silent */ } finally { setLoading(false); }
    }
    load();
  }, []);

  // ── Orb handlers ──
  const applyOrbPreset = (key) => {
    setOrbPreset(key);
    localStorage.setItem('mj_orb_preset', key);
    const p = ENERGY_PRESETS.find(e => e.key === key);
    if (p) {
      localStorage.setItem('mj_orb_color', p.color);
      window.dispatchEvent(new CustomEvent('orb:color', { detail: p.color }));
    }
  };

  const applyOrbMode = (key) => {
    setOrbMode(key);
    localStorage.setItem('mj_orb_mode', key);
    window.dispatchEvent(new CustomEvent('orb:mode', { detail: key }));
  };

  const setSlider = (setter, lsKey, val, eventName) => {
    setter(val);
    localStorage.setItem(lsKey, String(val));
    if (eventName) window.dispatchEvent(new CustomEvent(eventName, { detail: val }));
  };

  const toggleOrb = (setter, lsKey, current) => {
    const next = !current;
    setter(next);
    localStorage.setItem(lsKey, String(next));
    window.dispatchEvent(new CustomEvent('orb:setting', { detail: { [lsKey]: next } }));
  };

  // ── Dashboard handlers ──
  const applyTheme = (key) => {
    setDashTheme(key);
    localStorage.setItem('mj_dash_theme', key);
    const t = DASH_THEMES.find(d => d.key === key);
    if (t) {
      setAccentColor(t.accent);
      localStorage.setItem('mj_accent', t.accent);
      document.documentElement.style.setProperty('--accent', t.accent);
    }
    window.dispatchEvent(new CustomEvent('dash:theme', { detail: key }));
  };

  const applyAccent = (c) => {
    setAccentColor(c);
    localStorage.setItem('mj_accent', c);
    document.documentElement.style.setProperty('--accent', c);
  };

  const toggleDash = (setter, lsKey, current) => {
    const next = !current;
    setter(next);
    localStorage.setItem(lsKey, String(next));
  };

  const resetDash = () => {
    applyTheme('default');
    setCardOpacity(75); localStorage.setItem('mj_opacity', '75');
    setFontSize(11); localStorage.setItem('mj_fontsize', '11');
    setBgParticles(50); localStorage.setItem('mj_particles', '50');
    setAnimations(true); localStorage.setItem('mj_anims', 'true');
    setBlurEffects(true); localStorage.setItem('mj_blur', 'true');
    setCompactMode(false); localStorage.setItem('mj_compact', 'false');
    setShowSeconds(true); localStorage.setItem('mj_seconds', 'true');
  };

  // ── Voice/Provider handlers ──
  const handleSaveVoice = async () => {
    try {
      await voiceAPI.updateSettings({ ...voiceSettings, voice: selectedVoice, speed: voiceSpeed });
      setSaveMsg('Saved!'); setTimeout(() => setSaveMsg(''), 2000);
    } catch { setSaveMsg('Error saving'); }
  };

  const handleProvider = async (p) => {
    try { await modelAPI.setProvider(p); setProvider(p); } catch { /* silent */ }
  };

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="settings-panel">
        <div className="settings-header">
          <span className="settings-title">{'⚙'} Settings</span>
          <button className="panel-close" onClick={onClose}>{'✕'}</button>
        </div>

        {/* Tab Bar */}
        <div className="settings-tabs">
          {[
            { key: 'orb', label: 'Orb' },
            { key: 'dashboard', label: 'Dashboard' },
            { key: 'voice', label: 'Voice' },
            { key: 'provider', label: 'Provider' },
          ].map(t2 => (
            <button
              key={t2.key}
              className={`settings-tab${tab === t2.key ? ' active' : ''}`}
              onClick={() => setTab(t2.key)}
            >
              {t2.label}
            </button>
          ))}
        </div>

        <div className="settings-body">
          {/* ─── ORB TAB ─── */}
          {tab === 'orb' && (
            <>
              <div className="settings-section">
                <div className="settings-label">ENERGY CORE PRESET</div>
                <div className="os-presets">
                  {ENERGY_PRESETS.map(p => (
                    <button
                      key={p.key}
                      className={`os-preset-btn${orbPreset === p.key ? ' active' : ''}`}
                      onClick={() => applyOrbPreset(p.key)}
                    >
                      <div className="os-preset-dot" style={{ background: p.color, boxShadow: `0 0 10px ${p.shadow}` }} />
                      <span className="os-preset-name">{p.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">INTERACTION MODE</div>
                <div className="os-modes">
                  {INTERACTION_MODES.map(m => (
                    <button
                      key={m.key}
                      className={`os-mode-btn${orbMode === m.key ? ' active' : ''}`}
                      onClick={() => applyOrbMode(m.key)}
                    >
                      <div className="mode-label">{m.label}</div>
                      <div className="mode-desc">{m.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">FINE TUNING</div>
                <div className="os-slider-group">
                  <div className="os-slider-header"><span>Particle Count</span><span>{orbCount.toLocaleString()}</span></div>
                  <input type="range" className="os-slider" min="500" max="8000" step="250" value={orbCount}
                    onChange={e => setSlider(setOrbCount, 'mj_orb_count', parseInt(e.target.value), 'orb:count')} />
                </div>
                <div className="os-slider-group">
                  <div className="os-slider-header"><span>Dot Size</span><span>{orbSize} px</span></div>
                  <input type="range" className="os-slider" min="0.3" max="3.5" step="0.1" value={orbSize}
                    onChange={e => setSlider(setOrbSize, 'mj_orb_size', parseFloat(e.target.value), 'orb:size')} />
                </div>
                <div className="os-slider-group">
                  <div className="os-slider-header"><span>Pulse Speed</span><span>{orbPulse}</span></div>
                  <input type="range" className="os-slider" min="0.5" max="6" step="0.2" value={orbPulse}
                    onChange={e => setSlider(setOrbPulse, 'mj_orb_pulse', parseFloat(e.target.value), 'orb:pulse')} />
                </div>
                <div className="os-slider-group">
                  <div className="os-slider-header"><span>Rotation Speed</span><span>{orbRot}</span></div>
                  <input type="range" className="os-slider" min="1" max="20" step="1" value={orbRot}
                    onChange={e => setSlider(setOrbRot, 'mj_orb_rot', parseInt(e.target.value), 'orb:rot')} />
                </div>
              </div>

              <div className="settings-section">
                <div className="os-toggles">
                  <div className="os-toggle-card">
                    <div className="os-toggle-info"><div className="os-toggle-title">Volume Fill</div><div className="os-toggle-desc">Solid inner core</div></div>
                    <button className={`os-toggle-switch${orbVolFill ? ' on' : ''}`} onClick={() => toggleOrb(setOrbVolFill, 'mj_orb_vol', orbVolFill)}>
                      <div className="os-toggle-knob" />
                    </button>
                  </div>
                  <div className="os-toggle-card">
                    <div className="os-toggle-info"><div className="os-toggle-title">Hyper Glow</div><div className="os-toggle-desc">Max bloom</div></div>
                    <button className={`os-toggle-switch${orbHyperGlow ? ' on' : ''}`} onClick={() => toggleOrb(setOrbHyperGlow, 'mj_orb_glow', orbHyperGlow)}>
                      <div className="os-toggle-knob" />
                    </button>
                  </div>
                  <div className="os-toggle-card">
                    <div className="os-toggle-info"><div className="os-toggle-title">Holo FX</div><div className="os-toggle-desc">Scan lines + rings</div></div>
                    <button className={`os-toggle-switch${orbHoloFX ? ' on' : ''}`} onClick={() => toggleOrb(setOrbHoloFX, 'mj_orb_holo', orbHoloFX)}>
                      <div className="os-toggle-knob" />
                    </button>
                  </div>
                </div>
                <div className="os-tip"><strong>Tip:</strong> Drag the orb to rotate manually. Click inside the sphere to trigger shockwave ripples.</div>
              </div>
            </>
          )}

          {/* ─── DASHBOARD TAB ─── */}
          {tab === 'dashboard' && (
            <>
              <div className="settings-section">
                <div className="settings-label">THEME</div>
                <div className="dsp-theme-grid">
                  {DASH_THEMES.map(t2 => (
                    <div
                      key={t2.key}
                      className={`dsp-theme-swatch${dashTheme === t2.key ? ' active' : ''}`}
                      style={{ background: t2.bg }}
                      onClick={() => applyTheme(t2.key)}
                    >
                      <span style={{ color: t2.accent, fontSize: 9 }}>{t2.name}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">ACCENT COLOR</div>
                <div className="dsp-color-row">
                  <input type="color" value={accentColor} onChange={e => applyAccent(e.target.value)} className="dsp-color-picker" />
                  <span className="dsp-hex">{accentColor}</span>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">CARD OPACITY</div>
                <div className="dsp-slider-row">
                  <input type="range" min="0" max="100" value={cardOpacity} className="dsp-slider"
                    onChange={e => { setCardOpacity(parseInt(e.target.value)); localStorage.setItem('mj_opacity', e.target.value); }} />
                  <span className="dsp-val">{cardOpacity}%</span>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">FONT SIZE</div>
                <div className="dsp-slider-row">
                  <input type="range" min="8" max="16" value={fontSize} className="dsp-slider"
                    onChange={e => { setFontSize(parseInt(e.target.value)); localStorage.setItem('mj_fontsize', e.target.value); }} />
                  <span className="dsp-val">{fontSize}px</span>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">BACKGROUND PARTICLES</div>
                <div className="dsp-slider-row">
                  <input type="range" min="0" max="200" value={bgParticles} className="dsp-slider"
                    onChange={e => { setBgParticles(parseInt(e.target.value)); localStorage.setItem('mj_particles', e.target.value); }} />
                  <span className="dsp-val">{bgParticles}</span>
                </div>
              </div>

              <div className="settings-section">
                <div className="settings-label">OPTIONS</div>
                <div className="dsp-toggle-row"><span>Animations</span>
                  <button className={`os-toggle-switch${animations ? ' on' : ''}`} onClick={() => toggleDash(setAnimations, 'mj_anims', animations)}><div className="os-toggle-knob" /></button>
                </div>
                <div className="dsp-toggle-row"><span>Blur Effects</span>
                  <button className={`os-toggle-switch${blurEffects ? ' on' : ''}`} onClick={() => toggleDash(setBlurEffects, 'mj_blur', blurEffects)}><div className="os-toggle-knob" /></button>
                </div>
                <div className="dsp-toggle-row"><span>Compact Mode</span>
                  <button className={`os-toggle-switch${compactMode ? ' on' : ''}`} onClick={() => toggleDash(setCompactMode, 'mj_compact', compactMode)}><div className="os-toggle-knob" /></button>
                </div>
                <div className="dsp-toggle-row"><span>Show Seconds</span>
                  <button className={`os-toggle-switch${showSeconds ? ' on' : ''}`} onClick={() => toggleDash(setShowSeconds, 'mj_seconds', showSeconds)}><div className="os-toggle-knob" /></button>
                </div>
                <button className="dsp-reset-btn" onClick={resetDash}>Reset to Default</button>
              </div>
            </>
          )}

          {/* ─── VOICE TAB ─── */}
          {tab === 'voice' && (
            <div className="settings-section">
              <div className="settings-label">VOICE</div>
              {loading ? <div className="settings-loading">Loading voices...</div> : voices.length === 0 ? (
                <div className="settings-loading">No voices available</div>
              ) : (
                <>
                  <select className="settings-select" value={selectedVoice} onChange={e => setSelectedVoice(e.target.value)}>
                    {voices.map(v => (
                      <option key={typeof v === 'string' ? v : v.id} value={typeof v === 'string' ? v : v.id}>
                        {typeof v === 'string' ? v : v.name || v.id}
                      </option>
                    ))}
                  </select>
                  <div className="settings-sublabel" style={{ marginTop: 8 }}>Speed: {voiceSpeed.toFixed(1)}x</div>
                  <input type="range" min="0.5" max="2" step="0.1" value={voiceSpeed}
                    onChange={e => setVoiceSpeed(parseFloat(e.target.value))} className="settings-range" />
                  <button className="settings-save-btn" onClick={handleSaveVoice}>SAVE VOICE SETTINGS</button>
                  {saveMsg && <div className="settings-save-msg">{saveMsg}</div>}
                </>
              )}
            </div>
          )}

          {/* ─── PROVIDER TAB ─── */}
          {tab === 'provider' && (
            <div className="settings-section">
              <div className="settings-label">AI PROVIDER</div>
              <div className="settings-provider-btns">
                <button className={`settings-provider-btn${provider === 'ollama' ? ' active' : ''}`}
                  onClick={() => handleProvider('ollama')}>Ollama (Local)</button>
                <button className={`settings-provider-btn${provider === 'groq' ? ' active' : ''}`}
                  onClick={() => handleProvider('groq')}>Groq (Cloud)</button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
