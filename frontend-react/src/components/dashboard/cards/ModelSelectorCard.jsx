import { useState, useEffect, useCallback } from 'react';
import { modelAPI } from '@/services/api';

/**
 * ModelSelectorCard — shows installed models, active model, Groq vs Ollama provider
 * Polls GET /models every 60s. Click model to set active.
 */

const MODEL_ICONS = {
  mistral: '🌬️', llama: '🦙', gemma: '💎', phi: 'φ', qwen: '🏮',
  deepseek: '🔍', codellama: '💻', llava: '👁️', neural: '🧠',
  vicuna: '🦙', starcoder: '⭐', wizard: '🧙', openchat: '💬',
  dolphin: '🐬', nous: '🧪', solar: '☀️', yi: '🇨🇳',
  mixtral: '🌀', command: '⌘', default: '🤖',
};

function getIcon(name) {
  const short = (name || '').split(':')[0].toLowerCase();
  return MODEL_ICONS[short] || MODEL_ICONS.default;
}

function getDisplayName(name) {
  const short = (name || '').split(':')[0];
  return short.charAt(0).toUpperCase() + short.slice(1);
}

export default function ModelSelectorCard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [setting, setSetting] = useState(false);

  const fetchModels = useCallback(async () => {
    try {
      const res = await modelAPI.getModels();
      setData(res.data);
    } catch (e) {
      console.log('[MJ] Failed to load models:', e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
    const timer = setInterval(fetchModels, 60000);
    return () => clearInterval(timer);
  }, [fetchModels]);

  const setActiveModel = useCallback(async (model) => {
    if (setting) return;
    setSetting(true);
    try {
      await fetch('/models/set-active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model }),
      });
      await fetchModels();
    } catch (e) {
      console.log('[MJ] Failed to set model:', e.message);
    } finally {
      setSetting(false);
    }
  }, [setting, fetchModels]);

  const toggleAutoSelect = useCallback(async () => {
    if (!data) return;
    try {
      await fetch('/models/auto-select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !data.auto_select }),
      });
      await fetchModels();
    } catch (e) {
      console.log('[MJ] Failed to toggle auto:', e.message);
    }
  }, [data, fetchModels]);

  if (loading) {
    return <div className="model-loading">Loading models...</div>;
  }

  if (!data) {
    return <div className="model-loading">Failed to connect</div>;
  }

  const models = data.models || [];
  const active = data.active || '';
  const isAuto = data.auto_select;
  const provider = data.provider || 'ollama';
  const isGroq = provider === 'groq';
  const groqAvail = data.groq?.available;

  return (
    <div className="model-selector-content">
      {/* Badges */}
      <div className="model-badges">
        <span
          className={`zeus-auto-badge ${isAuto ? 'auto' : 'manual'}`}
          onClick={toggleAutoSelect}
          title={isAuto ? 'Click for manual mode' : 'Click for auto mode'}
          style={{ cursor: 'pointer' }}
        >
          {isAuto ? 'AUTO' : 'MANUAL'}
        </span>
        <span className={`zeus-auto-badge provider ${isGroq ? 'groq' : 'ollama'}`}>
          {isGroq ? 'GROQ ☁️' : 'OLLAMA'}
        </span>
        {groqAvail && !isGroq && (
          <span className="zeus-auto-badge groq-avail">GROQ ✓</span>
        )}
      </div>

      {/* Model grid */}
      {models.length === 0 ? (
        <div className="model-empty">No models installed</div>
      ) : (
        <div className="zeus-models">
          {models.map((m) => (
            <div
              key={m.name}
              className={`zeus-model${m.name === active ? ' active' : ''}${setting ? ' disabled' : ''}`}
              onClick={() => !isAuto && setActiveModel(m.name)}
              title={isAuto ? 'Disable auto-select to choose manually' : `Set ${m.name} as active`}
            >
              <div className="zm-dot" />
              <div className="zm-icon">{getIcon(m.name)}</div>
              <div className="zm-info">
                <div className="zm-name">
                  {getDisplayName(m.name)}
                  {m.size && <span className="zm-size"> ({m.size})</span>}
                </div>
                <div className="zm-role">
                  {data.model_map
                    ? Object.entries(data.model_map)
                        .filter(([, v]) => v === m.name)
                        .map(([k]) => k)
                        .join(', ') || 'general'
                    : 'general'}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
