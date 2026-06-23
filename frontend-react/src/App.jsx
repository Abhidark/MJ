import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from '@/context/AppContext';

function ChatPage() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="card p-8 text-center">
        <div className="text-4xl mb-4">&#129302;</div>
        <h1 className="text-2xl font-bold text-[var(--cyan)] mb-2">MJ Assistant</h1>
        <p className="text-[var(--text-dim)]">Chat interface — coming Day 2</p>
        <div className="mt-6 flex gap-3 justify-center text-sm">
          <a href="/dashboard" className="px-4 py-2 rounded-lg bg-[var(--cyan-dim)] text-[var(--cyan)] hover:bg-[var(--cyan-glow)] transition-colors">Dashboard</a>
          <a href="/modules" className="px-4 py-2 rounded-lg bg-[var(--cyan-dim)] text-[var(--cyan)] hover:bg-[var(--cyan-glow)] transition-colors">Modules</a>
          <a href="/settings" className="px-4 py-2 rounded-lg bg-[var(--cyan-dim)] text-[var(--cyan)] hover:bg-[var(--cyan-glow)] transition-colors">Settings</a>
        </div>
      </div>
    </div>
  );
}

function DashboardPage() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="card p-8 text-center">
        <h1 className="text-2xl font-bold text-[var(--cyan)] mb-2">Dashboard</h1>
        <p className="text-[var(--text-dim)]">Orb + HUD + AI Flow — coming Day 4</p>
      </div>
    </div>
  );
}

function ModulesPage() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="card p-8 text-center">
        <h1 className="text-2xl font-bold text-[var(--cyan)] mb-2">Zeus Modules</h1>
        <p className="text-[var(--text-dim)]">21 module cards — coming Day 6</p>
      </div>
    </div>
  );
}

function SettingsPage() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="card p-8 text-center">
        <h1 className="text-2xl font-bold text-[var(--cyan)] mb-2">Settings</h1>
        <p className="text-[var(--text-dim)]">Voice, Models, Memory — coming Day 8</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/modules" element={<ModulesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AppProvider>
  );
}
