import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSystemStats } from '@/hooks/useSystemStats';

// ─── Stat bar color logic ───
function barClass(val) {
  if (val >= 90) return 'crit';
  if (val >= 70) return 'warn';
  return '';
}
function dotClass(val) {
  if (val >= 90) return 'crit';
  if (val >= 70) return 'warn';
  return '';
}

// ─── HUD Stat Item ───
function HudStat({ icon, label, value, percent, showBar = true }) {
  return (
    <div className="hud-item">
      <div className="hud-hex">
        <span className="hud-hex-icon">{icon}</span>
        <span className={`hud-hex-dot ${dotClass(percent)}`} />
      </div>
      <div className="hud-detail">
        <div className="hud-detail-label">{label}</div>
        <div className="hud-detail-value">{value}</div>
        {showBar && (
          <div className="hud-detail-bar">
            <div
              className={`hud-detail-bar-fill ${barClass(percent)}`}
              style={{ width: `${Math.min(100, percent)}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── HUD Clickable Button ───
function HudButton({ icon, label, subtext, subtextColor, onClick }) {
  return (
    <div className="hud-item clickable" onClick={onClick}>
      <div className="hud-hex">
        <span className="hud-hex-icon">{icon}</span>
      </div>
      <div className="hud-detail">
        <div className="hud-detail-label">{label}</div>
        <div className="hud-detail-value" style={{ fontSize: 10, color: subtextColor || 'var(--text-dim)' }}>
          {subtext}
        </div>
      </div>
    </div>
  );
}

// ─── Mini Calendar ───
function MiniCalendar() {
  const [date, setDate] = useState(new Date());
  const [selected, setSelected] = useState(null);

  const month = date.getMonth();
  const year = date.getFullYear();
  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();

  const days = useMemo(() => {
    const arr = [];
    for (let i = 0; i < firstDay; i++) arr.push(null);
    for (let d = 1; d <= daysInMonth; d++) arr.push(d);
    return arr;
  }, [firstDay, daysInMonth]);

  const monthLabel = date.toLocaleString('en-US', { month: 'long', year: 'numeric' });

  const prev = () => setDate(new Date(year, month - 1, 1));
  const next = () => setDate(new Date(year, month + 1, 1));

  return (
    <div className="sidebar-widget">
      <div className="sidebar-widget-title">{'\u{1F4C5}'} Calendar</div>
      <div className="sb-cal-nav">
        <button onClick={prev}>{'◀'}</button>
        <span className="sb-cal-month">{monthLabel}</span>
        <button onClick={next}>{'▶'}</button>
      </div>
      <div className="sb-cal-grid">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(d => (
          <span key={d} className="sb-cal-head">{d}</span>
        ))}
        {days.map((d, i) => {
          if (d === null) return <span key={`e${i}`} className="sb-cal-day empty" />;
          const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
          const isSel = d === selected;
          return (
            <span
              key={d}
              className={`sb-cal-day${isToday ? ' today' : ''}${isSel ? ' selected' : ''}`}
              onClick={() => setSelected(d)}
            >
              {d}
            </span>
          );
        })}
      </div>
      {selected && (
        <div className="sb-cal-selected-date">
          {new Date(year, month, selected).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
        </div>
      )}
    </div>
  );
}

// ─── Focus Timer ───
function FocusTimer() {
  const MODES = { focus: 25*60, short: 5*60, long: 15*60 };
  const [mode, setMode] = useState('focus');
  const [timeLeft, setTimeLeft] = useState(MODES.focus);
  const [running, setRunning] = useState(false);
  const [sessions, setSessions] = useState(0);

  useEffect(() => {
    if (!running) return;
    if (timeLeft <= 0) {
      setRunning(false);
      if (mode === 'focus') setSessions(s => s + 1);
      return;
    }
    const id = setInterval(() => setTimeLeft(t => t - 1), 1000);
    return () => clearInterval(id);
  }, [running, timeLeft, mode]);

  const switchMode = (m) => { setMode(m); setTimeLeft(MODES[m]); setRunning(false); };
  const reset = () => { setTimeLeft(MODES[mode]); setRunning(false); };

  const total = MODES[mode];
  const progress = ((total - timeLeft) / total) * 251.2;
  const mm = String(Math.floor(timeLeft / 60)).padStart(2, '0');
  const ss = String(timeLeft % 60).padStart(2, '0');

  return (
    <div className="sidebar-widget focus-timer-widget">
      <div className="sidebar-widget-title">{'⏱'} Focus Timer</div>
      <div className={`focus-timer-ring${mode !== 'focus' ? ' break' : ''}`}>
        <svg viewBox="0 0 90 90">
          <circle className="ring-bg" cx="45" cy="45" r="40" />
          <circle className="ring-progress" cx="45" cy="45" r="40" style={{ strokeDashoffset: 251.2 - progress }} />
        </svg>
        <div className="timer-text">{mm}:{ss}</div>
        <div className="timer-label">{mode === 'focus' ? 'FOCUS' : 'BREAK'}</div>
      </div>
      <div className="focus-timer-controls">
        <button onClick={() => setRunning(!running)} className={running ? 'active' : ''}>
          {running ? '⏸ Pause' : '▶ Start'}
        </button>
        <button onClick={reset}>{'↻'} Reset</button>
      </div>
      <div className="focus-timer-mode">
        {Object.keys(MODES).map(m => (
          <button key={m} className={mode === m ? 'active' : ''} onClick={() => switchMode(m)}>
            {m === 'focus' ? '25m' : m === 'short' ? '5m' : '15m'}
          </button>
        ))}
      </div>
      <div className="focus-timer-sessions">Sessions: {sessions}</div>
    </div>
  );
}

// ─── Uptime formatter ───
function formatUptime(seconds) {
  if (!seconds) return '--';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

// ═══════════════════════════════════════════════
// MAIN SIDEBAR EXPORT
// ═══════════════════════════════════════════════
export default function Sidebar({ width, iconsOnly, isResizing, onResizeStart, onOrbSettings, onRoadmap, onSecurity, onHotkeys, onWidgets, onTray, onEventLog }) {
  const { stats } = useSystemStats(3000);

  const cpu = stats?.cpu_percent ?? 0;
  const ram = stats?.ram_percent ?? 0;
  const gpu = stats?.gpu_percent ?? 0;
  const disk = stats?.disk_percent ?? 0;
  const netSpeed = stats?.net_speed ?? '0 KB/s';
  const netPercent = Math.min(100, (stats?.net_bytes_sent ?? 0) / 10000);
  const processCount = stats?.process_count ?? '--';
  const uptime = stats?.uptime_seconds;

  return (
    <>
      <div
        className={`hud-sidebar${iconsOnly ? ' sidebar-icons-only' : ''}${isResizing ? ' resizing' : ''}`}
        style={{ width }}
      >
        <div className="hud-corner-tl" />
        <div className="hud-corner-bl" />

        <HudStat icon={'⚙'} label="CPU" value={`${cpu}%`} percent={cpu} />
        <HudStat icon={'\u{1F4CB}'} label="RAM" value={`${ram}%`} percent={ram} />
        <HudStat icon={'\u{1F3AE}'} label="GPU" value={`${gpu}%`} percent={gpu} />

        <div className="hud-divider" />

        <HudStat icon={'\u{1F4E1}'} label="NETWORK" value={netSpeed} percent={netPercent} />
        <HudStat icon={'\u{1F4BE}'} label="DISK" value={`${disk}%`} percent={disk} />

        <div className="hud-divider" />

        <HudStat icon={'▦'} label="PROCESSES" value={processCount} percent={0} showBar={false} />

        <div className="hud-item">
          <div className="hud-hex">
            <span className="hud-hex-icon">{'⚡'}</span>
            <span className="hud-hex-dot" />
          </div>
          <div className="hud-detail">
            <div className="hud-detail-label">TASK</div>
            <div className="hud-task-text">IDLE</div>
          </div>
        </div>

        <HudButton icon={'⚙'} label="ORB SETTINGS" subtext="Configure" onClick={onOrbSettings} />
        <HudButton icon={'\u{1F680}'} label="ROADMAP" subtext="V1 → V25" subtextColor="#ffd900" onClick={onRoadmap} />
        <HudButton icon={'\u{1F512}'} label="SECURITY" subtext="Logout / Password" onClick={onSecurity} />
        <HudButton icon={'\u{2328}'} label="HOTKEYS" subtext="Shortcuts" onClick={onHotkeys} />
        <HudButton icon={'\u{1F4E6}'} label="WIDGETS" subtext="Dashboard" onClick={onWidgets} />
        <HudButton icon={'\u{1F5D4}'} label="TRAY" subtext="System Tray" onClick={onTray} />
        <HudButton icon={'\u{1F4CB}'} label="EVENT LOG" subtext="System Events" onClick={onEventLog} />

        <div className="hud-divider" />

        {!iconsOnly && <MiniCalendar />}
        {!iconsOnly && <FocusTimer />}

        <div className="hud-item" style={{ marginTop: 'auto' }}>
          <div className="hud-hex">
            <span className="hud-hex-icon">{'⏰'}</span>
          </div>
          <div className="hud-detail">
            <div className="hud-detail-label">UPTIME</div>
            <div className="hud-detail-value" style={{ fontSize: 10 }}>{formatUptime(uptime)}</div>
          </div>
        </div>
      </div>

      <div
        className={`sidebar-resize-handle${isResizing ? ' active resizing' : ''}`}
        style={{ left: width }}
        onMouseDown={onResizeStart}
      />
    </>
  );
}
