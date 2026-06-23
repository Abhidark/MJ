import { useRef, useEffect, useState } from 'react';
import { useChat } from '@/hooks/useChat';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ChatHistory from './ChatHistory';

// ─── Stage indicator text ───
function stageText(stage) {
  if (stage === 'understanding') return 'Understanding your message...';
  if (stage === 'calling_ai') return 'Calling AI...';
  if (stage === 'streaming') return '';
  return '';
}

export default function ChatPanel() {
  const {
    messages,
    chats,
    activeChatId,
    isStreaming,
    stage,
    modelInfo,
    sendMessage,
    cancelStream,
    selectChat,
    newChat,
    deleteChat,
  } = useChat();

  const [historyOpen, setHistoryOpen] = useState(false);
  const scrollRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages]);

  const handleSend = (text, file) => {
    sendMessage(text, file);
  };

  return (
    <div className="chat-panel">
      <ChatHistory
        chats={chats}
        activeChatId={activeChatId}
        onSelect={selectChat}
        onDelete={deleteChat}
        onNewChat={newChat}
        isOpen={historyOpen}
        onToggle={() => setHistoryOpen(h => !h)}
      />

      {/* Messages area */}
      <div className="chat-container" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <div className="chat-empty-orb" />
            <div className="chat-empty-title">MJ ASSISTANT</div>
            <div className="chat-empty-sub">Ask me anything — I'm ready.</div>
          </div>
        )}

        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {/* Stage indicator (while streaming, before tokens arrive) */}
        {isStreaming && stage && stage !== 'streaming' && (
          <div className="chat-stage-indicator">
            <div className="stage-dot" />
            <span>{stageText(stage)}</span>
          </div>
        )}
      </div>

      {/* Model info bar */}
      {modelInfo && (
        <div className="chat-model-bar">
          <span className="cmb-dot" />
          <span className="cmb-model">{modelInfo.model?.split(':')[0]}</span>
          <span className="cmb-provider">{modelInfo.provider?.toUpperCase()}</span>
          {modelInfo.task_type && modelInfo.task_type !== 'chat' && (
            <span className="cmb-task">{modelInfo.task_type}</span>
          )}
        </div>
      )}

      {/* Input */}
      <ChatInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
