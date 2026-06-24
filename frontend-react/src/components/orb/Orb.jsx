import { useRef, useEffect, useCallback } from 'react';

/**
 * Orb — 3D interactive particle sphere rendered on canvas
 *
 * States: idle, listening, thinking, speaking, error
 * - 3500 particles on spherical shell with spring physics
 * - Mouse/touch interaction: drag to rotate, click for ripple
 * - Color lerps between state presets
 * - 30fps when idle, 60fps when active
 * - Pauses when tab not visible
 * - Holographic scan line + depth rings
 */

const SIZE = 320;
const PARTICLE_COUNT = 3500;
const ORB_RADIUS = 120;
const FOV = 350;

const STATE_PRESETS = {
  idle:      { primary: '#00d4ff', glow: '#0088cc', speed: 1 },
  listening: { primary: '#00ffcc', glow: '#00cc99', speed: 1.5 },
  thinking:  { primary: '#ffd900', glow: '#eab308', speed: 3 },
  speaking:  { primary: '#b92eff', glow: '#8b5cf6', speed: 2 },
  error:     { primary: '#ff3b30', glow: '#f97316', speed: 4 },
};

function hexToRgb(hex) {
  return {
    r: parseInt(hex.slice(1, 3), 16),
    g: parseInt(hex.slice(3, 5), 16),
    b: parseInt(hex.slice(5, 7), 16),
  };
}

class Particle {
  constructor(bx, by, bz) {
    this.bx = bx; this.by = by; this.bz = bz;
    this.px = bx + (Math.random() - 0.5) * 10;
    this.py = by + (Math.random() - 0.5) * 10;
    this.pz = bz + (Math.random() - 0.5) * 10;
    this.vx = 0; this.vy = 0; this.vz = 0;
    this.twinkle = Math.random() * Math.PI * 2;
    this.size = 0.5 + Math.random() * 0.8;
  }
  rotate(ax, ay) {
    if (ay !== 0) {
      const c = Math.cos(ay), s = Math.sin(ay);
      const x2 = this.bx * c + this.bz * s;
      const z2 = -this.bx * s + this.bz * c;
      this.bx = x2; this.bz = z2;
    }
    if (ax !== 0) {
      const c = Math.cos(ax), s = Math.sin(ax);
      const y2 = this.by * c - this.bz * s;
      const z2 = this.by * s + this.bz * c;
      this.by = y2; this.bz = z2;
    }
  }
}

function createParticles() {
  const particles = [];
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = ORB_RADIUS + (Math.random() - 0.5) * (ORB_RADIUS * 0.04);
    particles.push(new Particle(
      r * Math.sin(phi) * Math.cos(theta),
      r * Math.sin(phi) * Math.sin(theta),
      r * Math.cos(phi)
    ));
  }
  return particles;
}

export default function Orb({ state = 'idle', onClick }) {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const stateRef = useRef(state);
  const particlesRef = useRef(null);
  const mouseRef = useRef({ x: -1000, y: -1000, hovering: false });
  const dragRef = useRef({ active: false, sx: 0, sy: 0, vx: 0, vy: 0 });
  const ripplesRef = useRef([]);
  const colorRef = useRef({ cur: hexToRgb('#00d4ff'), tar: hexToRgb('#00d4ff') });
  const pulseRef = useRef(0);
  const clickReactRef = useRef(0);
  const lastFrameRef = useRef(0);
  const sortCacheRef = useRef(null);
  const frameCountRef = useRef(0);

  // Update state ref when prop changes
  useEffect(() => {
    stateRef.current = state;
    const preset = STATE_PRESETS[state] || STATE_PRESETS.idle;
    colorRef.current.tar = hexToRgb(preset.primary);
  }, [state]);

  // ─── Mouse/Touch handlers ───
  const getPos = useCallback((e, rect) => {
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return { x: clientX - rect.left - SIZE / 2, y: clientY - rect.top - SIZE / 2 };
  }, []);

  const onMouseMove = useCallback((e) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const pos = getPos(e, rect);
    mouseRef.current = { ...pos, hovering: true };
    if (dragRef.current.active) {
      const raw = e.touches ? e.touches[0] : e;
      dragRef.current.vx = (raw.clientX - rect.left - dragRef.current.sx) * 0.005;
      dragRef.current.vy = (raw.clientY - rect.top - dragRef.current.sy) * 0.005;
      dragRef.current.sx = raw.clientX - rect.left;
      dragRef.current.sy = raw.clientY - rect.top;
    }
  }, [getPos]);

  const onMouseDown = useCallback((e) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return;
    const raw = e.touches ? e.touches[0] : e;
    dragRef.current = { active: true, sx: raw.clientX - rect.left, sy: raw.clientY - rect.top, vx: 0, vy: 0 };
  }, []);

  const onMouseUp = useCallback((e) => {
    if (dragRef.current.active) {
      dragRef.current.active = false;
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const raw = e.changedTouches ? e.changedTouches[0] : e;
        const rx = (raw.clientX - rect.left) - SIZE / 2;
        const ry = (raw.clientY - rect.top) - SIZE / 2;
        ripplesRef.current.push({ x: rx, y: ry, radius: 5, maxR: ORB_RADIUS * 1.8, strength: 0.75 });
        clickReactRef.current = 0.5;
      }
    }
  }, []);

  const onMouseLeave = useCallback(() => {
    mouseRef.current = { x: -1000, y: -1000, hovering: false };
    dragRef.current.active = false;
  }, []);

  // ─── Main render loop ───
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = SIZE;
    canvas.height = SIZE;

    if (!particlesRef.current) {
      particlesRef.current = createParticles();
    }
    const particles = particlesRef.current;

    function render(timestamp) {
      // Tab visibility check
      if (document.hidden) {
        animRef.current = requestAnimationFrame(render);
        return;
      }

      // FPS throttle: 30fps idle, 60fps active
      const curState = stateRef.current;
      const preset = STATE_PRESETS[curState] || STATE_PRESETS.idle;
      const targetFPS = (curState === 'idle' && !mouseRef.current.hovering && ripplesRef.current.length === 0) ? 30 : 60;
      const elapsed = timestamp - lastFrameRef.current;
      if (elapsed < 1000 / targetFPS) {
        animRef.current = requestAnimationFrame(render);
        return;
      }
      lastFrameRef.current = timestamp;

      ctx.clearRect(0, 0, SIZE, SIZE);

      // Lerp color
      const cur = colorRef.current.cur;
      const tar = colorRef.current.tar;
      cur.r += (tar.r - cur.r) * 0.04;
      cur.g += (tar.g - cur.g) * 0.04;
      cur.b += (tar.b - cur.b) * 0.04;
      const cr = Math.round(cur.r), cg = Math.round(cur.g), cb = Math.round(cur.b);
      const cx = SIZE / 2, cy = SIZE / 2;

      // Ambient glow
      const ambGlow = ctx.createRadialGradient(cx, cy, 10, cx, cy, ORB_RADIUS * 1.6);
      ambGlow.addColorStop(0, `rgba(${cr},${cg},${cb},0.06)`);
      ambGlow.addColorStop(0.5, `rgba(${cr},${cg},${cb},0.02)`);
      ambGlow.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = ambGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, ORB_RADIUS * 1.6, 0, Math.PI * 2);
      ctx.fill();

      // Pulse
      const speedMul = preset.speed;
      const pSpeed = curState === 'thinking' ? 0.04 : curState === 'speaking' ? 0.03 : curState === 'error' ? 0.06 : 0.02;
      const pIntensity = curState === 'thinking' ? 0.08 : curState === 'speaking' ? 0.06 : curState === 'error' ? 0.07 : 0.05;
      pulseRef.current += pSpeed * speedMul;
      clickReactRef.current *= 0.94;
      const combinedScale = 1.0 + Math.sin(pulseRef.current) * pIntensity + clickReactRef.current;

      // Rotation
      let rotX = 0.002 * speedMul;
      let rotY = 0.005 * speedMul;
      const drag = dragRef.current;
      if (drag.active) {
        rotX = drag.vy;
        rotY = drag.vx;
      } else {
        drag.vx *= 0.95;
        drag.vy *= 0.95;
        rotX += drag.vy;
        rotY += drag.vx;
      }

      // Update ripples
      const ripples = ripplesRef.current;
      for (let i = ripples.length - 1; i >= 0; i--) {
        ripples[i].radius += 5;
        if (ripples[i].radius >= ripples[i].maxR) ripples.splice(i, 1);
      }

      // Draw ripple rings
      for (const rp of ripples) {
        const progress = rp.radius / rp.maxR;
        ctx.strokeStyle = `rgba(${cr},${cg},${cb},${(0.15 * (1 - progress)).toFixed(2)})`;
        ctx.lineWidth = 8 * (1 - progress);
        ctx.beginPath();
        ctx.arc(cx + rp.x, cy + rp.y, rp.radius, 0, Math.PI * 2);
        ctx.stroke();
      }

      // Physics
      const mouse = mouseRef.current;
      const now = performance.now();
      for (const p of particles) {
        p.rotate(rotX, rotY);
        const tx = p.bx * combinedScale, ty = p.by * combinedScale, tz = p.bz * combinedScale;
        p.vx += (tx - p.px) * 0.08;
        p.vy += (ty - p.py) * 0.08;
        p.vz += (tz - p.pz) * 0.08;

        // Mouse repel
        if (mouse.hovering) {
          const zd = FOV / (FOV + p.pz);
          const sx = p.px * zd, sy = p.py * zd;
          const dx = sx - mouse.x, dy = sy - mouse.y;
          const dist = Math.hypot(dx, dy);
          if (dist < 110) {
            const inf = Math.pow(1 - dist / 110, 1.5) * 0.5;
            const ang = Math.atan2(dy, dx);
            p.vx += Math.cos(ang) * inf * 8;
            p.vy += Math.sin(ang) * inf * 8;
            p.vz += (Math.random() - 0.5) * inf * 12;
          }
        }

        // Ripple forces
        for (const rp of ripples) {
          const zd = FOV / (FOV + p.pz);
          const sx = p.px * zd, sy = p.py * zd;
          const dx = sx - rp.x, dy = sy - rp.y;
          const dist = Math.hypot(dx, dy);
          const waveDist = Math.abs(dist - rp.radius);
          if (waveDist < 25) {
            const push = (1 - waveDist / 25) * rp.strength * 4;
            const ang = Math.atan2(dy, dx);
            p.vx += Math.cos(ang) * push;
            p.vy += Math.sin(ang) * push;
            p.vz += (Math.random() - 0.5) * push * 3;
          }
        }

        p.px += p.vx; p.py += p.vy; p.pz += p.vz;
        p.vx *= 0.88; p.vy *= 0.88; p.vz *= 0.88;
      }

      // Sort (cached for idle)
      frameCountRef.current++;
      const sortEvery = (curState === 'idle' && !mouse.hovering) ? 3 : 1;
      if (frameCountRef.current % sortEvery === 0 || !sortCacheRef.current) {
        sortCacheRef.current = particles.slice().sort((a, b) => b.pz - a.pz);
      }

      // Draw particles (additive blend)
      ctx.globalCompositeOperation = 'lighter';
      for (const p of sortCacheRef.current) {
        const zd = FOV / (FOV + p.pz);
        const dx = p.px * zd + cx, dy = p.py * zd + cy;
        if (dx < -10 || dx > SIZE + 10 || dy < -10 || dy > SIZE + 10) continue;

        const twinkle = Math.sin(now * 0.003 + p.twinkle) * 0.15 + 0.85;
        const sz = Math.max(0.4, 1.2 * zd * p.size * twinkle);
        const normZ = (p.pz + ORB_RADIUS) / (2 * ORB_RADIUS);
        const alpha = Math.max(0.08, Math.min(1.0, (1.1 - normZ * 0.7) * twinkle));

        ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha.toFixed(2)})`;
        ctx.beginPath();
        ctx.arc(dx, dy, sz, 0, Math.PI * 2);
        ctx.fill();
      }

      // Holographic effects
      // Scan line
      const scanY = (now * 0.05) % SIZE;
      ctx.globalCompositeOperation = 'source-over';
      const scanGrad = ctx.createLinearGradient(0, scanY - 20, 0, scanY + 20);
      scanGrad.addColorStop(0, 'rgba(0,212,255,0)');
      scanGrad.addColorStop(0.5, `rgba(${cr},${cg},${cb},0.08)`);
      scanGrad.addColorStop(1, 'rgba(0,212,255,0)');
      ctx.fillStyle = scanGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, ORB_RADIUS * 1.1, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalCompositeOperation = 'lighter';

      // Depth rings
      for (let ri = 0; ri < 3; ri++) {
        const ringPhase = now * 0.001 + ri * 2.094;
        const ringR = ORB_RADIUS * (0.5 + ri * 0.25) + Math.sin(ringPhase) * 5;
        const ringA = 0.06 + Math.sin(ringPhase) * 0.03;
        ctx.strokeStyle = `rgba(${cr},${cg},${cb},${ringA.toFixed(3)})`;
        ctx.lineWidth = 0.5;
        ctx.beginPath();
        ctx.ellipse(cx, cy, ringR, ringR * 0.3, now * 0.0003, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.globalCompositeOperation = 'source-over';
      animRef.current = requestAnimationFrame(render);
    }

    animRef.current = requestAnimationFrame(render);

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, []);

  return (
    <div className="orb-container" onClick={onClick}>
      <div className="orb-ring" />
      <div className="orb-ring-2" />
      <div className="orb">
        <canvas
          ref={canvasRef}
          className="orb-canvas"
          onMouseMove={onMouseMove}
          onMouseDown={onMouseDown}
          onMouseUp={onMouseUp}
          onMouseLeave={onMouseLeave}
          onTouchStart={onMouseDown}
          onTouchMove={onMouseMove}
          onTouchEnd={onMouseUp}
        />
      </div>
    </div>
  );
}
