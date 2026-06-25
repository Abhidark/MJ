# Audio Spectrum Analyzer — Investigation & Restore Report
_MJ Assistant · 25 June 2026_

## Phase 1 — Root Cause Analysis

### 1. Where it lived in the OLD UI
The old monolithic UI (`frontend/index.html`, 8,392 lines) had a right-side panel `#ai-flow-panel` with **four stacked canvas sections** (HTML at lines 4080–4118):

| Section | Canvas id | What it drew |
|---|---|---|
| Neural Network | `#af-brain` | Animated neural node graph |
| **Signal Analysis** | `#af-wave` | **Scrolling waveform + Freq/Amp stats** ← the "spectrum" |
| **Data Flow** | `#af-bars` | **32 animated frequency bars** ← the "spectrum bars" |
| Inference Field | `#af-field` | Particle field |

The render loop was at `index.html` lines 6089–6310 (`animate()`), driven by `requestAnimationFrame`.

### 2. How it was driven (important finding)
The waveform and bars were **NOT real audio / FFT**. They were **synthetic animation**:

```js
// index.html ~6268
const amp  = isActive ? 0.6 + Math.random()*0.3 : 0.15 + Math.random()*0.1;
waveData[...] = Math.sin(wavePhase)*amp + Math.sin(wavePhase*2.7)*amp*0.3 + (Math.random()-0.5)*amp*0.4;
// bars:
const target = isActive ? 0.3 + Math.random()*0.6 : 0.05 + Math.random()*0.15;
```

`isActive` came from a global state flag:

```js
window._aiFlowSetState = function(state){ aiState = state; };       // index.html ~6141
// set from the orb state machine:
if (window._aiFlowSetState) window._aiFlowSetState(state);          // setOrbState(), ~4308
```

And `setOrbState("speaking")` was fired by the TTS function `speakText()` (lines 5932–5950) when MJ's audio started:

```js
mjAudio = new Audio(API + data.audio_url);
setOrbState("speaking");           // → _aiFlowSetState("speaking") → bars/wave go "active"
mjAudio.onended = () => setOrbState(...idle...);
```

**So the old spectrum *looked* like it reacted to MJ's voice, but it was procedurally generated `Math.sin + random`, merely gated on the "speaking" flag.** The only real `AudioContext` in the whole repo was in `frontend/dashboard.html` (line 964) — a separate, unused page, not the main UI.

### 3. Current status in React (`frontend-react/`)
- **`AIFlowPanel.jsx`** was **rewritten from scratch** as a *text pipeline* (INPUT → INTENT → MEMORY → ROUTING → INFERENCE → TOOLS → RESPONSE → LEARN) with `FlowNode` rows and a log list. **It contains no `<canvas>` at all.**
- A repo-wide search of `frontend-react/src/` for `AnalyserNode`, `createAnalyser`, `getByteFrequencyData`, `AudioContext`, `spectrum`, `fftSize`, `af-wave`, `af-bars`, `_aiFlowSetState` → **zero matches.** Nothing audio-visual was ported.
- `useVoice.js` `speak()` does create the MJ audio element (`const audio = new Audio(data.audio_url)`) and sets `orbState='speaking'`, but **does not expose the element** or any analyser.
- `App.jsx` renders `<AIFlowPanel modelInfo={null} chatStage={null} />` — hardcoded nulls — and **does not even use `useVoice`** (voice is instantiated inside `DashboardGrid.jsx`). So the right panel is effectively static.

### 4. Exact reason it disappeared
**Migration regression — feature was dropped, not broken.** During the React migration, the right-panel `#ai-flow-panel` (4 canvases) was replaced by a completely different text-based `AIFlowPanel` component. The Signal Analysis waveform and Data Flow bars (what you remember as the spectrum analyzer) were never re-implemented in React.

It is **not** a CSS/z-index/visibility bug and **not** a broken import — the canvas code simply does not exist in the React codebase.

### 5. Decision
- Old code cannot be "reconnected" because (a) it doesn't exist in React, and (b) even the original was fake animation.
- Your new requirements explicitly ask for **real FFT / Web Audio / AnalyserNode reacting to actual TTS volume**.

➡️ **Phase 2 = build a NEW real-audio spectrum analyzer** (the old one was synthetic + missing), placed in the right panel, themed to match MJ, and wired to the real MJ TTS audio stream.

---

## Phase 2 — Restore Plan (implemented)
1. **`src/services/audioAnalyser.js`** (new) — singleton Web Audio engine: one `AudioContext`, `attach(audioEl)` → `createMediaElementSource` + `AnalyserNode` (fftSize 256), `getFrequencyData()`. Real FFT, low CPU.
2. **`src/hooks/useVoice.js`** (edit) — in `speak()`, after creating the `Audio` element, call `audioAnalyser.attach(audio)` so the analyser taps the real MJ voice stream.
3. **`src/components/effects/AudioSpectrum.jsx`** (new) — canvas component, 60 fps `requestAnimationFrame`, reads `getByteFrequencyData`, draws cyan/blue glowing bars; **auto-shows while audio energy is present, fades out when silent**; pauses on tab-hidden.
4. **`src/components/panels/AIFlowPanel.jsx`** (edit) — render `<AudioSpectrum />` in a "SIGNAL ANALYSIS" section (right panel, matching old location).
5. **`src/styles/panels.css`** (edit) — cyberpunk cyan glow styling, smooth transitions, no layout break.

### Files Modified / Created

| File | Type | Change |
|---|---|---|
| `src/services/audioAnalyser.js` | **NEW** | Web Audio singleton: one `AudioContext` + `AnalyserNode` (fftSize 256), `attach(audioEl)` via `createMediaElementSource`, `getFrequencyData()`, `isPlaying()`. Real FFT. |
| `src/components/effects/AudioSpectrum.jsx` | **NEW** | Canvas spectrum component. 60fps rAF, reads `getByteFrequencyData`, 36 glowing cyan bars + mirrored reflection, fade in/out on voice energy, pauses on tab-hidden, cheap idle frames. |
| `src/hooks/useVoice.js` | EDIT | Import analyser; in `speak()` after `new Audio(...)` call `audioAnalyser.attach(audio)` to tap the real voice stream. |
| `src/components/panels/AIFlowPanel.jsx` | EDIT | Import + render `<AudioSpectrum bars={36} height={96} />` inside a new "SIGNAL ANALYSIS" section (right panel). |
| `src/styles/panels.css` | EDIT | `.aiflow-signal`, `.aiflow-section-label`, `.mj-spectrum`, `.mj-spectrum-canvas` — cyberpunk cyan glow, holographic baseline, smooth transitions. |

### Before vs After

| | OLD (index.html) | NEW (React) |
|---|---|---|
| Data source | `Math.sin + random` (fake) | **Real FFT** from MJ TTS audio (`AnalyserNode`) |
| Trigger | `aiState` flag (orb state) | **Actual audio energy** of the voice stream |
| Location | Right panel `#ai-flow-panel` | Right panel `AIFlowPanel` → SIGNAL ANALYSIS |
| Rendering | Canvas, ~60fps | Canvas, 60fps, DPR-aware, tab-hidden pause |
| Reacts to volume | No (random) | **Yes — bar height = real frequency magnitude** |
| Hidden when silent | Stayed animating low | **Fades out, idle frames skip drawing** |

### How it satisfies the requirements
- Real-time FFT ✓ · Web Audio API + AnalyserNode ✓ · React component ✓ · 60fps ✓
- Reacts to actual MJ voice volume (not random) ✓ · Auto show while speaking / fade when silent ✓
- Cyan/blue cyberpunk glow ✓ · Right panel ✓ · Low CPU (idle bail + tab-pause) ✓

### Verification status
- `audioAnalyser.js` + `AudioSpectrum.jsx` → **esbuild parse: OK**.
- `useVoice.js` + `AIFlowPanel.jsx` → esbuild parsed cleanly **through the edited code**; the only error was at end-of-file due to a known sandbox mount truncation (the Linux sandbox served truncated tails of several files, including `App.jsx` which was not modified). The real Windows files are complete.
- **Final build must be run on Windows** (per project workflow): `npm run build` in `frontend-react/`. The sandbox cannot run the full bundle build today because of the mount truncation, not because of a code error.

### Notes / caveats
- The React right panel (`AIFlowPanel`) is **toggle-based** (header "AI FLOW" button) — it isn't always visible like the old always-on panel. The spectrum shows inside it. If you want it always visible while MJ speaks, we can promote `AudioSpectrum` to a standalone always-mounted element near the orb — say the word.
- `createMediaElementSource` requires the TTS audio to be **same-origin** (it is — FastAPI serves both the React build and `/audio/...`). Cross-origin would silence the analyser; the code fails safe (visualizer stays idle, audio still plays).
- Screenshots require a running Windows build + backend (TTS audio). Once you run `npm run build` and start the backend, open the right "AI FLOW" panel and speak — bars will move with MJ's voice.
