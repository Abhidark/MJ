import { useState, useRef, useCallback } from 'react';

// File size formatter
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [fileThumb, setFileThumb] = useState(null);
  const inputRef = useRef(null);
  const fileRef = useRef(null);

  const handleSend = useCallback(() => {
    if ((!text.trim() && !file) || disabled) return;
    onSend(text, file);
    setText('');
    setFile(null);
    setFileThumb(null);
    inputRef.current?.focus();
  }, [text, file, disabled, onSend]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleFileSelect = useCallback((e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    // Generate thumbnail for images
    if (f.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (ev) => setFileThumb(ev.target.result);
      reader.readAsDataURL(f);
    } else {
      setFileThumb(null);
    }
  }, []);

  const clearFile = useCallback(() => {
    setFile(null);
    setFileThumb(null);
    if (fileRef.current) fileRef.current.value = '';
  }, []);

  // Drag & drop
  const [dragging, setDragging] = useState(false);

  const onDragOver = useCallback((e) => { e.preventDefault(); setDragging(true); }, []);
  const onDragLeave = useCallback(() => setDragging(false), []);
  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f) {
      setFile(f);
      if (f.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (ev) => setFileThumb(ev.target.result);
        reader.readAsDataURL(f);
      }
    }
  }, []);

  const fileIcon = file
    ? (file.type.startsWith('image/') ? '🖼️'
      : file.type.includes('pdf') ? '📄'
      : file.type.includes('text') ? '📝'
      : '📎')
    : null;

  return (
    <div
      className="chat-input-wrapper"
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      {/* File preview */}
      {file && (
        <div className="file-preview visible">
          <div className="file-preview-info">
            {fileThumb
              ? <img src={fileThumb} alt="" className="file-preview-thumb" />
              : <span className="file-preview-icon">{fileIcon}</span>
            }
            <span className="file-preview-name">{file.name}</span>
            <span className="file-preview-size">{formatFileSize(file.size)}</span>
          </div>
          <button className="file-remove-btn" onClick={clearFile}>✕</button>
        </div>
      )}

      {/* Input bar */}
      <div className="input-bar">
        <button
          className={`attach-btn${file ? ' has-file' : ''}`}
          onClick={() => fileRef.current?.click()}
          title="Attach file"
        >
          📎
        </button>
        <input
          type="file"
          ref={fileRef}
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          accept=".txt,.pdf,.jpg,.jpeg,.png,.csv,.json,.py,.js,.md"
        />

        <textarea
          ref={inputRef}
          className="chat-textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask MJ anything..."
          rows={1}
          disabled={disabled}
        />

        <button
          className="send-btn"
          onClick={handleSend}
          disabled={disabled || (!text.trim() && !file)}
        >
          SEND
        </button>
      </div>

      {/* Drop overlay */}
      {dragging && (
        <div className="drop-overlay active">
          <div className="drop-overlay-icon">📁</div>
          <div className="drop-overlay-text">DROP FILE</div>
        </div>
      )}
    </div>
  );
}
