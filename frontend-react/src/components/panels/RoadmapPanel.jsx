import { useState, useMemo } from 'react';

const ROADMAP = [
  { phase: 'Phase 1 — Foundation', items: [
    { v:'V1', name:'JARVIS Core', desc:'Chat, Voice, FastAPI, Ollama, Logging, Settings, Auth, React', pct:100, features:'Chat UI ✅ | Voice In ✅ | Voice Out ✅ | FastAPI ✅ | Ollama ✅ | Local LLM ✅ | Logging ✅ | Settings ✅ | Auth ✅ | Login Screen ✅ | Change Password ✅ | React ✅' },
    { v:'V2', name:'Memory Engine', desc:'Memory, profile, search, DB ready, migration, analytics', pct:100, features:'Long-Term Memory ✅ | Chat History ✅ | Fact Extraction ✅ | Vector Embeddings ✅ | Short-Term Memory ✅ | User Profile ✅ | Hybrid Search ✅ | Session Context ✅ | Qdrant Stub ✅ | PostgreSQL Stub ✅ | DB Migration Ready ✅ | Data Export ✅ | Garbage Collection ✅ | Memory Analytics ✅' },
    { v:'V3', name:'Tool Engine', desc:'Calculator, files, weather, search, email, calendar + 21 modules', pct:100, features:'Calculator ✅ | Notes/Todos ✅ | File Manager ✅ | Weather ✅ | Web Search ✅ | Email ✅ | Clipboard ✅ | Calendar ✅ | Finance ✅ | Entertainment ✅ | Privacy ✅ | Smart Home ✅ | Scenes ✅ | Automations ✅' },
    { v:'V4', name:'Agent Framework', desc:'Registry, lifecycle, message bus, events', pct:100, features:'Agent Registry ✅ | Agent Lifecycle ✅ | Message Bus ✅ | Event System ✅ | Shared Memory ✅ | Task Queue ✅' },
    { v:'V5', name:'Constitutional AI', desc:'Safety, validation, hallucination detection', pct:100, features:'Self Critique ✅ | Policy Engine ✅ | Hallucination ✅ | Safety ✅ | Confidence ✅ | Validation ✅' },
  ]},
  { phase: 'Phase 2 — Specialized Agents', items: [
    { v:'V6', name:'Zeus (Master Brain)', desc:'Intent, planning, agent selection', pct:100, features:'Intent Detection ✅ | Agent Selection ✅ | Error Recovery ✅ | Planning ✅ | Task Breakdown ✅ | Workflows ✅' },
    { v:'V7', name:'Hermes (Communication)', desc:'Email, notifications, messaging', pct:100, features:'Gmail ✅ | Notifications ✅ | Outlook ✅ | WhatsApp ✅ | Discord ✅ | Slack ✅ | Telegram ✅ | SMS ✅' },
    { v:'V8', name:'Athena (Knowledge)', desc:'Search, RAG, PDF, research', pct:100, features:'Web Search ✅ | RAG (TF-IDF) ✅ | Deep Research ✅ | PDF Reader ✅ | Knowledge Graph ✅ | Citations ✅' },
    { v:'V9', name:'Hephaestus (Developer)', desc:'Coding, git, debugging, testing, deploy, CI/CD', pct:100, features:'Code Execution ✅ | Git Read ✅ | Git Write ✅ | File Analysis ✅ | Code Gen ✅ | Debug Engine ✅ | Error Patterns ✅ | Testing Framework ✅ | Deploy Tools ✅ | Docker Info ✅ | CI/CD Pipelines ✅ | GitHub Actions ✅ | GitLab CI ✅ | Lint Configs ✅ | Pre-Commit ✅' },
    { v:'V10', name:'Apollo (Creative)', desc:'Image gen, writing, video pipeline, render queue, asset manager, design tokens', pct:100, features:'Image Gen (Pollinations) ✅ | 14 Art Styles ✅ | Creative Writing ✅ | Video Gen ✅ | UI Mockups ✅ | Logo Design ✅ | Presentations ✅ | Creative Log ✅ | Full Video Pipeline ✅ | Scene Generator ✅ | Presentation Gen V2 ✅ | Theme Presets ✅ | Design Tokens ✅ | Render Queue ✅ | Asset Manager ✅ | Creative Stats ✅' },
    { v:'V11', name:'Ares (Execution)', desc:'Desktop, keyboard, apps, browser, mouse', pct:100, features:'Desktop Control ✅ | Keyboard ✅ | Windows API ✅ | App Mgmt ✅ | Browser ✅ | Mouse ✅' },
    { v:'V12', name:'Argus (Vision)', desc:'OCR, camera, object detection, screen AI', pct:100, features:'OCR ✅ | Screenshot ✅ | Camera ✅ | Object Detection ✅ | Screen AI ✅' },
    { v:'V13', name:'Mnemosyne (Memory Agent)', desc:'Episodic, semantic, preferences, decay, indexing, consolidation', pct:100, features:'User Preferences ✅ | Knowledge Base ✅ | Semantic Search ✅ | User Profile ✅ | Short-Term Context ✅ | Episodic Memory ✅ | Memory Compression ✅ | Timeline ✅ | Importance Scoring ✅ | Memory Decay ✅ | Knowledge Indexer ✅ | Auto-Categorize ✅ | Consolidation ✅ | Duplicate Detection ✅ | Contradiction Finder ✅' },
    { v:'V14', name:'Chronos (Time Agent)', desc:'Reminders, calendar, planning, recurring, timezone, habits, conflicts', pct:100, features:'Reminders ✅ | Productivity Tracking ✅ | Calendar Events ✅ | Daily Planning ✅ | Time Blocks ✅ | Streaks ✅ | Recurring Events ✅ | Timezone Convert ✅ | Google Calendar Stub ✅ | Conflict Detection ✅ | Smart Scheduling ✅ | Habit Tracker ✅ | Day Availability ✅' },
    { v:'V15', name:'Sentinel (Security)', desc:'Permissions, encryption, secrets, audit, threats', pct:100, features:'Hashing ✅ | Tool Sandbox ✅ | Permissions ✅ | Secrets Vault ✅ | Audit Logs ✅ | Threats ✅' },
  ]},
  { phase: 'Phase 3 — Intelligence Layer', items: [
    { v:'V16', name:'Reflection Engine', desc:'Mistake detection, learning reports', pct:100, features:'Mistake Detection ✅ | Learning Reports ✅ | Suggestions ✅ | Daily Reflection ✅ | Agent Score ✅' },
    { v:'V17', name:'Learning Engine', desc:'Habits, preferences, prompt tuning', pct:100, features:'Preference Learning ✅ | Habit Learning ✅ | Prompt Optimization ✅ | Workflow Learning ✅' },
    { v:'V18', name:'Dashboard 2.0 (Orb UI)', desc:'Orb, HUD, stats, alerts, AI flow', pct:100, features:'Orb ✅ | Live Stats ✅ | CPU/RAM/VRAM ✅ | Notifications ✅ | Voice Viz ✅ | Memory Graph ✅ | Timeline ✅ | Agent Network ✅' },
    { v:'V19', name:'Workflow Engine', desc:'Automation, parallel, triggers, retry, live orchestration', pct:100, features:'Workflow CRUD ✅ | Daily Briefing ✅ | Task Planning ✅ | Sequential Execution ✅ | Morning Routine ✅ | News Digest ✅ | Email Auto-Sort ✅ | Scheduled Triggers ✅ | Templates ✅ | Event Triggers ✅ | Parallel Workflows ✅ | Condition Triggers ✅ | Trigger Stats ✅ | Error Recovery ✅ | Auto-Retry ✅ | Live Status ✅ | Dashboard Data ✅' },
    { v:'V20', name:'Multi-Agent Collaboration', desc:'Pipelines, parallel, orchestration, load balancing, capabilities', pct:100, features:'Shared Context ✅ | Sequential Chaining ✅ | Message Bus ✅ | Pipeline Orchestrator ✅ | Parallel Execution ✅ | Peer-to-Peer Mail ✅ | Agent Groups ✅ | Dependency Resolution ✅ | Real-Time Status ✅ | Resource Locks ✅ | Conflict Resolution ✅ | Coordination Protocol ✅ | Load Balancing ✅ | Health Checks ✅ | Auto-Redistribute ✅ | Live Orchestration ✅ | Capability Registry ✅ | Smart Task Assignment ✅' },
  ]},
  { phase: 'Phase 4 — AI Operating System', items: [
    { v:'V21', name:'Plugin Marketplace', desc:'Store, install, ratings, sandbox, versioning, registry, auto-update, webhooks', pct:100, features:'Plugin Loader ✅ | Hot Reload ✅ | Plugin Discovery ✅ | Store Catalog ✅ | Browse & Search ✅ | Install/Uninstall ✅ | Ratings & Reviews ✅ | Sandbox Check ✅ | Categories ✅ | Store Stats ✅ | Versioning ✅ | Update Check ✅ | Plugin Update ✅ | Dependency Resolution ✅ | Featured Plugins ✅ | Changelog ✅ | Remote Registry ✅ | Auto-Update ✅ | Plugin Health Monitor ✅ | Publish ✅ | Live Registry ✅ | Webhook Events ✅ | Install/Uninstall Hooks ✅ | Registry Sync ✅' },
    { v:'V22', name:'Hybrid AI', desc:'5 providers, auto routing, benchmarks, A/B testing', pct:100, features:'Ollama Local ✅ | Groq Cloud ✅ | OpenAI GPT-4o ✅ | Anthropic Claude ✅ | Google Gemini ✅ | Provider Switching ✅ | Multi-Model Reasoning ✅ | Smart Auto-Routing ✅ | Cost Tracking ✅ | Budget Limits ✅ | Cost-Aware Routing ✅ | Fallback Chains ✅ | Model Benchmarking ✅ | A/B Testing ✅' },
    { v:'V23', name:'AI Operating System', desc:'Multi-user, permissions, API gateway, services, apps, sync, backup, monitor, VFS, sandbox, event log', pct:100, features:'Health Monitor ✅ | User Management ✅ | Role-Based Permissions ✅ | Session Management ✅ | API Gateway ✅ | API Key Management ✅ | Rate Limiting ✅ | Background Task Runner ✅ | Permission Engine ✅ | OS Status ✅ | System Services ✅ | Service Auto-Start ✅ | App Registry ✅ | App Launch ✅ | Cross-Device Sync Stub ✅ | Device Registration ✅ | Cloud Sync Engine ✅ | System Backup ✅ | Backup Restore ✅ | Auto-Backup Config ✅ | Notification Rules ✅ | Rule Evaluation ✅ | System Monitor ✅ | Metric Recording ✅ | Monitor Summary ✅ | Virtual File System ✅ | Mount Points ✅ | Quota Management ✅ | Process Isolation ✅ | Sandbox Levels ✅ | Process Kill/OOM ✅ | System Event Log ✅ | Event Filtering ✅ | Retention Policy ✅' },
  ]},
  { phase: 'Phase 5 — Autonomous Intelligence', items: [
    { v:'V24', name:'Self-Improving JARVIS', desc:'Auto-fix, performance, ML tuning, adaptive routing, quality, learning', pct:100, features:'Error Auto-Fix (LLM) ✅ | Error Tracker ✅ | Health Monitor ✅ | Alert System ✅ | Self-Heal Middleware ✅ | Performance Tracker ✅ | Slow Query Detection ✅ | Prompt Auto-Improve ✅ | Memory Optimizer ✅ | Data Compaction ✅ | Auto-Tuner ✅ | Optimization Suggestions ✅ | Quality Scorer ✅ | Auto-Retry Engine ✅ | Learning Feedback Loop ✅ | Weak Area Detection ✅ | Quality Trends ✅ | ML-Based Tuning ✅ | Adaptive Routing ✅ | Confidence Calibration ✅' },
    { v:'V25', name:'JARVIS OS Ultimate', desc:'Unified controller, PWA, smart home, themes, command palette, launcher, voice hub', pct:72, features:'Unified Controller ✅ | System Overview ✅ | Mode Switching ✅ | System Search ✅ | Quick Actions ✅ | PWA Manifest ✅ | Mobile Config ✅ | Smart Home Hub ✅ | Device Manager ✅ | Scenes ✅ | Rooms ✅ | Notification Center ✅ | Unread Tracking ✅ | Service Worker Stub ✅ | Offline Cache Config ✅ | Command Palette ✅ | Command Search ✅ | Custom Commands ✅ | Theme Engine ✅ | 4 Built-In Themes ✅ | Custom Themes ✅ | Theme Export ✅ | App Launcher ✅ | Pinned Apps ✅ | Favorites ✅ | Voice Hub ✅ | Wake Word Config ✅ | Voice Selection ✅ | Cross-Device Live ⚠️ | Full Mobile App ⚠️' },
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
        <span className={`rm-expand ${open ? 'open' : ''}`}>{'▶'}</span>
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
          <span className="rm-title">{'🚀'} MJ ROADMAP</span>
          <button className="panel-close" onClick={onClose}>x</button>
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
