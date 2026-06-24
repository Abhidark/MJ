/**
 * LiveIntelCard — Real-time intelligence feed with CPU, RAM, Network, GPU.
 */
import { useState, useEffect } from 'react';

export default function LiveIntelCard() {
  const [expanded, setExpanded] = useState(false);
  const [stats, setStats] = useState(null);
  const [procs, setProcs] = useState([]);

  useEffect(() => {
    const load = () => {
      fetch('/system-stats').then(r => r.json()).then(d => setStats(d)).catch(() => {});
    };
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (expanded) {
      fetch('/top-processes').then(r => r.json()).then(d => setProcs(d.processes || [])).catch(() => {});
    }
  }, [expanded]);

  const cpu = stats?.cpu_percent ?? '--';
  const ram = stats?.ram_percent ?? '--';
  const gpu = stats?.gpu_percent ?? 'N/A';
  const gpuTemp = stats?.gpu_temp ?? '--';
  const netSpeed = stats?.network_speed ?? '--';

  const cpuSub = cpu > 80 ? 'High load detected' : cpu > 50 ? 'Moderate load' : 'System load nominal';
  const ramSub = ram > 80 ? 'High memory usage' : 'Memory allocation stable';

  return (
    <div className="liveintel-card">
      <div className="liveintel-header" onClick={() => setExpanded(e => !e)}>
        <span>Live Intelligence</span>
        <span className="live-dot-indicator" />
        <span className={`expand-arrow ${expanded ? 'open' : ''}`}>▶</span>
      </div>
      <div className="liveintel-feed">
        <div className="lf-item">
          <span className="lf-icon">📈</span>
          <div className="lf-info">
            <div className="lf-text">CPU usage at <span className="lf-val">{cpu}%</span></div>
            <div className="lf-sub">{cpuSub}</div>
          </div>
        </div>
        <div className="lf-item">
          <span className="lf-icon">💾</span>
          <div className="lf-info">
            <div className="lf-text">RAM: <span className="lf-val">{ram}%</span></div>
            <div className="lf-sub">{ramSub}</div>
          </div>
        </div>
        <div className="lf-item">
          <span className="lf-icon">🌍</span>
          <div className="lf-info">
            <div className="lf-text">Network: <span className="lf-val">Active</span></div>
            <div className="lf-sub">{netSpeed}</div>
          </div>
        </div>
        <div className="lf-item">
          <span className="lf-icon">🔧</span>
          <div className="lf-info">
            <div className="lf-text">GPU: <span className="lf-val">{gpu}%</span></div>
            <div className="lf-sub">{gpuTemp}°C</div>
          </div>
        </div>
      </div>
      {expanded && (
        <div className="liveintel-detail">
          <div className="lid-section">CPU Details</div>
          <div className="lid-row"><span>Usage</span><span>{cpu}%</span></div>
          <div className="lid-row"><span>Cores</span><span>{stats?.cpu_cores || '--'}</span></div>
          <div className="lid-section">Memory Details</div>
          <div className="lid-row"><span>Used</span><span>{stats?.ram_used_gb ?? '--'} GB</span></div>
          <div className="lid-row"><span>Total</span><span>{stats?.ram_total_gb ?? '--'} GB</span></div>
          <div className="lid-section">GPU Details</div>
          <div className="lid-row"><span>Name</span><span>{stats?.gpu_name || 'N/A'}</span></div>
          <div className="lid-row"><span>Temp</span><span>{gpuTemp}°C</span></div>
          <div className="lid-row"><span>VRAM</span><span>{stats?.gpu_vram || 'N/A'}</span></div>
          <div className="lid-section">Network</div>
          <div className="lid-row"><span>Speed</span><span>{netSpeed}</span></div>
          {procs.length > 0 && (
            <>
              <div className="lid-section">Top Processes</div>
              {procs.slice(0, 5).map((p, i) => (
                <div key={i} className="lid-proc">
                  <span>{p.name}</span>
                  <span>CPU: {p.cpu}% | RAM: {p.memory}MB</span>
                </div>
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}
