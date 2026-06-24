import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider, useApp } from '@/context/AppContext';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { useSidebarResize } from '@/hooks/useSidebarResize';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MainContent, { ContentRow } from '@/components/layout/MainContent';
import LoginScreen from '@/components/auth/LoginScreen';
import SecurityPanel from '@/components/auth/SecurityPanel';
import RoadmapPanel from '@/components/panels/RoadmapPanel';
import SettingsPanel from '@/components/panels/SettingsPanel';
import AIFlowPanel from '@/components/panels/AIFlowPanel';
import ChatPanel from '@/components/chat/ChatPanel';
import DashboardGrid from '@/components/dashboard/DashboardGrid';
import ParticlesCanvas from '@/components/effects/ParticlesCanvas';
import HexGrid from '@/components/effects/HexGrid';
import Scanline from '@/components/effects/Scanline';
import ToastContainer from '@/components/ui/ToastContainer';
import ProcessPanel from '@/components/panels/ProcessPanel';
import ErrorPanel from '@/components/panels/ErrorPanel';

function ModulesView() {
  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ padding: 32, textAlign: 'center' }}>
        <h2 style={{ color: 'var(--cyan)', marginBottom: 8 }}>Zeus Modules</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>21 module cards - coming soon</p>
      </div>
    </div>
  );
}

function AppLayout() {
  const { needsLogin, checking } = useAuth();
  const { state, dispatch } = useApp();
  const { width, isResizing, iconsOnly, onMouseDown } = useSidebarResize(210);

  const [securityOpen, setSecurityOpen] = useState(false);
  const [roadmapOpen, setRoadmapOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [aiFlowOpen, setAiFlowOpen] = useState(false);
  const [processOpen, setProcessOpen] = useState(false);
  const [errorPanelOpen, setErrorPanelOpen] = useState(false);

  if (checking) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="mj-login-orb" />
      </div>
    );
  }

  if (needsLogin) return <LoginScreen />;

  return (
    <>
      <ParticlesCanvas />
      <HexGrid />
      <Scanline />

      <Sidebar
        width={width}
        iconsOnly={iconsOnly}
        isResizing={isResizing}
        onResizeStart={onMouseDown}
        onOrbSettings={() => setSettingsOpen(true)}
        onRoadmap={() => setRoadmapOpen(true)}
        onSecurity={() => setSecurityOpen(true)}
      />

      <MainContent isResizing={isResizing}>
        <Header
          onEditDashboard={() => {}}
          onSettings={() => setSettingsOpen(true)}
          onAIFlow={() => setAiFlowOpen(f => !f)}
          aiFlowOpen={aiFlowOpen}
        />
        <ContentRow>
          <div className={`content-main${state.chatPanelOpen ? ' with-side-chat' : ''}`}>
            <Routes>
              <Route path="/" element={<DashboardGrid />} />
              <Route path="/chat" element={<ChatPanel />} />
              <Route path="/modules" element={<ModulesView />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
          {state.chatPanelOpen && (
            <div className="chat-side-panel">
              <button
                className="chat-side-close"
                onClick={() => dispatch({ type: 'CLOSE_CHAT_PANEL' })}
                title="Close chat panel"
              >x</button>
              <ChatPanel sideMode />
            </div>
          )}
          {aiFlowOpen && (
            <AIFlowPanel
              onClose={() => setAiFlowOpen(false)}
              modelInfo={null}
              chatStage={null}
            />
          )}
        </ContentRow>
      </MainContent>

      {securityOpen && <SecurityPanel onClose={() => setSecurityOpen(false)} />}
      {roadmapOpen && <RoadmapPanel onClose={() => setRoadmapOpen(false)} />}
      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      {processOpen && <ProcessPanel onClose={() => setProcessOpen(false)} />}
      {errorPanelOpen && <ErrorPanel onClose={() => setErrorPanelOpen(false)} />}
      <ToastContainer />
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
