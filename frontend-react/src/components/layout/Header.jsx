import { useState, useEffect } from 'react';
import { useSystemStats } from '@/hooks/useSystemStats';
import { Link } from 'react-router-dom';

function useLiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function Header({ onEditDashboard, onSettings, onAIFlow, aiFlowOpen }) {
  const now = useLiveClock();
  const { stats } = useSystemStats(5000);

  const time = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  const date = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const cpu = stats?.cpu_percent ?? '--';
  const ram = stats?.ram_percent ?? '--';
  // System is ONLINE if backend is responding (stats exist)
  const systemUp = !!stats;

  return (
    <div className="top-bar">
      {/* Logo */}
      <Link to="/" className="logo" style={{ textDecoration: 'none' }}>
        M<span>J</span>
      </Link>

      {/* Center widgets */}
      <div className="top-bar-widgets">
        <div className="widget-mini">
          <div className="val time-val">{time}</div>
          <div>{date}</div>
        </div>
        <div className="widget-mini">
          <div className="val" style={{ color: 'var(--accent)' }}>--C</div>
          <div>Weather</div>
        </div>
        <div className="widget-mini">
          <div className="val">{cpu}%</div>
          <div>CPU</div>
        </div>
        <div className="widget-mini">
          <div className="val">{ram}%</div>
          <div>RAM</div>
        </div>
        <div className="widget-mini">
          <div className="val" style={{ color: systemUp ? 'var(--success)' : 'var(--error)' }}>
            {systemUp ? 'ONLINE' : 'OFFLINE'}
          </div>
          <div>SYSTEM</div>
        </div>
      </div>

      {/* Right actions */}
      <div className="top-bar-actions">
        <button className="icon-btn" onClick={onEditDashboard} title="Edit Dashboard">
          {'E'}
        </button>
        <Link to="/dashboard" className="icon-btn" title="System Dashboard">
          {'D'}
        </Link>
        <Link to="/settings" className="icon-btn" title="Voice Settings">
          {'S'}
        </Link>
        <button
          className="icon-btn"
          title="Fullscreen"
          onClick={() => {
            if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
            else document.exitFullscreen?.();
          }}
        >
          {'F'}
        </button>
        {onAIFlow && (
          <button
            className={`icon-btn${aiFlowOpen ? ' active' : ''}`}
            onClick={onAIFlow}
            title="AI Flow Panel"
            style={aiFlowOpen ? { color: '#00d4ff' } : {}}
          >
            {'A'}
          </button>
        )}
        <button className="icon-btn" onClick={onSettings} title="Dashboard Settings" style={{ color: '#00d4ff' }}>
          {'G'}
        </button>
      </div>
    </div>
  );
}
