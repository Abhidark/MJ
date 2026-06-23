import { useState, useEffect, useRef } from 'react';

const STORAGE_KEY = 'mj_notes';

function loadNotes() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []; }
  catch { return []; }
}

function saveNotes(notes) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(notes));
}

export default function NotesCard() {
  const [notes, setNotes] = useState(loadNotes);
  const [input, setInput] = useState('');
  const [editId, setEditId] = useState(null);
  const [editText, setEditText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => { saveNotes(notes); }, [notes]);

  const addNote = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    const note = {
      id: Date.now(),
      text,
      created: new Date().toISOString(),
      pinned: false,
    };
    setNotes(prev => [note, ...prev]);
    setInput('');
    inputRef.current?.focus();
  };

  const deleteNote = (id) => {
    setNotes(prev => prev.filter(n => n.id !== id));
  };

  const togglePin = (id) => {
    setNotes(prev => prev.map(n => n.id === id ? { ...n, pinned: !n.pinned } : n));
  };

  const startEdit = (note) => {
    setEditId(note.id);
    setEditText(note.text);
  };

  const saveEdit = () => {
    if (editText.trim()) {
      setNotes(prev => prev.map(n => n.id === editId ? { ...n, text: editText.trim() } : n));
    }
    setEditId(null);
    setEditText('');
  };

  // Sort: pinned first, then newest
  const sorted = [...notes].sort((a, b) => {
    if (a.pinned !== b.pinned) return b.pinned ? 1 : -1;
    return b.id - a.id;
  });

  return (
    <div className="notes-card">
      <div className="notes-header">
        <span className="notes-title">📝 NOTES</span>
        <span className="notes-count">{notes.length}</span>
      </div>

      {/* Add note */}
      <form onSubmit={addNote} className="notes-form">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Quick note..."
          className="notes-input"
        />
        <button type="submit" className="notes-add-btn">+</button>
      </form>

      {/* Notes list */}
      <div className="notes-list">
        {sorted.length === 0 && (
          <div className="notes-empty">No notes yet</div>
        )}
        {sorted.map(note => (
          <div key={note.id} className={`notes-item ${note.pinned ? 'pinned' : ''}`}>
            {editId === note.id ? (
              <div className="notes-edit">
                <input
                  type="text"
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && saveEdit()}
                  onBlur={saveEdit}
                  className="notes-edit-input"
                  autoFocus
                />
              </div>
            ) : (
              <>
                <div className="notes-text" onDoubleClick={() => startEdit(note)}>
                  {note.pinned && <span className="notes-pin-icon">📌 </span>}
                  {note.text}
                </div>
                <div className="notes-actions">
                  <button onClick={() => togglePin(note.id)} className="notes-action-btn" title={note.pinned ? 'Unpin' : 'Pin'}>
                    {note.pinned ? '📌' : '📍'}
                  </button>
                  <button onClick={() => startEdit(note)} className="notes-action-btn" title="Edit">✎</button>
                  <button onClick={() => deleteNote(note.id)} className="notes-action-btn delete" title="Delete">✕</button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
