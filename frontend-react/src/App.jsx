import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from '@/context/AppContext';
import { useSidebarResize } from '@/hooks/useSidebarResize';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MainContent, { ContentRow } from '@/components/layout/MainContent';

// ─── Page placeholders (Day 3–10) ───
function DashboardView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 12 }}>{'\u{1F916}'}</div>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8, fontFamily: 'Orbitron, monospace', letterSpacing: 3 }}>
          JARVIS DASHBOARD
        </h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
          Orb + HUD cards + AI Flow panel — coming Day 3-4
        </p>
      </div>
    </div>
  );
}

function ChatView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8 }}>Chat Panel</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>SSE streaming chat — coming Day 5</p>
      </div>
    </div>
  );
}

function ModulesView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8 }}>Zeus Modules</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>21 module cards — coming Day 6</p>
      </div>
    </div>
  );
}

function SettingsView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8 }}>Settings</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>Voice, Models, Memory — coming Day 8</p>
      </div>
    </div>
  );
}

// ─── Layout Shell ───
function AppLayout() {
  const { width, isResizing, iconsOnly, onMouseDown } = useSidebarResize(210);

  return (
    <>
      {/* Background layers */}
      <div className="hex-grid-bg" />
      <div className="scanline-overlay" />

      {/* HUD Sidebar */}
      <Sidebar
        width={width}
        iconsOnly={iconsOnly}
        isResizing={isResizing}
        onResizeStart={onMouseDown}
        onOrbSettings={() => console.log('TODO: Orb Settings panel')}
        onRoadmap={() => console.log('TODO: Roadmap panel')}
        onSecurity={() => console.log('TODO: Security panel')}
      />

      {/* Main content area */}
      <MainContent isResizing={isResizing}>
        <Header
          onEditDashboard={() => console.log('TODO: Edit mode')}
          onSettings={() => console.log('TODO: Dashboard settings')}
        />
        <ContentRow>
          <Routes>
            <Route path="/" element={<DashboardView />} />
            <Route path="/chat" element={<ChatView />} />
            <Route path="/modules" element={<ModulesView />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ContentRow>
      </MainContent>
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <AppLayout />
      </BrowserRouter>
    </AppProvider>
  );
}
