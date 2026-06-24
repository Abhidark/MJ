/**
 * HoloToggle — Holographic mode toggle button for the orb card.
 */
import { useState } from 'react';

export default function HoloToggle() {
  const [holo, setHolo] = useState(() => localStorage.getItem('mj_orb_holo') !== 'false');

  const toggle = () => {
    const next = !holo;
    setHolo(next);
    localStorage.setItem('mj_orb_holo', String(next));
    window.dispatchEvent(new CustomEvent('orb:setting', { detail: { mj_orb_holo: next } }));
    window.dispatchEvent(new CustomEvent('toast', {
      detail: { message: next ? 'Holographic FX enabled' : 'Holographic FX disabled', type: next ? 'success' : 'info' }
    }));
  };

  return (
    <button
      className={`holo-toggle-btn${holo ? ' active' : ''}`}
      onClick={toggle}
      title="Holographic Mode"
    >
      ◊
    </button>
  );
}
