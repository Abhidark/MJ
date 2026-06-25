/**
 * audioAnalyser — shared Web Audio FFT engine for MJ's voice spectrum.
 *
 * Single AudioContext + AnalyserNode for the whole app. The MJ TTS audio
 * element (created in useVoice.speak) is routed through this analyser so the
 * spectrum visualizer reads REAL frequency data from the voice stream —
 * not a synthetic animation.
 *
 * Usage:
 *   import * as audioAnalyser from '@/services/audioAnalyser';
 *   audioAnalyser.attach(audioElement);     // wire a playing <audio> in
 *   const data = audioAnalyser.getFrequencyData(); // Uint8Array of bins
 *   audioAnalyser.isPlaying();               // true while MJ speaks
 */

let ctx = null;
let analyser = null;
let freqData = null;
const attached = new WeakSet();   // each Audio element may be wired only once
let activeEl = null;              // the element currently routed/playing

function ensureCtx() {
  if (ctx) return ctx;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;            // Web Audio unsupported
  try {
    ctx = new AC();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 256;                 // 128 frequency bins — cheap, smooth
    analyser.smoothingTimeConstant = 0.8;   // natural decay between frames
    freqData = new Uint8Array(analyser.frequencyBinCount);
    analyser.connect(ctx.destination);      // keep audio audible through the graph
  } catch (e) {
    ctx = null;
    return null;
  }
  return ctx;
}

/**
 * Route an HTMLAudioElement through the analyser. Safe to call repeatedly;
 * each element is wired only once (createMediaElementSource is one-shot).
 */
export function attach(audioEl) {
  if (!audioEl) return;
  const c = ensureCtx();
  if (!c) return;
  try {
    if (c.state === 'suspended') c.resume().catch(() => {});
    if (!attached.has(audioEl)) {
      const src = c.createMediaElementSource(audioEl);
      src.connect(analyser);                // analyser → destination (set in ensureCtx)
      attached.add(audioEl);
    }
    activeEl = audioEl;
    const clear = () => { if (activeEl === audioEl) activeEl = null; };
    audioEl.addEventListener('ended', clear);
    audioEl.addEventListener('pause', clear);
    audioEl.addEventListener('error', clear);
  } catch (e) {
    // Cross-origin/tainted media or unsupported browser — fail silently,
    // visualizer just stays idle.
  }
}

/** Latest byte frequency data (0–255 per bin), or null if not ready. */
export function getFrequencyData() {
  if (!analyser) return null;
  analyser.getByteFrequencyData(freqData);
  return freqData;
}

/** Number of frequency bins available. */
export function getBinCount() {
  return analyser ? analyser.frequencyBinCount : 0;
}

/** True while MJ's voice is actively playing. */
export function isPlaying() {
  return !!(activeEl && !activeEl.paused && !activeEl.ended && activeEl.currentTime > 0);
}
