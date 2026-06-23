import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * useChat — manages chat state, SSE streaming, history CRUD
 *
 * SSE event format from POST /chat:
 *   { model, provider, task_type, stage: "calling_ai", prep_ms }  — first event
 *   { stage: "streaming" }                                         — streaming started
 *   { token: "..." }                                               — incremental text
 *   { emotion: "happy" }                                           — detected emotion
 *   { weather_widget: {...} }                                      — inline widget
 *   { image_url: "..." }                                           — generated image
 *   { model_used, perf_time, timings, auto_memory, issues, ... }   — summary
 *   data: [DONE]                                                   — stream end
 */

const TIMEOUT_GROQ = 35000;
const TIMEOUT_OLLAMA = 60000;

// ─── helpers ───
function nowTimestamp() {
  return new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

export function useChat() {
  const [messages, setMessages] = useState([]);
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [stage, setStage] = useState(null);        // null | 'understanding' | 'calling_ai' | 'streaming'
  const [modelInfo, setModelInfo] = useState(null); // { model, provider, task_type }
  const abortRef = useRef(null);

  // ─── Load chat list ───
  const loadChats = useCallback(async () => {
    try {
      const res = await fetch('/chats');
      if (!res.ok) return;
      const data = await res.json();
      setChats(data.chats || []);
      if (data.active) setActiveChatId(data.active);
    } catch (e) {
      console.error('[useChat] loadChats error:', e);
    }
  }, []);

  // ─── Select a chat and load its messages ───
  const selectChat = useCallback(async (chatId) => {
    try {
      const res = await fetch(`/select-chat/${chatId}`, { method: 'POST' });
      if (!res.ok) return;
      const data = await res.json();
      setActiveChatId(chatId);
      setMessages(
        (data.history || []).map((m, i) => ({
          id: `hist-${chatId}-${i}`,
          role: m.role,
          content: m.content,
          timestamp: '',
        }))
      );
    } catch (e) {
      console.error('[useChat] selectChat error:', e);
    }
  }, []);

  // ─── New chat ───
  const newChat = useCallback(async () => {
    try {
      const res = await fetch('/new-chat', { method: 'POST' });
      if (!res.ok) return;
      const data = await res.json();
      setActiveChatId(data.chat_id);
      setMessages([]);
      await loadChats();
    } catch (e) {
      console.error('[useChat] newChat error:', e);
    }
  }, [loadChats]);

  // ─── Delete chat ───
  const deleteChat = useCallback(async (chatId) => {
    try {
      const res = await fetch(`/delete-chat/${chatId}`, { method: 'DELETE' });
      if (!res.ok) return;
      if (chatId === activeChatId) setMessages([]);
      await loadChats();
    } catch (e) {
      console.error('[useChat] deleteChat error:', e);
    }
  }, [activeChatId, loadChats]);

  // ─── Cancel active stream ───
  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch (_) {}
      abortRef.current = null;
    }
    setIsStreaming(false);
    setStage(null);
  }, []);

  // ─── Send message ───
  const sendMessage = useCallback(async (text, file = null) => {
    if ((!text || !text.trim()) && !file) return;

    // Cancel any previous in-flight request
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch (_) {}
    }

    const userMsg = {
      id: `msg-${Date.now()}-u`,
      role: 'user',
      content: text.trim(),
      timestamp: nowTimestamp(),
      file: file ? { name: file.name, size: file.size } : null,
    };

    setMessages(prev => [...prev, userMsg]);
    setIsStreaming(true);
    setStage('understanding');
    setModelInfo(null);

    const assistantId = `msg-${Date.now()}-a`;
    // Add placeholder assistant message
    setMessages(prev => [
      ...prev,
      { id: assistantId, role: 'assistant', content: '', timestamp: '', streaming: true },
    ]);

    const abortCtrl = new AbortController();
    abortRef.current = abortCtrl;

    // Build FormData
    const formData = new FormData();
    formData.append('message', text.trim());
    if (file) formData.append('file', file);

    // Determine timeout based on current provider
    let responseStarted = false;
    const TIMEOUT_MS = modelInfo?.provider === 'groq' ? TIMEOUT_GROQ : TIMEOUT_OLLAMA;

    const hardTimeout = setTimeout(() => {
      if (!responseStarted) {
        console.warn('[useChat] Hard timeout — aborting after', TIMEOUT_MS, 'ms');
        abortCtrl.abort();
      }
    }, TIMEOUT_MS);

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        body: formData,
        signal: abortCtrl.signal,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let insideThink = false;
      let detectedModel = null;
      let detectedProvider = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

          try {
            const data = JSON.parse(line.slice(6));

            // Stage events
            if (data.stage) {
              if (data.stage === 'calling_ai') {
                setStage('calling_ai');
              } else if (data.stage === 'streaming') {
                setStage('streaming');
              }
            }

            // Model info event (first SSE event)
            if (data.model && !data.token) {
              responseStarted = true;
              clearTimeout(hardTimeout);
              detectedModel = data.model;
              detectedProvider = data.provider || 'ollama';
              setModelInfo({
                model: data.model,
                provider: data.provider || 'ollama',
                task_type: data.task_type || 'chat',
              });
              setStage('calling_ai');
              continue;
            }

            // Token event
            if (data.token) {
              if (!responseStarted) {
                responseStarted = true;
                clearTimeout(hardTimeout);
              }
              buffer += data.token;

              // Think-tag filter for deepseek/qwen3 (non-groq)
              const needsFilter = detectedProvider !== 'groq' &&
                /qwen3|deepseek/i.test(detectedModel || '');
              if (needsFilter && buffer.includes('<think>')) insideThink = true;
              if (insideThink) {
                if (buffer.includes('</think>')) {
                  insideThink = false;
                  buffer = buffer.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                }
              }

              if (!insideThink) {
                const displayBuffer = buffer;
                setMessages(prev =>
                  prev.map(m =>
                    m.id === assistantId ? { ...m, content: displayBuffer } : m
                  )
                );
              }
            }

            // Image event
            if (data.image_url) {
              responseStarted = true;
              clearTimeout(hardTimeout);
              const url = data.image_url;
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, images: [...(m.images || []), url] }
                    : m
                )
              );
            }

            // Weather widget
            if (data.weather_widget) {
              responseStarted = true;
              clearTimeout(hardTimeout);
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, weather: data.weather_widget }
                    : m
                )
              );
            }

            // Emotion
            if (data.emotion) {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId ? { ...m, emotion: data.emotion } : m
                )
              );
            }

            // Summary / final event
            if (data.model_used) {
              const finalModel = data.model_used;
              const finalTask = data.task_type || 'chat';
              setModelInfo(prev => ({ ...prev, model: finalModel, task_type: finalTask }));
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, modelBadge: finalModel, perfTime: data.perf_time }
                    : m
                )
              );
            }

            // Auto-memory
            if (data.auto_memory && data.auto_memory.length > 0) {
              setMessages(prev =>
                prev.map(m =>
                  m.id === assistantId
                    ? { ...m, autoMemory: data.auto_memory }
                    : m
                )
              );
            }
          } catch (_) {}
        }
      }

      // Stream complete — finalize
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, streaming: false, timestamp: nowTimestamp() }
            : m
        )
      );
      loadChats();

    } catch (err) {
      clearTimeout(hardTimeout);
      const errorText = err.name === 'AbortError'
        ? '⏳ Request timed out. Please try again.'
        : `⚠️ Send failed: ${err.message}`;

      setMessages(prev =>
        prev.map(m =>
          m.id === assistantId
            ? { ...m, content: errorText, streaming: false, error: true, timestamp: nowTimestamp() }
            : m
        )
      );
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
      setStage(null);
    }
  }, [modelInfo, loadChats]);

  // Load chats on mount
  useEffect(() => {
    loadChats();
  }, [loadChats]);

  // Load current chat history on mount
  useEffect(() => {
    async function loadCurrent() {
      try {
        const res = await fetch('/history');
        if (!res.ok) return;
        const data = await res.json();
        if (data.history && data.history.length > 0) {
          setMessages(
            data.history.map((m, i) => ({
              id: `init-${i}`,
              role: m.role,
              content: m.content,
              timestamp: '',
            }))
          );
        }
      } catch (_) {}
    }
    loadCurrent();
  }, []);

  return {
    messages,
    chats,
    activeChatId,
    isStreaming,
    stage,
    modelInfo,
    sendMessage,
    cancelStream,
    loadChats,
    selectChat,
    newChat,
    deleteChat,
  };
}
