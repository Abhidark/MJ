import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from '@/context/AppContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { useSidebarResize } from '@/hooks/useSidebarResize';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MainContent, { ContentRow } from '@/components/layout/MainContent';
import LoginScreen from '@/components/auth/LoginScreen';
import SecurityPanel from '@/components/auth/SecurityPanel';
import ChatPanel from '@/components/chat/ChatPanel';
import DashboardGrid from '@/components/dashboard/DashboardGrid';

// ─── Page placeholders (Day 7–10) ───
function ModulesView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8 }}>Zeus Modules</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>21 module cards — coming Day 7</p>
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
  const { needsLogin, checking } = useAuth();
  const { width, isResizing, iconsOnly, onMouseDown } = useSidebarResize(210);
  const [securityOpen, setSecurityOpen] = useState(false);

  if (checking) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="mj-login-orb" />
      </div>
    );
  }

  if (needsLogin) {
    return <LoginScreen />;
  }

  return (
    <>
      <div className="hex-grid-bg" />
      <div className="scanline-overlay" />

      <Sidebar
        width={width}
        iconsOnly={iconsOnly}
        isResizing={isResizing}
        onResizeStart={onMouseDown}
        onOrbSettings={() => console.log('TODO: Orb Settings panel')}
        onRoadmap={() => console.log('TODO: Roadmap panel')}
        onSecurity={() => setSecurityOpen(true)}
      />

      <MainContent isResizing={isResizing}>
        <Header
          onEditDashboard={() => console.log('TODO: Dashboard settings')}
          onSettings={() => console.log('TODO: Dashboard settings')}
        />
        <ContentRow>
          <Routes>
            <Route path="/" element={<DashboardGrid />} />
            <Route path="/chat" element={<ChatPanel />} />
            <Route path="/modules" element={<ModulesView />} />
            <Route path="/settings" element={<SettingsView />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </ContentRow>
      </MainContent>

      {securityOpen && <SecurityPanel onClose={() => setSecurityOpen(false)} />}
    </>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppLayout />
        </BrowserRouter>
      </AuthProvider>
    </AppProvider>
  );
}
