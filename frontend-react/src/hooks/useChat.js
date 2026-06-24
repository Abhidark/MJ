import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * useChat -- manages chat state, SSE streaming, history CRUD
 *
 * SSE event format from POST /chat:
 *   { model, provider, task_type, stage: "calling_ai", prep_ms }  -- first event
 *   { stage: "streaming" }                                         -- streaming started
 *   { token: "..." }                                               -- incremental text
 *   { emotion: "happy" }                                           -- detected emotion
 *   { weather_widget: {...} }                                      -- inline widget
 *   { image_url: "..." }                                           -- generated image
 *   { model_used, perf_time, timings, auto_memory, issues, ... }   -- summary
 *   data: [DONE]                                                   -- stream end
 */

const TIMEOUT_GROQ = 35000;
const TIMEOUT_OLLAMA = 60000;

// --- helpers ---
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

  // --- Load chat list ---
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

  // --- Select a chat and load its messages ---
  const selectChat = useCallback(async (chatId) => {
    try {
      const res = await fetch('/select-chat/' + chatId, { method: 'POST' });
      if (!res.ok) return;
      const data = await res.json();
      setActiveChatId(chatId);
      setMessages(
        (data.history || []).map((m, i) => ({
          id: 'hist-' + chatId + '-' + i,
          role: m.role,
          content: m.content,
          timestamp: '',
        }))
      );
    } catch (e) {
      console.error('[useChat] selectChat error:', e);
    }
  }, []);

  // --- New chat ---
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

  // --- Delete chat ---
  const deleteChat = useCallback(async (chatId) => {
    try {
      const res = await fetch('/delete-chat/' + chatId, { method: 'DELETE' });
      if (!res.ok) return;
      if (chatId === activeChatId) setMessages([]);
      await loadChats();
    } catch (e) {
      console.error('[useChat] deleteChat error:', e);
    }
  }, [activeChatId, loadChats]);

  // --- Cancel active stream ---
  const cancelStream = useCallback(() => {
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch (_) {}
      abortRef.current = null;
    }
    setIsStreaming(false);
    setStage(null);
  }, []);

  // --- Send message ---
  const sendMessage = useCallback(async (text, file) => {
    if ((!text || !text.trim()) && !file) return;

    // Cancel any previous in-flight request
    if (abortRef.current) {
      try { abortRef.current.abort(); } catch (_) {}
    }

    var userFile = null;
    if (file) {
      userFile = { name: file.name, size: file.size };
    }

    var userMsg = {
      id: 'msg-' + Date.now() + '-u',
      role: 'user',
      content: text.trim(),
      timestamp: nowTimestamp(),
      file: userFile,
    };

    setMessages(function(prev) { return prev.concat([userMsg]); });
    setIsStreaming(true);
    setStage('understanding');
    setModelInfo(null);

    var assistantId = 'msg-' + Date.now() + '-a';
    // Add placeholder assistant message
    setMessages(function(prev) {
      return prev.concat([{ id: assistantId, role: 'assistant', content: '', timestamp: '', streaming: true }]);
    });

    var abortCtrl = new AbortController();
    abortRef.current = abortCtrl;

    // Build FormData
    var formData = new FormData();
    formData.append('message', text.trim());
    if (file) formData.append('file', file);

    // Determine timeout based on current provider
    var responseStarted = false;
    var TIMEOUT_MS = modelInfo?.provider === 'groq' ? TIMEOUT_GROQ : TIMEOUT_OLLAMA;

    var hardTimeout = setTimeout(function() {
      if (!responseStarted) {
        console.warn('[useChat] Hard timeout -- aborting after', TIMEOUT_MS, 'ms');
        abortCtrl.abort();
      }
    }, TIMEOUT_MS);

    try {
      var res = await fetch('/chat', {
        method: 'POST',
        body: formData,
        signal: abortCtrl.signal,
      });

      if (!res.ok) throw new Error('Server error: ' + res.status);

      var reader = res.body.getReader();
      var decoder = new TextDecoder();
      var buffer = '';
      var insideThink = false;
      var detectedModel = null;
      var detectedProvider = null;

      while (true) {
        var result = await reader.read();
        if (result.done) break;

        var chunk = decoder.decode(result.value);
        var lines = chunk.split('\n');
        for (var li = 0; li < lines.length; li++) {
          var line = lines[li];
          if (!line.startsWith('data: ') || line === 'data: [DONE]') continue;

          try {
            var data = JSON.parse(line.slice(6));

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
              // Store provider on the assistant message early
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    return Object.assign({}, m, { provider: data.provider || 'ollama' });
                  }
                  return m;
                });
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
              var needsFilter = detectedProvider !== 'groq' &&
                /qwen3|deepseek/i.test(detectedModel || '');
              if (needsFilter && buffer.includes('<think>')) insideThink = true;
              if (insideThink) {
                if (buffer.includes('</think>')) {
                  insideThink = false;
                  buffer = buffer.replace(/<think>[\s\S]*?<\/think>/g, '').trim();
                }
              }

              if (!insideThink) {
                var displayBuffer = buffer;
                setMessages(function(prev) {
                  return prev.map(function(m) {
                    if (m.id === assistantId) {
                      return Object.assign({}, m, { content: displayBuffer });
                    }
                    return m;
                  });
                });
              }
            }

            // Image event
            if (data.image_url) {
              responseStarted = true;
              clearTimeout(hardTimeout);
              var url = data.image_url;
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    var imgs = (m.images || []).concat([url]);
                    return Object.assign({}, m, { images: imgs });
                  }
                  return m;
                });
              });
            }

            // Weather widget
            if (data.weather_widget) {
              responseStarted = true;
              clearTimeout(hardTimeout);
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    return Object.assign({}, m, { weather: data.weather_widget });
                  }
                  return m;
                });
              });
            }

            // Emotion
            if (data.emotion) {
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    return Object.assign({}, m, { emotion: data.emotion });
                  }
                  return m;
                });
              });
            }

            // Summary / final event
            if (data.model_used) {
              var finalModel = data.model_used;
              var finalTask = data.task_type || 'chat';
              setModelInfo(function(prev) {
                return Object.assign({}, prev, { model: finalModel, task_type: finalTask });
              });
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    return Object.assign({}, m, {
                      modelBadge: finalModel,
                      perfTime: data.perf_time,
                      provider: detectedProvider || m.provider,
                    });
                  }
                  return m;
                });
              });
            }

            // Auto-memory
            if (data.auto_memory && data.auto_memory.length > 0) {
              setMessages(function(prev) {
                return prev.map(function(m) {
                  if (m.id === assistantId) {
                    return Object.assign({}, m, { autoMemory: data.auto_memory });
                  }
                  return m;
                });
              });
            }
          } catch (_) {}
        }
      }

      // Stream complete -- finalize
      setMessages(function(prev) {
        return prev.map(function(m) {
          if (m.id === assistantId) {
            return Object.assign({}, m, { streaming: false, timestamp: nowTimestamp() });
          }
          return m;
        });
      });
      loadChats();

    } catch (err) {
      clearTimeout(hardTimeout);
      var errorText = err.name === 'AbortError'
        ? 'Request timed out. Please try again.'
        : 'Send failed: ' + err.message;

      setMessages(function(prev) {
        return prev.map(function(m) {
          if (m.id === assistantId) {
            return Object.assign({}, m, {
              content: errorText,
              streaming: false,
              error: true,
              timestamp: nowTimestamp(),
            });
          }
          return m;
        });
      });
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
      setStage(null);
    }
  }, [modelInfo, loadChats]);

  // Load chats on mount
  useEffect(function() {
    loadChats();
  }, [loadChats]);

  // Load current chat history on mount
  useEffect(function() {
    async function loadCurrent() {
      try {
        var res = await fetch('/history');
        if (!res.ok) return;
        var data = await res.json();
        if (data.history && data.history.length > 0) {
          setMessages(
            data.history.map(function(m, i) {
              return {
                id: 'init-' + i,
                role: m.role,
                content: m.content,
                timestamp: '',
              };
            })
          );
        }
      } catch (_) {}
    }
    loadCurrent();
  }, []);

  return {
    messages: messages,
    chats: chats,
    activeChatId: activeChatId,
    isStreaming: isStreaming,
    stage: stage,
    modelInfo: modelInfo,
    sendMessage: sendMessage,
    cancelStream: cancelStream,
    loadChats: loadChats,
    selectChat: selectChat,
    newChat: newChat,
    deleteChat: deleteChat,
  };
}
