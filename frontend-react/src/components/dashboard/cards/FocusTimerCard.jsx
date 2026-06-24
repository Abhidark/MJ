import { useState, useEffect, useRef, useCallback } from 'react';

const WORK_MIN = 25;
const BREAK_MIN = 5;

export default function FocusTimerCard() {
  const [mode, setMode] = useState('work'); // work | break
  const [seconds, setSeconds] = useState(WORK_MIN * 60);
  const [running, setRunning] = useState(false);
  const [sessions, setSessions] = useState(() => {
    return parseInt(localStorage.getItem('mj_focus_sessions') || '0', 10);
  });
  const intervalRef = useRef(null);

  // Persist sessions
  useEffect(() => {
    localStorage.setItem('mj_focus_sessions', String(sessions));
  }, [sessions]);

  const tick = useCallback(() => {
    setSeconds(prev => {
      if (prev <= 1) {
        // Timer done — switch mode
        setRunning(false);
        if (mode === 'work') {
          setSessions(s => s + 1);
          setMode('break');
          // Play notification sound
          try { new Audio('data:audio/wav;base64,UklGRl9vT19teleWQVZFZm10').play(); } catch {}
          if (Notification.permission === 'granted') {
            new Notification('🎉 Focus session complete!', { body: 'Time for a break.' });
          }
          return BREAK_MIN * 60;
        } else {
          setMode('work');
          return WORK_MIN * 60;
        }
      }
      return prev - 1;
    });
  }, [mode]);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(tick, 1000);
    }
    return () => clearInterval(intervalRef.current);
  }, [running, tick]);

  const toggle = () => {
    if (!running && Notification.permission === 'default') {
      Notification.requestPermission();
    }
    setRunning(!running);
  };

  const reset = () => {
    setRunning(false);
    setMode('work');
    setSeconds(WORK_MIN * 60);
  };

  const skip = () => {
    setRunning(false);
    if (mode === 'work') {
      setMode('break');
      setSeconds(BREAK_MIN * 60);
    } else {
      setMode('work');
      setSeconds(WORK_MIN * 60);
    }
  };

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const total = mode === 'work' ? WORK_MIN * 60 : BREAK_MIN * 60;
  const progress = ((total - seconds) / total) * 100;

  return (
    <div className="focus-card">
      <div className="focus-header">
        <span className="focus-title">⏱️ FOCUS TIMER</span>
        <span className={`focus-mode ${mode}`}>
          {mode === 'work' ? '🔴 WORK' : '🟢 BREAK'}
        </span>
      </div>

      {/* Timer ring */}
      <div className="focus-ring-wrap">
        <svg viewBox="0 0 120 120" className="focus-ring">
          <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="6" />
          <circle
            cx="60" cy="60" r="52"
            fill="none"
            stroke={mode === 'work' ? 'var(--cyan, #00d4ff)' : 'var(--green, #00e676)'}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 52}`}
            strokeDashoffset={`${2 * Math.PI * 52 * (1 - progress / 100)}`}
            transform="rotate(-90 60 60)"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
        <div className="focus-time">
          {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
        </div>
      </div>

      {/* Controls */}
      <div className="focus-controls">
        <button className="focus-btn" onClick={reset} title="Reset">↺</button>
        <button className={`focus-btn main ${running ? 'pause' : 'play'}`} onClick={toggle}>
          {running ? '⏸' : '▶'}
        </button>
        <button className="focus-btn" onClick={skip} title="Skip">⏭</button>
      </div>

      {/* Sessions count */}
      <div className="focus-sessions">
        Sessions today: <strong>{sessions}</strong>
        {sessions > 0 && (
          <button className="focus-reset-sessions" onClick={() => setSessions(0)}>Reset</button>
        )}
      </div>
    </div>
  );
}
