/**
 * VoiceLangSelector — Dropdown for voice recognition language selection.
 */
import { useState } from 'react';

const LANGUAGES = [
  { code: 'en-US', label: 'English (US)' },
  { code: 'en-IN', label: 'English (India)' },
  { code: 'hi-IN', label: 'Hindi' },
  { code: 'en-GB', label: 'English (UK)' },
  { code: 'es-ES', label: 'Spanish' },
  { code: 'fr-FR', label: 'French' },
  { code: 'de-DE', label: 'German' },
  { code: 'ja-JP', label: 'Japanese' },
  { code: 'zh-CN', label: 'Chinese' },
];

export default function VoiceLangSelector() {
  const [lang, setLang] = useState(() => localStorage.getItem('mj_voice_lang') || 'en-US');

  const handleChange = (e) => {
    const val = e.target.value;
    setLang(val);
    localStorage.setItem('mj_voice_lang', val);
    window.dispatchEvent(new CustomEvent('voice:lang', { detail: val }));
  };

  return (
    <div className="voice-lang-selector">
      <label className="voice-lang-label">Voice Language</label>
      <select className="voice-lang-select" value={lang} onChange={handleChange}>
        {LANGUAGES.map(l => (
          <option key={l.code} value={l.code}>{l.label}</option>
        ))}
      </select>
    </div>
  );
}
