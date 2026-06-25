import { useRef, useEffect, useState } from 'react';
import * as audioAnalyser from '@/services/audioAnalyser';

/**
 * NeuralNetwork — animated neural node-graph for the AI Flow panel.
 * Ported from the old index.html `#af-brain` canvas. Nodes fire and pulse;
 * firing rate rises while MJ is speaking (real audio activity). Reports a
 * live "active" count for the header readout.
 *
 * Cyberpunk cyan/blue theme. Pauses when the tab is hidden.
 */
const NODE_COUNT = 48;

export default function NeuralNetwork({ height = 130 }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);
  const [activeCount, setActiveCount] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // Build nodes in oval clusters (matches old layout)
    const nodes = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      const layer = Math.floor(i / 12);
      const angle = (i % 12) * (Math.PI * 2 / 12) + layer * 0.4;
      const rx = 0.22 + layer * 0.08 + Math.random() * 0.06;
      const ry = 0.18 + layer * 0.06 + Math.random() * 0.05;
      nodes.push({
        x: 0.5 + Math.cos(angle) * rx,
        y: 0.48 + Math.sin(angle) * ry,
        r: 1.5 + Math.random() * 1.5,
        pulse: Math.random() * Math.PI * 2,
        fire: 0,
      });
    }
    // Edges between nearby nodes
    const edges = [];
    for (let i = 0; i < NODE_COUNT; i++) {
      for (let j = i + 1; j < NODE_COUNT; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        if (Math.sqrt(dx * dx + dy * dy) < 0.18) {
          edges.push([i, j, Math.random() * 0.3 + 0.05]);
        }
      }
    }

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

    let time = 0;
    let frame = 0;

    function draw() {
      rafRef.current = requestAnimationFrame(draw);
      if (document.hidden) return;
      time += 0.016;
      frame++;

      const W = canvas.clientWidth || 1;
      const H = canvas.clientHeight || 1;
      const active = audioAnalyser.isPlaying();
      const level = active ? audioAnalyser.getLevel() : 0;
      const fireRate = active ? 0.15 + level * 0.5 : 0.04;

      ctx.clearRect(0, 0, W, H);

      if (Math.random() < fireRate) {
        nodes[Math.floor(Math.random() * NODE_COUNT)].fire = 1;
      }

      // Edges
      for (const [i, j, a] of edges) {
        const ni = nodes[i], nj = nodes[j];
        const fire = Math.max(ni.fire, nj.fire);
        ctx.strokeStyle = `rgba(0,180,255,${a * (0.3 + fire * 0.7)})`;
        ctx.lineWidth = 0.5 + fire;
        ctx.beginPath();
        ctx.moveTo(ni.x * W, ni.y * H);
        ctx.lineTo(nj.x * W, nj.y * H);
        ctx.stroke();
        if (fire > 0.3) {
          const t = (time * 3) % 1;
          ctx.fillStyle = `rgba(0,220,255,${fire * 0.6})`;
          ctx.beginPath();
          ctx.arc(ni.x * W + (nj.x - ni.x) * W * t, ni.y * H + (nj.y - ni.y) * H * t, 1.5, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      // Nodes
      let count = 0;
      for (const n of nodes) {
        n.fire *= 0.95;
        const pulse = Math.sin(time * 2 + n.pulse) * 0.3 + 0.7;
        const glow = n.fire > 0.1 ? n.fire : 0;
        if (n.fire > 0.1) count++;
        if (glow > 0) {
          ctx.fillStyle = `rgba(0,200,255,${glow * 0.15})`;
          ctx.beginPath();
          ctx.arc(n.x * W, n.y * H, n.r * 6, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = `rgba(0,${160 + glow * 60},255,${0.3 + glow * 0.5 + pulse * 0.2})`;
        ctx.beginPath();
        ctx.arc(n.x * W, n.y * H, n.r + glow * 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Update header count ~6x/sec (avoid re-render spam)
      if (frame % 10 === 0) setActiveCount(count);
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
        <span className="aiflow-section-label">NEURAL NETWORK</span>
        <span className="aiflow-viz-stats">
          <span className="vstat">Nodes: <b>{NODE_COUNT}</b></span>
          <span className="vstat">Active: <b>{activeCount}</b></span>
        </span>
      </div>
      <canvas ref={canvasRef} className="aiflow-viz-canvas" style={{ height }} />
    </div>
  );
}
