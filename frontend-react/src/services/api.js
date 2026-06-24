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
  getStats: () => api.get('/zeus/stats'),
  getHistory: (limit = 20) => api.get('/zeus/history', { params: { limit } }),
  route: (message) => api.post('/zeus/route', { message }),
  // Workflows
  getWorkflows: () => api.get('/zeus/workflows'),
  getWorkflow: (name) => api.get(`/zeus/workflows/${name}`),
  createWorkflow: (name, description, steps) => {
    const form = new FormData();
    form.append('name', name);
    form.append('description', description || '');
    form.append('steps', JSON.stringify(steps));
    return api.post('/zeus/workflows', form);
  },
  deleteWorkflow: (name) => api.delete(`/zeus/workflows/${name}`),
  runWorkflow: (name, message) => api.post(`/zeus/workflows/${name}/run`, { message }),
  // Planning
  plan: (message) => api.post('/zeus/plan', { message }),
  breakdown: (message) => api.post('/zeus/breakdown', { message }),
  smartRoute: (message) => api.post('/zeus/smart-route', { message }),
  // Recovery
  getRecovery: () => api.get('/zeus/recovery'),
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
  // Deep Research
  deepResearch: (message) => api.post('/research', { message }),
  // Knowledge Graph
  graphStats: () => api.get('/knowledge/graph/stats'),
  graphGetAll: (limit = 200) => api.get(`/knowledge/graph?limit=${limit}`),
  graphGetNode: (label) => api.get(`/knowledge/graph/node/${encodeURIComponent(label)}`),
  graphSearch: (q, limit = 10) => api.get(`/knowledge/graph/search?q=${encodeURIComponent(q)}&limit=${limit}`),
  graphFindPath: (from, to) => api.get(`/knowledge/graph/path?from_node=${encodeURIComponent(from)}&to_node=${encodeURIComponent(to)}`),
  graphBuild: () => api.post('/knowledge/graph/build'),
  // Citations
  getCitations: () => api.get('/citations'),
  getBibliography: (format = 'apa') => api.get(`/citations/bibliography?format=${format}`),
  getCitationStats: () => api.get('/citations/stats'),
  getCitationHistory: (limit = 20) => api.get(`/citations/history?limit=${limit}`),
  clearCitations: () => api.post('/citations/clear'),
};

// --- HERMES MESSAGING ---
export const hermesAPI = {
  getConfig: () => api.get('/hermes/messaging/config'),
  updateConfig: (platform, settings) => api.post(`/hermes/messaging/config/${platform}`, settings),
  send: (message) => api.post('/hermes/messaging/send', { message }),
  sendTo: (platform, message) => api.post(`/hermes/messaging/send/${platform}`, { message }),
  broadcast: (message) => api.post('/hermes/messaging/broadcast', { message }),
  getHistory: (limit = 50, platform = '') => api.get(`/hermes/messaging/history?limit=${limit}${platform ? '&platform=' + platform : ''}`),
  getStats: () => api.get('/hermes/messaging/stats'),
  getPlatforms: () => api.get('/hermes/messaging/platforms'),
  test: (platform) => api.post(`/hermes/messaging/test/${platform}`),
};

// --- CONSTITUTIONAL AI / SAFETY ---
export const safetyAPI = {
  checkInput: (message) => api.post('/safety/check-input', { message }),
  checkOutput: (query, response) => api.post('/safety/check-output', { message: `${query}|||${response}` }),
  critique: (query, response) => api.post('/safety/critique', { message: `${query}|||${response}` }),
  hallucination: (message) => api.post('/safety/hallucination', { message }),
  confidence: (query, response) => api.post('/safety/confidence', { message: `${query}|||${response}` }),
  fullCheck: (query, response) => api.post('/safety/full-check', { message: `${query}|||${response}` }),
  policyCheck: (message) => api.post('/safety/policy', { message }),
  getConfig: () => api.get('/safety/config'),
  updateConfig: (settings) => api.post('/safety/config', settings),
  getStats: () => api.get('/safety/stats'),
  getAudit: (limit = 50) => api.get(`/safety/audit?limit=${limit}`),
  clearAudit: () => api.post('/safety/audit/clear'),
};

// --- REFLECTION ENGINE (V16) ---
export const reflectionAPI = {
  logMistake: (module, type, query, response = '') => api.post('/reflection/log-mistake', { message: `${module}|${type}|${query}|${response}` }),
  logSuccess: (module) => api.post('/reflection/log-success', { message: module }),
  getMistakes: (limit = 50, module = '') => api.get(`/reflection/mistakes?limit=${limit}${module ? '&module=' + module : ''}`),
  generateReport: (days = 7) => api.post(`/reflection/report?days=${days}`),
  getReports: (limit = 10) => api.get(`/reflection/reports?limit=${limit}`),
  getDaily: () => api.get('/reflection/daily'),
  getScores: () => api.get('/reflection/scores'),
  getScore: (module) => api.get(`/reflection/scores/${module}`),
  getSuggestions: () => api.get('/reflection/suggestions'),
  getStats: () => api.get('/reflection/stats'),
};

// --- LEARNING ENGINE (V17) ---
export const learningAPI = {
  recordAction: (action, module = '') => api.post('/learning/record', { message: `${action}|${module}` }),
  learn: (message) => api.post('/learning/learn', { message }),
  getHabits: () => api.get('/learning/habits'),
  detectHabits: () => api.post('/learning/habits/detect'),
  getPreferences: () => api.get('/learning/preferences'),
  getPreferencePrompt: () => api.get('/learning/preference-prompt'),
  logPromptFeedback: (type, positive, notes = '') => api.post('/learning/prompt-feedback', { message: `${type}|${positive}|${notes}` }),
  getPromptSuggestions: () => api.get('/learning/prompt-suggestions'),
  getPromptStats: () => api.get('/learning/prompt-stats'),
  getWorkflows: () => api.get('/learning/workflows'),
  detectWorkflows: () => api.post('/learning/workflows/detect'),
  getStats: () => api.get('/learning/stats'),
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

// --- CALENDAR (localStorage-based, no backend needed) ---
export const calendarAPI = {
  _key: 'mj-calendar-events',
  getEvents: () => {
    try {
      return JSON.parse(localStorage.getItem('mj-calendar-events') || '[]');
    } catch { return []; }
  },
  addEvent: (event) => {
    const events = calendarAPI.getEvents();
    const newEvent = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      ...event,
      createdAt: new Date().toISOString(),
    };
    events.push(newEvent);
    localStorage.setItem('mj-calendar-events', JSON.stringify(events));
    return newEvent;
  },
  deleteEvent: (id) => {
    const events = calendarAPI.getEvents().filter(e => e.id !== id);
    localStorage.setItem('mj-calendar-events', JSON.stringify(events));
    return events;
  },
  getEventsForDate: (dateStr) => {
    return calendarAPI.getEvents().filter(e => e.date === dateStr);
  },
};

// --- WEATHER ---
export const weatherAPI = {
  get: (city = 'Gurgaon', days = 3) => api.get(`/weather?city=${encodeURIComponent(city)}&days=${days}`),
  post: (params) => api.post('/weather', params),
};

// --- AGENT FRAMEWORK ---
export const frameworkAPI = {
  getStatus: () => api.get('/framework/status'),
  // Message Bus
  busPublish: (topic, sender, data) => {
    const form = new FormData();
    form.append('topic', topic);
    form.append('sender', sender || 'frontend');
    if (data) form.append('data', JSON.stringify(data));
    return api.post('/framework/bus/publish', form);
  },
  busHistory: (topic, limit = 50) => api.get('/framework/bus/history', { params: { topic, limit } }),
  busStats: () => api.get('/framework/bus/stats'),
  // Events
  eventsEmit: (name, source, data) => {
    const form = new FormData();
    form.append('name', name);
    form.append('source', source || 'frontend');
    if (data) form.append('data', JSON.stringify(data));
    return api.post('/framework/events/emit', form);
  },
  eventsHistory: (name, limit = 50) => api.get('/framework/events/history', { params: { name, limit } }),
  eventsStats: () => api.get('/framework/events/stats'),
  eventsTypes: () => api.get('/framework/events/types'),
  // Shared Memory
  memorySet: (key, value, namespace = 'global', ttl = null) => {
    const form = new FormData();
    form.append('key', key);
    form.append('value', JSON.stringify(value));
    form.append('namespace', namespace);
    if (ttl) form.append('ttl', ttl);
    return api.post('/framework/memory/set', form);
  },
  memoryGet: (key, namespace = 'global') => api.get(`/framework/memory/get/${key}`, { params: { namespace } }),
  memoryAll: () => api.get('/framework/memory/all'),
  memoryNamespace: (ns) => api.get(`/framework/memory/namespace/${ns}`),
  memoryStats: () => api.get('/framework/memory/stats'),
  memoryDelete: (key, namespace = 'global') => api.delete(`/framework/memory/${key}`, { params: { namespace } }),
  // Task Queue
  queueSubmit: (name, handler, params = {}, priority = 5) => {
    const form = new FormData();
    form.append('name', name);
    form.append('handler', handler);
    form.append('params', JSON.stringify(params));
    form.append('priority', priority);
    return api.post('/framework/queue/submit', form);
  },
  queueProcess: () => api.post('/framework/queue/process'),
  queueProcessAll: () => api.post('/framework/queue/process-all'),
  queueList: () => api.get('/framework/queue'),
  queueStats: () => api.get('/framework/queue/stats'),
  queueHistory: (limit = 50) => api.get('/framework/queue/history', { params: { limit } }),
  queueTask: (taskId) => api.get(`/framework/queue/${taskId}`),
  queueCancel: (taskId) => api.delete(`/framework/queue/${taskId}`),
};

export default api;
