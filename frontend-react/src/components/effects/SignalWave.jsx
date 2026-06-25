import { useRef, useEffect, useState } from 'react';
import * as audioAnalyser from '@/services/audioAnalyser';

/**
 * SignalWave — scrolling signal waveform for the AI Flow panel.
 * Ported from old index.html `#af-wave`, but driven by REAL audio:
 * while MJ speaks, the wave amplitude tracks the actual voice level (RMS)
 * and the line shape uses the analyser's time-domain data. When silent it
 * settles to a gentle idle ripple. Shows live Freq / Amp readouts.
 *
 * 60fps, cyan/blue glow, pauses when tab hidden, low CPU when idle.
 */
const SAMPLES = 120;

export default function SignalWave({ height = 70 }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const [freq, setFreq] = useState('0.0');
  const [amp, setAmp] = useState('0.00');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const wave = new Float32Array(SAMPLES);
    let phase = 0;
    let frame = 0;

    function resize() {
      const w = canvas.clientWidth || 1;
      const h = canvas.clientHeight || 1;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    function draw() {
      rafRef.current = requestAnimationFrame(draw);
      if (document.hidden) return;
      frame++;

      const W = canvas.clientWidth || 1;
      const H = canvas.clientHeight || 1;
      const active = audioAnalyser.isPlaying();
      const level = active ? audioAnalyser.getLevel() : 0;     // real RMS 0..1

      // Amplitude: real voice level when speaking, soft idle ripple otherwise
      const amplitude = active ? Math.min(1, 0.15 + level * 2.2) : 0.12;
      phase += active ? 0.12 + level * 0.25 : 0.03;

      // Shift buffer; append new sample (real time-domain tap when speaking)
      for (let i = 0; i < SAMPLES - 1; i++) wave[i] = wave[i + 1];
      let sample;
      if (active) {
        const td = audioAnalyser.getTimeDomainData();
        const raw = td ? (td[td.length >> 1] - 128) / 128 : 0;
        sample = raw * amplitude * 2.0 + Math.sin(phase) * amplitude * 0.25;
      } else {
        sample = Math.sin(phase) * amplitude + Math.sin(phase * 2.7) * amplitude * 0.3;
      }
      wave[SAMPLES - 1] = Math.max(-1, Math.min(1, sample));

      ctx.clearRect(0, 0, W, H);

      // Center line
      ctx.strokeStyle = 'rgba(0,180,255,0.08)';
      ctx.lineWidth = 0.5;
      ctx.beginPath(); ctx.moveTo(0, H / 2); ctx.lineTo(W, H / 2); ctx.stroke();

      // Main signal
      ctx.strokeStyle = 'rgba(0,210,255,0.7)';
      ctx.lineWidth = 1.5;
      ctx.shadowBlur = 8;
      ctx.shadowColor = 'rgba(0,212,255,0.35)';
      ctx.beginPath();
      for (let i = 0; i < SAMPLES; i++) {
        const x = (i / SAMPLES) * W;
        const y = H / 2 + wave[i] * H * 0.4;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();

      // Secondary echo wave
      ctx.strokeStyle = 'rgba(0,120,255,0.22)';
      ctx.lineWidth = 1;
      ctx.shadowBlur = 4;
      ctx.beginPath();
      for (let i = 0; i < SAMPLES; i++) {
        const x = (i / SAMPLES) * W;
        const y = H / 2 + wave[Math.max(0, i - 8)] * H * 0.28;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Readouts ~6x/sec
      if (frame % 10 === 0) {
        if (active) {
          const bin = audioAnalyser.getDominantBin();
          const sr = audioAnalyser.getSampleRate();
          const binCount = audioAnalyser.getBinCount() || 128;
          const hz = (bin / binCount) * (sr / 2);
          setFreq((hz / 1000).toFixed(1));   // kHz
          setAmp(level.toFixed(2));
        } else {
          setFreq('0.0');
          setAmp('0.00');
        }
      }
    }
    draw();

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, []);

  return (
    <div className="aiflow-viz-section">
      <div className="aiflow-viz-head">
        <span className="aiflow-section-label">SIGNAL ANALYSIS</span>
        <span className="aiflow-viz-stats">
          <span className="vstat">Freq: <b>{freq} kHz</b></span>
          <span className="vstat">Amp: <b>{amp}</b></span>
        </span>
      </div>
      <canvas ref={canvasRef} className="aiflow-viz-canvas" style={{ height }} />
    </div>
  );
}
