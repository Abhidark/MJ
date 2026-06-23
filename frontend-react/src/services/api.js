import axios from 'axios';

// --- Axios Instance ---
const api = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Auth token injection
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mj_auth_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Global error handler
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('mj_auth_token');
      window.dispatchEvent(new Event('auth:logout'));
    }
    return Promise.reject(err);
  }
);

// --- AUTH ---
export const authAPI = {
  getStatus: () => api.get('/auth/status'),
  login: (password) => api.post('/auth/login', { password }),
  logout: () => api.post('/auth/logout'),
  changePassword: (old_password, new_password) =>
    api.post('/auth/change-password', { old_password, new_password }),
  toggle: (enabled, password) =>
    api.post('/auth/toggle', { enabled, password }),
};

// --- CHAT ---
export const chatAPI = {
  sendMessage: async (message, file = null) => {
    const form = new FormData();
    form.append('message', message);
    if (file) form.append('file', file);
    return fetch('/chat', { method: 'POST', body: form });
  },
  getChats: () => api.get('/chats'),
  getHistory: () => api.get('/history'),
  selectChat: (chatId) => api.post(`/select-chat/${chatId}`),
  newChat: () => api.post('/new-chat'),
  deleteChat: (chatId) => api.delete(`/delete-chat/${chatId}`),
};

// --- MEMORY ---
export const memoryAPI = {
  getCoreMemory: () => api.get('/core-memory'),
  remember: (fact) => api.post('/remember', { fact }),
  getContextMemory: () => api.get('/context-memory'),
};

// --- SYSTEM ---
export const systemAPI = {
  getStats: () => api.get('/system-stats'),
  getTopProcesses: () => api.get('/top-processes'),
  getProcesses: () => api.get('/processes'),
  killProcess: (pid) => api.post(`/processes/${pid}/kill`),
  getNetworkStats: () => api.get('/network-stats'),
  getHealth: () => api.get('/health'),
  getOllamaStatus: () => api.get('/ollama-status'),
  getWakeBriefing: () => api.get('/wake-briefing'),
};

// --- VOICE ---
export const voiceAPI = {
  speak: (text, emotion = 'neutral') =>
    fetch('/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, emotion }),
    }),
  getSettings: () => api.get('/voice-settings'),
  updateSettings: (settings) => api.post('/voice-settings', settings),
  testVoice: (params) => api.post('/test-voice', params),
};

// --- MODELS ---
export const modelAPI = {
  getModels: () => api.get('/models'),
  setActive: (model) => api.post('/models/set-active', { model }),
  toggleAuto: (enabled) => api.post('/models/auto-select', { enabled }),
  setTaskModel: (task, model) => api.post('/models/set-task-model', { task, model }),
  routePreview: (message) => api.post('/models/route', { message }),
  getProvider: () => api.get('/provider'),
  setProvider: (provider) => api.post('/provider/set', { provider }),
};

// --- ZEUS MODULES ---
export const zeusAPI = {
  getModules: () => api.get('/zeus/modules'),
  getModule: (name) => api.get(`/zeus/modules/${name}`),
  updateSettings: (name, settings) => api.post(`/zeus/modules/${name}/settings`, settings),
  executeModule: (name, input) => api.post(`/zeus/modules/${name}/execute`, { input }),
};

// --- ALERTS & ERRORS ---
export const alertAPI = {
  getAlerts: () => api.get('/alerts'),
  getActive: () => api.get('/alerts/active'),
  resolve: (id) => api.post(`/alerts/${id}/resolve`),
  clearAll: () => api.post('/alerts/clear'),
  clearResolved: () => api.post('/alerts/clear-resolved'),
  subscribe: () => new EventSource('/alerts/stream'),
};

export const errorAPI = {
  getErrors: () => api.get('/errors'),
  fix: (id) => api.post(`/errors/${id}/fix`),
  analyze: (id) => api.post(`/errors/${id}/analyze`),
  clearAll: () => api.post('/errors/clear'),
};

// --- KNOWLEDGE BASE ---
export const knowledgeAPI = {
  getStats: () => api.get('/knowledge-base'),
  search: (query) => api.post('/knowledge-base/search', { query }),
  ingest: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/knowledge-base/ingest', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  deleteDoc: (docId) => api.delete(`/knowledge-base/${docId}`),
};

// --- PLUGINS ---
export const pluginAPI = {
  getPlugins: () => api.get('/plugins'),
  reload: () => api.post('/plugins/reload'),
};

// --- PC CONTROL ---
export const pcAPI = {
  execute: (command) => api.post('/execute', { command }),
  notify: (message, title = 'MJ Assistant') =>
    api.post('/notify', { message, title }),
};

// --- SCHEDULING & REMINDERS ---
export const scheduleAPI = {
  getReminders: () => api.get('/reminders'),
  getScheduledTasks: () => api.get('/scheduled-tasks'),
};

// --- OCR & GIT ---
export const ocrAPI = {
  screenOCR: () => api.get('/ocr/screen'),
  fileOCR: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/ocr/file', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

export const gitAPI = {
  execute: (command) => api.post('/git', { command }),
  status: () => api.get('/git/status'),
};

// --- MISC ---
export const miscAPI = {
  getSuggestions: () => api.get('/suggestions'),
  getClipboardHistory: () => api.get('/clipboard/history'),
  getAppUsage: () => api.get('/app-usage'),
  getGeneratedImages: () => api.get('/generated-images'),
  getDiagnostics: () => api.get('/diagnostics'),
  getDiagnosticIssues: () => api.get('/diagnostics/issues'),
  getIntelligence: () => api.get('/intelligence'),
  getEmailConfig: () => api.get('/email/config'),
};

// --- WEATHER ---
export const weatherAPI = {
  get: (city = 'Gurgaon', days = 3) => api.get(`/weather?city=${encodeURIComponent(city)}&days=${days}`),
  post: (params) => api.post('/weather', params),
};

export default api;
