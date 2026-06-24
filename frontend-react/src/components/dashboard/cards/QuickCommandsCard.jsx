/**
 * QuickCommandsCard — Categorized command palette with search.
 */
import { useState, useMemo } from 'react';

const CMD_GROUPS = [
  { title: 'SYSTEM', cmds: [
    { label: 'Lock PC', cmd: 'lock pc' }, { label: 'Shutdown', cmd: 'shutdown' },
    { label: 'Restart', cmd: 'restart' }, { label: 'Sleep', cmd: 'sleep' },
    { label: 'Mute', cmd: 'volume mute' }, { label: 'Brightness+', cmd: 'brightness up' },
    { label: 'Brightness-', cmd: 'brightness down' },
  ]},
  { title: 'APPS', cmds: [
    { label: 'Chrome', cmd: 'open chrome' }, { label: 'VS Code', cmd: 'open vs code' },
    { label: 'Notepad', cmd: 'open notepad' }, { label: 'Files', cmd: 'open file explorer' },
    { label: 'Calculator', cmd: 'open calculator' }, { label: 'Spotify', cmd: 'open spotify' },
    { label: 'YouTube', cmd: 'open youtube' }, { label: 'Terminal', cmd: 'open terminal' },
  ]},
  { title: 'DEV TOOLS', cmds: [
    { label: 'Git Status', cmd: 'git status' }, { label: 'Git Push', cmd: 'git push' },
    { label: 'Git Pull', cmd: 'git pull' }, { label: 'Git Log', cmd: 'git log' },
    { label: 'Processes', cmd: 'top processes' }, { label: 'App Usage', cmd: 'app usage' },
  ]},
  { title: 'AI / MEDIA', cmds: [
    { label: 'Screenshot', cmd: 'screenshot le' }, { label: 'OCR Screen', cmd: 'screen pe kya likha hai' },
    { label: 'Weather', cmd: 'weather kya hai' }, { label: 'Cricket', cmd: 'live cricket score' },
    { label: 'Joke', cmd: 'Tell me a joke' }, { label: 'Briefing', cmd: 'good morning' },
  ]},
];

const QUICK_CMDS = [
  { icon: '🌐', label: 'Open Chrome', cmd: 'open chrome' },
  { icon: '💻', label: 'VS Code', cmd: 'open vs code' },
  { icon: '📷', label: 'Screenshot', cmd: 'screenshot le' },
  { icon: '☀', label: 'Daily Briefing', cmd: 'good morning' },
  { icon: '✉', label: 'Check Email', cmd: 'check email' },
];

export default function QuickCommandsCard({ onAction }) {
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!search) return CMD_GROUPS;
    const q = search.toLowerCase();
    return CMD_GROUPS.map(g => ({
      ...g,
      cmds: g.cmds.filter(c => c.label.toLowerCase().includes(q) || c.cmd.toLowerCase().includes(q)),
    })).filter(g => g.cmds.length > 0);
  }, [search]);

  const run = (cmd) => {
    if (onAction) onAction(cmd);
  };

  return (
    <div className="qcmd-card">
      <div className="qcmd-header" onClick={() => setExpanded(e => !e)}>
        <span>Quick Commands</span>
        <span className={`expand-arrow ${expanded ? 'open' : ''}`}>▶</span>
      </div>
      <div className="qcmd-quick">
        {QUICK_CMDS.map(c => (
          <div key={c.cmd} className="qcmd-item" onClick={() => run(c.cmd)}>
            <span className="qcmd-icon">{c.icon}</span>
            <span className="qcmd-label">{c.label}</span>
          </div>
        ))}
      </div>
      {expanded && (
        <div className="qcmd-palette">
          <input
            className="qcmd-search"
            placeholder="Search commands..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {filtered.map(g => (
            <div key={g.title} className="qcmd-group">
              <div className="qcmd-group-title">{g.title}</div>
              <div className="qcmd-grid">
                {g.cmds.map(c => (
                  <button key={c.cmd} className="qcmd-btn" onClick={() => run(c.cmd)}>
                    {c.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
