import { useState } from 'react';

const DEFAULT_PATH = '~/';

export default function FileManagerCard() {
  const [path, setPath] = useState(DEFAULT_PATH);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [command, setCommand] = useState('');
  const [output, setOutput] = useState('');
  const [history, setHistory] = useState([]);

  // File manager works via chat commands in the backend
  // We send commands like "list files in /path" and parse response
  const executeCommand = async (cmd) => {
    setLoading(true);
    setError('');
    setOutput('');
    try {
      const form = new FormData();
      form.append('message', cmd);
      const token = localStorage.getItem('mj_auth_token');
      const headers = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch('/chat', { method: 'POST', body: form, headers });
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ') && line !== 'data: [DONE]') {
              try {
                const d = JSON.parse(line.slice(6));
                if (d.token) fullText += d.token;
              } catch {}
            }
          }
        }
      }

      setOutput(fullText);
      setHistory(prev => [...prev.slice(-9), { cmd, result: fullText.slice(0, 100) }]);
    } catch (e) {
      setError('Command failed');
    }
    setLoading(false);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!command.trim()) return;
    executeCommand(command.trim());
    setCommand('');
  };

  const quickCommands = [
    { label: '📂 List Files', cmd: `list files in ${path}` },
    { label: '📁 Desktop', cmd: 'list files in ~/Desktop' },
    { label: '📁 Documents', cmd: 'list files in ~/Documents' },
    { label: '📁 Downloads', cmd: 'list files in ~/Downloads' },
  ];

  return (
    <div className="fm-card">
      <div className="fm-header">
        <span className="fm-title">📁 FILE MANAGER</span>
      </div>

      {/* Quick commands */}
      <div className="fm-quick">
        {quickCommands.map((qc, i) => (
          <button
            key={i}
            className="fm-quick-btn"
            onClick={() => executeCommand(qc.cmd)}
            disabled={loading}
          >
            {qc.label}
          </button>
        ))}
      </div>

      {/* Command input */}
      <form onSubmit={handleSubmit} className="fm-form">
        <input
          type="text"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          placeholder='Try: "create file test.txt" or "list files in ~/Desktop"'
          className="fm-input"
        />
        <button type="submit" className="fm-go-btn" disabled={loading}>
          {loading ? '⏳' : '▶'}
        </button>
      </form>

      {/* Output */}
      {error && <div className="fm-error">{error}</div>}
      {output && (
        <div className="fm-output">
          <pre className="fm-output-text">{output}</pre>
        </div>
      )}

      {/* History */}
      {history.length > 0 && (
        <div className="fm-history">
          <div className="fm-history-label">Recent</div>
          {history.slice().reverse().slice(0, 4).map((h, i) => (
            <div
              key={i}
              className="fm-history-item"
              onClick={() => executeCommand(h.cmd)}
              title={h.cmd}
            >
              <span className="fm-hist-cmd">{h.cmd.slice(0, 30)}</span>
              <span className="fm-hist-result">{h.result.slice(0, 20)}...</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
