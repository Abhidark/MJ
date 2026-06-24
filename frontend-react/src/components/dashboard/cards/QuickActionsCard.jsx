/**
 * QuickActionsCard — shortcut buttons that send commands to chat
 */

const QUICK_ACTIONS = [
  { cmd: 'open chrome',       label: 'Chrome',     icon: '🌐' },
  { cmd: 'open notepad',      label: 'Notepad',    icon: '📝' },
  { cmd: 'open calculator',   label: 'Calculator', icon: '🔢' },
  { cmd: 'open file explorer',label: 'Files',      icon: '📁' },
  { cmd: 'open vs code',      label: 'VS Code',    icon: '💻' },
  { cmd: 'screenshot le',     label: 'Screenshot', icon: '📸' },
  { cmd: 'volume up',         label: 'Vol +',      icon: '🔊' },
  { cmd: 'volume down',       label: 'Vol -',      icon: '🔉' },
  { cmd: 'open youtube',      label: 'YouTube',    icon: '▶️' },
  { cmd: 'Tell me a joke',    label: 'Joke',       icon: '😄' },
  { cmd: 'good morning',      label: 'Briefing',   icon: '☀️' },
  { cmd: 'list files in downloads', label: 'Downloads', icon: '📥' },
  { cmd: 'clipboard history', label: 'Clipboard',  icon: '📋' },
  { cmd: 'app usage',         label: 'Screen Time',icon: '📊' },
  { cmd: 'check email',       label: 'Email',      icon: '📧' },
  { cmd: 'generate image of a sunset over mountains', label: 'AI Image', icon: '🎨' },
];

export default function QuickActionsCard({ onAction }) {
  return (
    <div className="quick-actions">
      {QUICK_ACTIONS.map((a) => (
        <button
          key={a.cmd}
          className="qa-btn"
          onClick={() => onAction?.(a.cmd)}
          title={a.cmd}
        >
          <span className="qa-icon">{a.icon}</span>
          <span>{a.label}</span>
        </button>
      ))}
    </div>
  );
}
