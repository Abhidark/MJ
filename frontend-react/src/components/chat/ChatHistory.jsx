import { useState, useMemo, useCallback } from 'react';

export default function ChatHistory({ chats, activeChatId, onSelect, onDelete, onNewChat, isOpen, onToggle }) {
  const [search, setSearch] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null); // chatId pending confirmation

  const filtered = useMemo(() => {
    if (!search.trim()) return chats;
    const q = search.toLowerCase();
    return chats.filter(c => c.title?.toLowerCase().includes(q));
  }, [chats, search]);

  const handleDelete = useCallback((e, chatId) => {
    e.stopPropagation();
    setConfirmDelete(chatId);
  }, []);

  const confirmDeleteAction = useCallback(() => {
    if (confirmDelete) {
      onDelete(confirmDelete);
      setConfirmDelete(null);
    }
  }, [confirmDelete, onDelete]);

  return (
    <>
      {/* Header buttons row — always visible */}
      <div className="chat-header">
        <h2>COMM CHANNEL</h2>
        <div className="chat-header-btns">
          <button onClick={onNewChat}>
            <span className="btn-icon">+</span> NEW
          </button>
          <button
            className={isOpen ? 'active-hist' : ''}
            onClick={onToggle}
          >
            <span className="btn-icon">☰</span> HISTORY
          </button>
        </div>
      </div>

      {/* Collapsible history panel */}
      <div className={`chat-history${isOpen ? ' open' : ''}`}>
        {/* Search bar */}
        <div className="ch-search-bar">
          <span>🔍</span>
          <input
            className="ch-search-input"
            placeholder="Search chats..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button className="ch-search-clear visible" onClick={() => setSearch('')}>
              CLEAR
            </button>
          )}
        </div>

        {/* Chat list */}
        <div className="chat-history-inner">
          {filtered.length === 0 ? (
            <div className="ch-empty">
              {search ? 'No matches found' : 'No conversations yet'}
            </div>
          ) : (
            filtered.map(chat => (
              <div
                key={chat.id}
                className={`ch-item${chat.id === activeChatId ? ' active' : ''}`}
                onClick={() => onSelect(chat.id)}
              >
                <span className="ch-item-title">{chat.title || 'Untitled Chat'}</span>
                <button
                  className="ch-delete"
                  onClick={(e) => handleDelete(e, chat.id)}
                  title="Delete"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Delete confirmation overlay */}
      {confirmDelete && (
        <div className="chat-delete-confirm open">
          <div className="cdc-box">
            <span className="cdc-icon">⚠️</span>
            <div className="cdc-title">DELETE CHAT</div>
            <div className="cdc-desc">
              This conversation will be permanently deleted. This cannot be undone.
            </div>
            <div className="cdc-btns">
              <button className="cdc-cancel" onClick={() => setConfirmDelete(null)}>
                CANCEL
              </button>
              <button className="cdc-delete" onClick={confirmDeleteAction}>
                DELETE
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
