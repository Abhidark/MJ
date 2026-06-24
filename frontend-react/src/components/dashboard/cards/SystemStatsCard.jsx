import { useSystemStats } from '@/hooks/useSystemStats';

/**
 * SystemStatsCard — circular SVG gauges for CPU/RAM/Disk/GPU + detail rows
 */

function GaugeRing({ value = 0, label, color = '#00d4ff' }) {
  const r = 35;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;

  // Color by threshold
  const ringColor = value >= 90 ? '#ff3b30' : value >= 75 ? '#ffd900' : color;

  return (
    <div className="sysmon-gauge">
      <svg viewBox="0 0 80 80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="rgba(0,180,255,0.1)" strokeWidth="4" />
        <circle
          cx="40" cy="40" r={r} fill="none"
          stroke={ringColor} strokeWidth="4"
          strokeDasharray={circ} strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 40 40)"
          style={{ transition: 'stroke-dashoffset 0.6s ease, stroke 0.4s' }}
        />
      </svg>
      <div className="sysmon-val">{Math.round(value)}%</div>
      <div className="sysmon-label">{label}</div>
    </div>
  );
}

function DetailRow({ label, value, unit = '' }) {
  return (
    <div className="sysmon-detail-row">
      <span className="sysmon-detail-label">{label}</span>
      <span className="sysmon-detail-value">{value}{unit}</span>
    </div>
  );
}

export default function SystemStatsCard() {
  const { stats, loading } = useSystemStats(3000);

  if (loading || !stats) {
    return <div className="sysmon-loading">Connecting to system...</div>;
  }

  return (
    <div className="sysmon-content">
      {/* Gauge rings */}
      <div className="sysmon-gauges">
        <GaugeRing value={stats.cpu} label="CPU" color="#00d4ff" />
        <GaugeRing value={stats.ram_percent} label="RAM" color="#00e676" />
        <GaugeRing value={stats.disk_percent} label="DISK" color="#ffd700" />
        <GaugeRing value={stats.gpu_util || 0} label="GPU" color="#b92eff" />
      </div>

      {/* Detail rows */}
      <div className="sysmon-details">
        <DetailRow label="RAM" value={`${stats.ram_used?.toFixed(1)} / ${stats.ram_total} GB`} />
        {stats.gpu_name && (
          <DetailRow label="GPU" value={stats.gpu_name} />
        )}
        {stats.gpu_temp != null && (
          <DetailRow label="GPU Temp" value={stats.gpu_temp} unit="°C" />
        )}
        <DetailRow label="Network" value={`↓${stats.net_down_kbs?.toFixed(0) || 0} ↑${stats.net_up_kbs?.toFixed(0) || 0}`} unit=" KB/s" />
        <DetailRow label="Processes" value={stats.process_count || '-'} />
        {stats.uptime && <DetailRow label="Uptime" value={stats.uptime} />}
        {stats.battery != null && (
          <DetailRow label="Battery" value={`${stats.battery}%${stats.charging ? ' ⚡' : ''}`} />
        )}
      </div>
    </div>
  );
}
