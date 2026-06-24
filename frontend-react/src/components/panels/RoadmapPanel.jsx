import { useState, useMemo } from 'react';

const ROADMAP = [
  { phase: 'Phase 1 — Foundation', items: [
    { v:'V1', name:'JARVIS Core', desc:'Chat, Voice, FastAPI, Ollama, Logging, Settings, Auth, React', pct:100, features:'Chat UI ✅ | Voice In ✅ | Voice Out ✅ | FastAPI ✅ | Ollama ✅ | Local LLM ✅ | Logging ✅ | Settings ✅ | Auth ✅ | Login Screen ✅ | Change Password ✅ | React ✅' },
    { v:'V2', name:'Memory Engine', desc:'Short/long-term memory, profile, search', pct:45, features:'Long-Term Memory ✅ | Chat History ✅ | Short-Term ⚠️ | User Profile ⚠️ | Memory Search ⚠️ | Timeline ❌ | Qdrant ❌ | PostgreSQL ❌' },
    { v:'V3', name:'Tool Engine', desc:'Calculator, files, weather, search, email, calendar', pct:100, features:'Calculator ✅ | Notes/Todos ✅ | File Manager ✅ | Weather ✅ | Web Search ✅ | Email ✅ | Clipboard ✅ | Calendar ✅' },
    { v:'V4', name:'Agent Framework', desc:'Registry, lifecycle, message bus, events', pct:100, features:'Agent Registry ✅ | Agent Lifecycle ✅ | Message Bus ✅ | Event System ✅ | Shared Memory ✅ | Task Queue ✅' },
    { v:'V5', name:'Constitutional AI', desc:'Safety, validation, hallucination detection', pct:10, features:'Self Critique ❌ | Policy Engine ❌ | Hallucination ❌ | Safety ⚠️ | Confidence ❌ | Validation ❌' },
  ]},
  { phase: 'Phase 2 — Specialized Agents', items: [
    { v:'V6', name:'Zeus (Master Brain)', desc:'Intent, planning, agent selection', pct:60, features:'Intent Detection ✅ | Agent Selection ✅ | Error Recovery ⚠️ | Planning ❌ | Task Breakdown ❌ | Workflows ❌' },
    { v:'V7', name:'Hermes (Communication)', desc:'Email, notifications, messaging', pct:15, features:'Gmail ✅ | Notifications ✅ | Outlook ⚠️ | WhatsApp ❌ | Discord ❌ | Slack ❌ | Telegram ❌ | SMS ❌' },
    { v:'V8', name:'Athena (Knowledge)', desc:'Search, RAG, PDF, research', pct:50, features:'Web Search ✅ | RAG (TF-IDF) ✅ | Deep Research ⚠️ | PDF Reader ⚠️ | Knowledge Graph ❌ | Citations ❌' },
    { v:'V9', name:'Hephaestus (Developer)', desc:'Coding, git, debugging, testing', pct:45, features:'Code Context ✅ | Git (9 cmds) ✅ | Debugging ⚠️ | APIs ⚠️ | Docs ❌ | Testing ❌ | Deploy ❌' },
    { v:'V10', name:'Apollo (Creative)', desc:'Image gen, writing, video, design', pct:30, features:'Image Gen ✅ | Creative Writing ✅ | Video ❌ | UI Design ❌ | Logo ❌ | Presentation ❌' },
    { v:'V11', name:'Ares (Execution)', desc:'Desktop, keyboard, apps, browser, mouse', pct:100, features:'Desktop Control ✅ | Keyboard ✅ | Windows API ✅ | App Mgmt ✅ | Browser ✅ | Mouse ✅' },
    { v:'V12', name:'Argus (Vision)', desc:'OCR, camera, object detection', pct:25, features:'OCR ✅ | Screenshot ⚠️ | Camera ❌ | Object Detection ❌ | Screen AI ❌' },
    { v:'V13', name:'Mnemosyne (Memory Agent)', desc:'Episodic, semantic, preferences', pct:40, features:'User Preferences ✅ | Knowledge Base ⚠️ | Semantic ⚠️ | Episodic ❌ | Compression ❌' },
    { v:'V14', name:'Chronos (Time Agent)', desc:'Reminders, scheduling, tracking', pct:40, features:'Reminders ✅ | Productivity Tracking ✅ | Scheduling ⚠️ | Calendar ❌ | Daily Planning ❌' },
    { v:'V15', name:'Sentinel (Security)', desc:'Permissions, encryption, audit', pct:20, features:'Hashing ⚠️ | Tool Sandbox ⚠️ | Permissions ❌ | Secrets ❌ | Audit Logs ❌ | Threats ❌' },
  ]},
  { phase: 'Phase 3 — Intelligence Layer', items: [
    { v:'V16', name:'Reflection Engine', desc:'Mistake detection, learning reports', pct:30, features:'Mistake Detection ✅ | Learning Reports ⚠️ | Suggestions ⚠️ | Daily Reflection ❌ | Agent Score ❌' },
    { v:'V17', name:'Learning Engine', desc:'Habits, preferences, prompt tuning', pct:35, features:'Preference Learning ✅ | Habit Learning ⚠️ | Prompt Optimization ❌ | Workflow Learning ❌' },
    { v:'V18', name:'Dashboard 2.0 (Orb UI)', desc:'Orb, HUD, stats, alerts, AI flow', pct:100, features:'Orb ✅ | Live Stats ✅ | CPU/RAM/VRAM ✅ | Notifications ✅ | Voice Viz ✅ | Memory Graph ✅ | Timeline ✅ | Agent Network ✅' },
    { v:'V19', name:'Workflow Engine', desc:'Morning routine, automation chains', pct:5, features:'Daily Briefing ⚠️ | Morning Routine ❌ | News ❌ | Email Auto ❌ | Calendar ❌ | Auto Tasks ❌' },
    { v:'V20', name:'Multi-Agent Collaboration', desc:'Agent pipeline, parallel execution', pct:5, features:'Shared Context ⚠️ | Agent Pipeline ❌ | Parallel Execution ❌' },
  ]},
  { phase: 'Phase 4 — AI Operating System', items: [
    { v:'V21', name:'Plugin Marketplace', desc:'Plugin store, third-party integrations', pct:15, features:'Plugin Loader ⚠️ | Plugin Store ❌ | GitHub ❌ | Docker ❌ | Notion ❌ | Google Drive ❌' },
    { v:'V22', name:'Hybrid AI', desc:'Local + cloud models, auto routing', pct:40, features:'Local Models ✅ | Auto Routing ✅ | Cloud (OpenAI) ❌ | Cloud (Anthropic) ❌ | Cloud (Gemini) ❌' },
    { v:'V23', name:'AI Operating System', desc:'Multi-user, permissions, sync', pct:5, features:'Background Services ⚠️ | Multi User ❌ | Permissions ❌ | API Gateway ❌ | Cross Device ❌' },
  ]},
  { phase: 'Phase 5 — Autonomous Intelligence', items: [
    { v:'V24', name:'Self-Improving JARVIS', desc:'Auto-fix, performance, optimization', pct:15, features:'Error Auto-Fix ✅ | Resource Monitor ✅ | Performance ⚠️ | Prompt Improve ❌ | Memory Optimize ❌' },
    { v:'V25', name:'JARVIS OS Ultimate', desc:'Everything unified as one AI OS', pct:0, features:'Full Integration ❌ | Mobile ❌ | Smart Home ⚠️ | Complete Stack ⚠️' },
  ]},
];

function statusIcon(pct) {
  if (pct >= 70) return '✓';
  if (pct > 0) return '◐';
  return '○';
}
function statusClass(pct) {
  if (pct >= 70) return 'done';
  if (pct > 0) return 'partial';
  return 'soon';
}

function FeatureList({ features }) {
  const items = features.split(' | ');
  return (
    <div className="rm-features">
      {items.map((f, i) => {
        let cls = 'rm-feat';
        if (f.includes('✅')) cls += ' done';
        else if (f.includes('⚠️')) cls += ' wip';
        else cls += ' todo';
        return <span key={i} className={cls}>{f}</span>;
      })}
    </div>
  );
}

function RoadmapItem({ item }) {
  const [open, setOpen] = useState(false);
  const st = statusClass(item.pct);

  return (
    <div className={`rm-item ${st}`} onClick={() => setOpen(o => !o)}>
      <div className="rm-item-header">
        <span className={`rm-icon ${st}`}>{statusIcon(item.pct)}</span>
        <span className="rm-version">{item.v}</span>
        <span className="rm-name">{item.name}</span>
        <span className="rm-pct">{item.pct}%</span>
        <span className={`rm-expand ${open ? 'open' : ''}`}>▶</span>
      </div>
      <div className="rm-bar-wrap">
        <div className={`rm-bar-fill ${st}`} style={{ width: `${item.pct}%` }} />
      </div>
      <div className="rm-desc">{item.desc}</div>
      {open && <FeatureList features={item.features} />}
    </div>
  );
}

export default function RoadmapPanel({ onClose }) {
  const [search, setSearch] = useState('');

  const { overall, filtered } = useMemo(() => {
    let totalPct = 0, count = 0;
    const q = search.toLowerCase();

    const filtered = ROADMAP.map(phase => {
      const items = phase.items.filter(it => {
        const match = !q || it.name.toLowerCase().includes(q) ||
          it.v.toLowerCase().includes(q) || it.desc.toLowerCase().includes(q);
        if (match) { totalPct += it.pct; count++; }
        return match;
      });
      return { ...phase, items };
    }).filter(p => p.items.length > 0);

    return { overall: count > 0 ? Math.round(totalPct / count) : 0, filtered };
  }, [search]);

  return (
    <div className="panel-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="rm-panel">
        <div className="rm-header">
          <span className="rm-title">🚀 MJ ROADMAP</span>
          <button className="panel-close" onClick={onClose}>✕</button>
        </div>

        <div className="rm-overall">
          <div className="rm-overall-label">OVERALL PROGRESS</div>
          <div className="rm-overall-bar">
            <div className="rm-overall-fill" style={{ width: `${overall}%` }} />
          </div>
          <div className="rm-overall-pct">{overall}%</div>
        </div>

        <input
          className="rm-search"
          placeholder="Search versions, features..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />

        <div className="rm-body">
          {filtered.map(phase => (
            <div key={phase.phase} className="rm-phase">
              <div className="rm-phase-title">{phase.phase}</div>
              {phase.items.map(it => <RoadmapItem key={it.v} item={it} />)}
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="rm-empty">No matching versions found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
