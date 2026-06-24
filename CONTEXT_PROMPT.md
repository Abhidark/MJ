# MJ-Assistant Project Context — Paste This in New Chat

## PROJECT OVERVIEW
MJ-Assistant (codename "Zeus") — AI desktop assistant with FastAPI backend + React frontend.
- **Backend**: FastAPI, dual provider (Ollama local + Groq cloud), Python modules for voice, vision, memory, security, research, etc.
- **Frontend**: React (Vite 8 + Rolldown) in `frontend-react/` — parallel to old monolithic `frontend/index.html`
- **Repo**: `F:\MJ\MJ-Assistant\` on office laptop

## RULES (MUST FOLLOW EVERY TIME)
1. Build in `frontend-react/` (React JSX only, not old `frontend/`)
2. Do NOT damage existing code or functionality
3. Before updating any file, preserve existing code
4. Give git push commands at end (NO `cd` command — only `git add .` / `git commit -m "..."` / `git push`)
5. Do NOT use my laptop (no computer-use/desktop control MCP tools)
6. Laptop is for coding only — no Ollama/GPU tasks
7. After every task, verify build passes with `npm run build`
8. Do not damage existing functionality — backend, APIs, voice, chat, LLM integration must stay untouched

## WORKFLOW
- **Office Laptop**: Coding only, no Ollama/GPU. Build/push from here. Has Groq API key in `.env`.
- **Personal PC** (RTX 3060): Full backend, Ollama, Voice, GPU tasks. Pull and run.
- **Known issue**: Sandbox mount sync lag — files written via Edit tool may appear truncated in Linux bash sandbox. Windows Read tool always shows correct file. `npm run build` runs on Windows where files are complete.

## ARCHITECTURE

### Backend (`backend/`)
- `main.py` — FastAPI server, all API routes
- `zeus/brain.py` — Zeus AI brain with error recovery, task planning, workflows
- `core/` — message_bus, event_system, shared_memory, task_queue
- `intelligence/` — knowledge_graph, citations, reflection_engine, learning_engine
- `modules/` — hermes (messaging), argus (vision), sentinel (security), voice, memory, etc.
- `constitutional_ai.py` — safety & validation
- `mouse_control.py`, `browser_control.py` — automation

### Frontend React (`frontend-react/`)
- Vite 8 + Rolldown build
- 12-column CSS grid dashboard with explicit col/row/w/h per card in localStorage
- Layout version: **v7** — key: `mj-dash-layout-v7`
- Flex layout chain: `#root` → `AppLayout` → `Sidebar(fixed)` + `MainContent(flex)` → `Header` + `ContentRow(flex)` → `content-main` + side panels
- Side panel pattern: state-driven conditional render alongside Routes
- Toast system via `CustomEvent('toast')` on `window`
- Settings panel with 4 tabs (Orb, Dashboard, Voice, Provider) using localStorage

### Key Files
- `src/App.jsx` — Main layout with Sidebar, Header, ContentRow, panels
- `src/hooks/useDashboard.js` — Layout state (v7), edit mode, save/load/reset, updateCardPos, getDefaultPos
- `src/components/dashboard/DashboardGrid.jsx` — 14 cards + orb, drag/resize handlers, grid-cell math, ghost/placeholder
- `src/components/dashboard/DashboardCard.jsx` — Card wrapper with edit toolbar, resize handle, position badge, drag handle
- `src/components/layout/MainContent.jsx` — MainContent + ContentRow wrappers
- `src/hooks/useSidebarResize.js` — Sidebar drag resize
- `src/hooks/useVoice.js` — Voice/wake word system
- `src/context/AppContext.jsx` — Global state (chatPanelOpen, etc.)
- `src/context/AuthContext.jsx` — Auth state
- `src/services/api.js` — All API service calls

### CSS Files (load order in main.jsx)
1. `theme.css` — CSS variables, design tokens
2. `animations.css` — Keyframes
3. `index.css` — Base resets, scrollbar, card base
4. `layout.css` — Main content, sidebar, header, sidebar widgets
5. `auth.css` — Login screen
6. `chat.css` — Chat panel
7. `orb.css` — Orb visualization
8. `dashboard.css` — Grid, cards, edit mode (toolbar/resize/badge/overlay), stats, models, quick actions, memory graph, timeline, agent network
9. `cards.css` — Card-specific styles
10. `panels.css` — Roadmap, Settings, AIFlow panels
11. `migration-cards.css` — All 13 migrated feature styles
12. `responsive.css` — Media queries

### Dashboard Cards (14 total)
1. `AICoreCard` — AI subsystem status (5 indicators, 21 modules)
2. `LiveIntelCard` — Real-time CPU/RAM/Network/GPU feed
3. `QuickCommandsCard` — 5 quick buttons + full command palette (4 categories, 27 cmds)
4. `SystemStatsCard` — System monitor with gauges
5. `ModelSelectorCard` — LLM model selector
6. `QuickActionsCard` — Quick action buttons
7. `SystemStatsWidgetCard` — 6 mini status tiles
8. `SmartSuggestionsCard` — AI suggestion chips
9. `MemoryGraphCard` — Memory visualization
10. `TimelineCard` — Activity timeline
11. `AgentNetworkCard` — Agent status visualization
12. `GestureControlCard` — Webcam gesture control
13. `HoloToggle` — Holographic mode toggle (inside orb card)
14. `VoiceLangSelector` — Voice language dropdown (9 languages)

### Panels
- `SettingsPanel` — 4-tab (Orb/Dashboard/Voice/Provider)
- `AIFlowPanel` — Right sidebar, resizable, shows AI pipeline stages
- `RoadmapPanel` — V1-V25 roadmap progress
- `SecurityPanel` — Auth/security overlay
- `ProcessPanel` — Sortable process table with kill action
- `ErrorPanel` — System errors with auto-fix

## WHAT WAS JUST COMPLETED (Latest Session)

### 1. Dashboard Scroll Fix
- **Problem**: Dashboard couldn't scroll — 3 nested `overflow: hidden` containers clipped all content below the fold
- **Fix**: Added `overflow-y: auto; overflow-x: hidden` to `.dashboard-wrapper` in `dashboard.css`
- Dashboard now scrolls independently, right sidebar (AIFlowPanel) stays fixed height

### 2. Complete Edit Layout Regression Fix
Audited old UI (`frontend/index.html`) vs new React and fixed ALL regressions:

**What was broken → Now fixed:**
- **Drag & Drop**: Was HTML5 swap-based → Now mouse-based with ghost element + grid-snapping placeholder (matches old UI)
- **Widget Resize**: Was completely missing → Now has corner drag handle + toolbar buttons (wider/narrower/taller/shorter)
- **Card Edit Toolbar**: Was missing → Now has color picker, resize buttons, per-card reset
- **Grid Overlay**: Was subtle stripes → Now full 12-column + row grid lines via `::before`
- **Position Badge**: Was missing → Now shows "C1 R1 4×5" per card in edit mode
- **Card Outline**: Was missing → Now 2px dashed cyan outline in edit mode
- **Layout Save**: Was only col/row/w/h → Now includes bg color + minHeight

**How drag works now (matching old UI):**
- `DashboardGrid` has `gridRef` to the `.dash-grid` element
- `getGridCell(clientX, clientY)` calculates exact grid col/row from mouse position
- `handleDragStart` creates imperative ghost div (fixed position, 60fps tracking), sets React state for placeholder
- Placeholder snaps to grid cells as mouse moves
- On mouseup, card gets placeholder's grid position
- Ghost element removed, dragState cleared

**How resize works now:**
- Corner drag: mousedown on `.card-resize-handle`, tracks dx/dy, calculates new w/h using `colW + gap` and `rowH` ratios
- Toolbar buttons: direct ±1 to col/row spans with bounds checking
- Per-card reset: restores DEFAULT_LAYOUT position for that card

**useDashboard.js API:**
```javascript
{
  layout,          // { cardId: { col, row, w, h, bg?, minH? } }
  editing,         // boolean
  enterEdit,       // () => void — snapshot current layout, set editing=true
  saveEdit,        // () => void — persist to localStorage, exit edit
  cancelEdit,      // () => void — restore snapshot, exit edit
  resetLayout,     // () => void — reset to DEFAULT_LAYOUT
  updateCardPos,   // (cardId, { col?, row?, w?, h?, bg?, minH? }) => void
  getDefaultPos,   // (cardId) => { col, row, w, h } | null
  getCardStyle,    // (cardId) => { gridColumn, gridRow, background?, minHeight? }
}
```

## ROADMAP STATUS (V1-V25)
V1-V17 are complete (100%). V18-V25 are pending.
- V18: Plugin System
- V19: Multi-Agent Orchestration
- V20: Predictive Intelligence
- V21: Advanced NLP Pipeline
- V22: DevOps Integration
- V23: Creative Suite
- V24: AR/VR Interface
- V25: Autonomous Operations

## IMPORTANT TECHNICAL NOTES
- `STORAGE_KEY = 'mj-dash-layout-v7'` — bumping resets all users' layouts
- Sidebar resize uses CSS variable `--sidebar-w` and localStorage key `mj-sidebar-width`
- AIFlow panel width stored in `mj-aiflow-width`
- Dashboard settings (theme/accent) in `mj-dash-settings`
- All card components have their own internal state and API fetching
- Voice system uses wake word detection + Web Speech API
- Toast notifications via `window.dispatchEvent(new CustomEvent('toast', { detail: { message, type } }))`
