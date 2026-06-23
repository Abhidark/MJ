# React Migration — 10 Day Plan
# Copy-paste each day's prompt into a NEW Claude session
# Push code at end of each day

---

## DAY 1 — Scaffold & Setup

```
I'm migrating my MJ-Assistant project from monolithic index.html (7500+ lines) to React. This is Day 1 of 10. My project is at F:\MJ\MJ-Assistant. Backend is FastAPI (Python). 

Today's task:
1. Create Vite + React project in `frontend-react/` folder (keep old `frontend/` working)
2. Set up folder structure: `components/`, `hooks/`, `services/`, `styles/`, `context/`
3. Create `services/api.js` — centralized API layer with all fetch calls + auth token injection from localStorage key `mj_auth_token`
4. Basic `App.jsx` entry point with React Router placeholder
5. Install and configure Tailwind CSS
6. Add proxy config in vite.config.js to forward /api calls to FastAPI backend at localhost:8000

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 1 - vite scaffold, folder structure, API layer, tailwind"
git push origin main
```

---

## DAY 2 — Layout Shell

```
I'm migrating MJ-Assistant to React. This is Day 2 of 10. Project at F:\MJ\MJ-Assistant. Yesterday I set up Vite + React in `frontend-react/`.

Today's task:
1. Create layout components: `App.jsx` with main layout structure
2. `components/layout/Sidebar.jsx` — left HUD sidebar (CPU, RAM, GPU, Network stats display, Orb Settings btn, Roadmap btn, Security btn)
3. `components/layout/Header.jsx` — top bar with logo "MJ", live time, date, weather mini widget slots
4. `components/layout/MainContent.jsx` — wrapper for dashboard + chat panel
5. Port all layout CSS from index.html into `styles/layout.css` (the grid structure, sidebar width, header height, responsive breakpoints)
6. Sidebar should be resizable with drag handle (like current implementation)

Reference: Read `frontend/index.html` lines 1-200 for CSS variables, lines 3060-3160 for sidebar HTML structure, lines 3384-3420 for main content wrapper.

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 2 - layout shell, sidebar, header, main content"
git push origin main
```

---

## DAY 3 — Auth Context + Login

```
I'm migrating MJ-Assistant to React. This is Day 3 of 10. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Create `context/AuthContext.jsx` — React context for auth state (token, isAuthenticated, login, logout, checkAuth)
2. Create `components/auth/LoginScreen.jsx` — full-screen login overlay matching current cyberpunk MJ theme (dark background, glowing orb, password input, "M J" title, "PERSONAL AI ASSISTANT" subtitle)
3. Create `components/auth/SecurityPanel.jsx` — panel with password lock toggle, change password form, logout button
4. Wrap App in AuthProvider — auto-check `/auth/status` on mount, show login if auth enabled + no valid token
5. Use `services/api.js` for all fetch calls (already has token injection)
6. Port login CSS from index.html (search for `mj-login-overlay` styles)

Backend auth endpoints already exist: POST /auth/login, POST /auth/logout, GET /auth/status, POST /auth/change-password, POST /auth/toggle

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 3 - auth context, login screen, security panel"
git push origin main
```

---

## DAY 4 — Chat Panel (BIGGEST DAY)

```
I'm migrating MJ-Assistant to React. This is Day 4 of 10. Project at F:\MJ\MJ-Assistant. This is the most important day — chat is the core feature.

Today's task:
1. Create `components/chat/ChatPanel.jsx` — main chat container
2. Create `components/chat/ChatMessage.jsx` — single message bubble (user/assistant), supports markdown rendering, code blocks
3. Create `components/chat/ChatInput.jsx` — input bar with send button, file attach button, file preview
4. Create `hooks/useChat.js` — custom hook handling:
   - Send message via POST /chat (FormData with message, chat_id, optional file)
   - SSE streaming response (EventSource pattern with ReadableStream)
   - AbortController for cancel/timeout (35s Groq, 60s Ollama)
   - Stage events from backend: understanding → calling_ai → streaming
   - Chat history load/save via /chats and /chats/{id}/messages endpoints
5. Create `components/chat/ChatHistory.jsx` — sidebar panel listing past chats with search
6. Port chat CSS (search index.html for `.chat-container`, `.msg-bubble`, `#user-input` styles)

Key backend endpoints: POST /chat (FormData: message, chat_id, file), GET /chats, GET /chats/{id}/messages, DELETE /chats/{id}

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 4 - chat panel, messages, SSE streaming, history"
git push origin main
```

---

## DAY 5 — Orb + Voice

```
I'm migrating MJ-Assistant to React. This is Day 5 of 10. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Create `components/orb/Orb.jsx` — animated orb with states: idle, listening, thinking, speaking, error. Canvas-based animation with pulse/glow effects
2. Create `hooks/useVoice.js` — custom hook for:
   - Speech-to-text via Web Speech API (webkitSpeechRecognition)
   - Text-to-speech via backend POST /tts endpoint (returns audio blob)
   - Orb state management based on voice activity
3. Create `components/orb/StatusDisplay.jsx` — shows current state text below orb ("Listening...", "Thinking...", etc.)
4. Create `hooks/useSystemStats.js` — fetches /system-stats every 5s (with visibility check), provides CPU/RAM/GPU/Network data
5. Wire orb click → toggle listening, voice result → send to chat
6. Port orb CSS and canvas animation from index.html (search for `#orb`, `.orb-container`, orb animation code in script)

Key: Orb animation should be 30fps when idle, 60fps when active. Pause when tab not visible.

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 5 - orb component, voice STT/TTS, system stats"
git push origin main
```

---

## DAY 6 — Dashboard Grid

```
I'm migrating MJ-Assistant to React. This is Day 6 of 10. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Create `components/dashboard/DashboardGrid.jsx` — 12-column CSS grid layout for dashboard cards
2. Create `components/dashboard/DashboardCard.jsx` — reusable card wrapper with title, icon, content slot
3. Create `hooks/useDashboard.js` — manages card positions, drag-to-reorder, save/load layout from localStorage
4. Create card components:
   - `components/dashboard/cards/SystemStatsCard.jsx` (CPU, RAM, GPU, Network bars)
   - `components/dashboard/cards/QuickActionsCard.jsx` (shortcut buttons)
   - `components/dashboard/cards/ModelSelectorCard.jsx` (dropdown to pick AI model, shows Groq vs Ollama)
5. Dashboard edit mode — toggle to show drag handles, reset layout button
6. Port dashboard grid CSS from index.html (search for `.dashboard-grid`, `.grid-card` styles)

Backend endpoints: GET /models (list available models), GET /system-stats

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 6 - dashboard grid, cards, drag-reorder, model selector"
git push origin main
```

---

## DAY 7 — Feature Widgets

```
I'm migrating MJ-Assistant to React. This is Day 7 of 10. Project at F:\MJ\MJ-Assistant.

Today's task — port these widgets as dashboard cards:
1. `components/dashboard/cards/WeatherCard.jsx` — shows weather data from GET /weather?city={city}, temperature, icon, forecast
2. `components/dashboard/cards/KnowledgeBaseCard.jsx` — search KB via GET /knowledge/search?q={query}, add entry via POST /knowledge, list via GET /knowledge
3. `components/dashboard/cards/FileManagerCard.jsx` — browse files via GET /files?path={path}, create/delete/move via POST /files/{action}
4. `components/dashboard/cards/NotesCard.jsx` — simple notes with save to localStorage
5. `components/dashboard/cards/FocusTimerCard.jsx` — pomodoro timer (25min work / 5min break), start/pause/reset
6. `components/dashboard/cards/CalendarCard.jsx` — mini calendar showing current month, highlight today

Port the widget CSS and functionality from index.html for each.

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 7 - weather, KB, file manager, notes, timer, calendar widgets"
git push origin main
```

---

## DAY 8 — Panels & Settings

```
I'm migrating MJ-Assistant to React. This is Day 8 of 10. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Create `components/panels/RoadmapPanel.jsx` — shows V1-V25 roadmap with progress bars, percentage, click to expand features. Reuse the roadmap data array from index.html (search for "const roadmap = [")
2. Create `components/panels/SettingsPanel.jsx` — orb settings (color, animation speed, voice selection from GET /voices)
3. Create `components/panels/AIFlowPanel.jsx` — resizable right panel showing AI processing flow visualization
4. Integrate SecurityPanel (from Day 3) into sidebar
5. Create `components/chat/ProviderBadge.jsx` — shows "Groq" or "Ollama" badge on messages based on provider info from SSE response
6. Wire all sidebar buttons (Orb Settings, Roadmap, Security) to toggle their respective panels

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 8 - roadmap, settings, AI flow panel, provider badge"
git push origin main
```

---

## DAY 9 — Canvas Animations & CSS

```
I'm migrating MJ-Assistant to React. This is Day 9 of 10. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Create `components/effects/ParticlesCanvas.jsx` — background particle animation using canvas (port from index.html, search for "particles" canvas code). 30fps, pause when tab hidden.
2. Create `components/effects/HexGrid.jsx` — hex grid background overlay
3. Create `components/effects/Scanline.jsx` — scanline CSS effect
4. Create `styles/theme.css` — all CSS variables (--accent, --bg-dark, --text-dim, etc.) ported from index.html
5. Create `styles/animations.css` — all keyframe animations (pulse, glow, fade, slide)
6. Create `styles/responsive.css` — all media queries for mobile/tablet
7. Ensure entire app matches the current cyberpunk/JARVIS HUD look exactly
8. Performance: Add visibility-based pause for all animations (MJPerf pattern from current code)

Rules: Do NOT touch `frontend/index.html`. Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing functionality.
```

Push:
```
git add .
git commit -m "react: day 9 - particles, hex grid, scanline, all CSS, animations"
git push origin main
```

---

## DAY 10 — Test, Fix, Deploy

```
I'm migrating MJ-Assistant to React. This is Day 10 of 10 — FINAL DAY. Project at F:\MJ\MJ-Assistant.

Today's task:
1. Read through all React components and fix any import errors, missing props, broken references
2. Test build: run `npm run build` in frontend-react/, fix any build errors
3. Update FastAPI backend to serve React build:
   - Add static mount for `frontend-react/dist/` folder
   - Update root route `/` to serve React's index.html
   - Keep `/static` mount as fallback for old frontend
4. Test all features work:
   - Chat send/receive with SSE streaming
   - Voice input/output
   - Dashboard grid with all cards
   - File manager, weather, KB
   - Auth login/logout (when enabled)
   - Orb animations and state changes
   - Sidebar resize
   - Mobile responsive
5. Fix any bugs found
6. Update roadmap V1 to 100%

Rules: Do NOT use my laptop/desktop control. Give git push commands at end (no cd commands). Do not damage existing backend functionality.
```

Push:
```
git add .
git commit -m "react: day 10 - final test, bug fixes, backend serves React, V1 100%"
git push origin main
```

---

## NOTES
- Always open NEW Claude session each day
- Copy-paste the day's prompt exactly
- Push at end of each day
- Old frontend/index.html stays untouched until Day 10
- If a day's work isn't finished, say "continue" in same session (don't start new one)
