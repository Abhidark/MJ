import { createContext, useContext, useReducer } from 'react';

const AppContext = createContext(null);

const initialState = {
  isAuthenticated: !!localStorage.getItem('mj_auth_token'),
  currentChat: null,
  sidebarOpen: true,
  theme: 'dark',
  ollamaOnline: false,
  systemStats: null,
  chatPanelOpen: false,
  pendingVoiceMessage: null,
};

function appReducer(state, action) {
  switch (action.type) {
    case 'SET_AUTH':
      return { ...state, isAuthenticated: action.payload };
    case 'SET_CURRENT_CHAT':
      return { ...state, currentChat: action.payload };
    case 'TOGGLE_SIDEBAR':
      return { ...state, sidebarOpen: !state.sidebarOpen };
    case 'SET_OLLAMA_STATUS':
      return { ...state, ollamaOnline: action.payload };
    case 'SET_SYSTEM_STATS':
      return { ...state, systemStats: action.payload };
    case 'OPEN_CHAT_PANEL':
      return { ...state, chatPanelOpen: true, pendingVoiceMessage: action.payload || null };
    case 'CLOSE_CHAT_PANEL':
      return { ...state, chatPanelOpen: false, pendingVoiceMessage: null };
    case 'CLEAR_VOICE_MESSAGE':
      return { ...state, pendingVoiceMessage: null };
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  return (
    <AppContext.Provider value={{ state, dispatch }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}
