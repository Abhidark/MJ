import { useRef, useEffect } from 'react';
import * as audioAnalyser from '@/services/audioAnalyser';

/**
 * AudioSpectrum — real-time FFT spectrum analyzer for MJ's voice.
 *
 * Reads live frequency data from the shared Web Audio analyser (fed by the
 * TTS audio stream in useVoice). Renders glowing cyan/blue frequency bars at
 * 60fps. Auto fades IN while MJ speaks and OUT when silent. Pauses when the
 * browser tab is hidden. Fully decoupled — needs no props/state from voice.
 *
 * Cyberpunk/holographic MJ theme. Low CPU: idle frames clear once and bail.
 */
export default function AudioSpectrum({ bars = 36, height = 96 }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const fadeRef = useRef(0);                  // 0..1 visibility envelope

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const smooth = new Float32Array(bars);

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
      if (document.hidden) return;            // pause off-screen

      const w = canvas.clientWidth || 1;
      const h = canvas.clientHeight || 1;
      const playing = audioAnalyser.isPlaying();

      // Smoothly fade the whole spectrum in/out
      fadeRef.current += ((playing ? 1 : 0) - fadeRef.current) * 0.12;

      // Idle & invisible → clear once, skip heavy work (low CPU when silent)
      if (!playing && fadeRef.current < 0.015) {
        ctx.clearRect(0, 0, w, h);
        return;
      }

      ctx.clearRect(0, 0, w, h);
      const data = audioAnalyser.getFrequencyData();
      const binCount = audioAnalyser.getBinCount();
      const alpha = fadeRef.current;
      const slot = w / bars;
      const bw = Math.max(2, slot - 2);

      for (let i = 0; i < bars; i++) {
        let v = 0;
        if (data && binCount) {
          // Use lower ~80% of bins (speech energy lives there; top bins are quiet)
          const idx = Math.floor((i / bars) * binCount * 0.8);
          v = data[idx] / 255;
        }
        // Mild idle shimmer so the bars aren't dead-flat during the fade tail
        if (!playing) v *= 0.0;
        smooth[i] += (v - smooth[i]) * 0.35;

        const bh = Math.max(2, smooth[i] * h * 0.95);
        const x = i * slot + 1;
        const y = h - bh;

        const grad = ctx.createLinearGradient(0, y, 0, h);
        grad.addColorStop(0, `rgba(0,229,255,${(0.55 + smooth[i] * 0.4) * alpha})`);
        grad.addColorStop(1, `rgba(0,120,220,${0.10 * alpha})`);
        ctx.fillStyle = grad;
        ctx.shadowBlur = 8 * alpha;
        ctx.shadowColor = `rgba(0,212,255,${0.5 * alpha})`;
        ctx.fillRect(x, y, bw, bh);

        // Mirrored reflection (holographic feel)
        ctx.globalAlpha = 0.12 * alpha;
        ctx.fillRect(x, h, bw, Math.min(bh * 0.4, h * 0.3));
        ctx.globalAlpha = 1;
      }
      ctx.shadowBlur = 0;
    }

    draw();
    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [bars]);

  return (
    <div className="mj-spectrum">
      <canvas ref={canvasRef} className="mj-spectrum-canvas" style={{ height }} />
    </div>
  );
}
