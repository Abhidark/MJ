import { useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AppProvider } from '@/context/AppContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { useSidebarResize } from '@/hooks/useSidebarResize';
import { useVoice } from '@/hooks/useVoice';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MainContent, { ContentRow } from '@/components/layout/MainContent';
import LoginScreen from '@/components/auth/LoginScreen';
import SecurityPanel from '@/components/auth/SecurityPanel';
import ChatPanel from '@/components/chat/ChatPanel';
import Orb from '@/components/orb/Orb';
import StatusDisplay from '@/components/orb/StatusDisplay';

// ─── Dashboard with Orb ───
function DashboardView() {
  const navigate = useNavigate();

  const handleTranscript = useCallback((text) => {
    // Voice command → navigate to chat and send
    navigate('/chat', { state: { voiceMessage: text } });
  }, [navigate]);

  const handleWake = useCallback(() => {
    // First wake → could trigger briefing
    console.log('[MJ] Wake word detected — first activation');
  }, []);

  const voice = useVoice({
    onTranscript: handleTranscript,
    onWake: handleWake,
  });

  return (
    <div className="orb-section">
      <Orb state={voice.orbState} onClick={voice.handleOrbClick} />
      <StatusDisplay
        orbState={voice.orbState}
        micStatus={voice.micStatus}
        waveState={voice.waveState}
        listening={voice.listening}
        onMicToggle={voice.toggleListening}
      />
    </div>
  );
}

// ─── Page placeholders (Day 6–10) ───
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
          onEditDashboard={() => console.log('TODO: Edit mode')}
          onSettings={() => console.log('TODO: Dashboard settings')}
        />
        <ContentRow>
          <Routes>
            <Route path="/" element={<DashboardView />} />
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
