import { useState, useCallback, useMemo } from 'react';
import ProviderBadge from './ProviderBadge';

// --- Simple markdown-like renderer ---
// Handles: **bold**, *italic*, `inline code`, ```code blocks```, [links](url), headers, lists
// No external dependency -- keeps bundle small

function parseCodeBlocks(text) {
  const parts = [];
  const regex = /```(\w*)\n?([\s\S]*?)```/g;
  let lastIdx = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push({ type: 'text', content: text.slice(lastIdx, match.index) });
    }
    parts.push({ type: 'code', lang: match[1] || '', content: match[2].trimEnd() });
    lastIdx = match.index + match[0].length;
  }

  if (lastIdx < text.length) {
    parts.push({ type: 'text', content: text.slice(lastIdx) });
  }

  return parts.length > 0 ? parts : [{ type: 'text', content: text }];
}

function formatInlineText(text) {
  // Process line by line for headers and lists
  return text.split('\n').map((line, i) => {
    // Headers
    if (/^### /.test(line)) return <div key={i} className="md-h3">{processInline(line.slice(4))}</div>;
    if (/^## /.test(line)) return <div key={i} className="md-h2">{processInline(line.slice(3))}</div>;
    if (/^# /.test(line)) return <div key={i} className="md-h1">{processInline(line.slice(2))}</div>;
    // Bullet list
    if (/^[-*] /.test(line)) return <div key={i} className="md-li">* {processInline(line.slice(2))}</div>;
    // Numbered list
    if (/^\d+\. /.test(line)) return <div key={i} className="md-li">{processInline(line)}</div>;
    // Regular line
    if (line === '') return <div key={i} className="md-br" />;
    return <span key={i}>{processInline(line)}{'\n'}</span>;
  });
}

function processInline(text) {
  // Bold, italic, inline code, links
  const parts = [];
  const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`([^`]+)`)|(\[([^\]]+)\]\(([^)]+)\))/g;
  let lastIdx = 0;
  let match;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIdx) {
      parts.push(text.slice(lastIdx, match.index));
    }
    if (match[1]) parts.push(<strong key={key++}>{match[2]}</strong>);
    else if (match[3]) parts.push(<em key={key++}>{match[4]}</em>);
    else if (match[5]) parts.push(<code key={key++} className="md-inline-code">{match[6]}</code>);
    else if (match[7]) parts.push(<a key={key++} href={match[9]} target="_blank" rel="noopener noreferrer" className="md-link">{match[8]}</a>);
    lastIdx = match.index + match[0].length;
  }

  if (lastIdx < text.length) parts.push(text.slice(lastIdx));
  return parts.length > 0 ? parts : text;
}

// --- Code Block with copy ---
function CodeBlock({ lang, content }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [content]);

  return (
    <div className="msg-code-block">
      <div className="msg-code-header">
        <span className="msg-code-lang">{lang || 'code'}</span>
        <button className="msg-code-copy" onClick={handleCopy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="msg-code-pre"><code>{content}</code></pre>
    </div>
  );
}

// --- MAIN EXPORT ---
export default function ChatMessage({ message }) {
  const { role, content, timestamp, streaming, error, file, modelBadge, provider, images } = message;

  const isUser = role === 'user';

  const rendered = useMemo(() => {
    if (!content) return null;
    const blocks = parseCodeBlocks(content);
    return blocks.map((block, i) =>
      block.type === 'code'
        ? <CodeBlock key={i} lang={block.lang} content={block.content} />
        : <div key={i} className="msg-text-block">{formatInlineText(block.content)}</div>
    );
  }, [content]);

  return (
    <div className={`msg-row ${role}${error ? ' error' : ''}`}>
      <div className={`avatar ${isUser ? 'user-avatar' : 'mj-avatar'}`}>
        {isUser ? 'U' : 'MJ'}
      </div>
      <div className="msg-content">
        <div className={`msg ${role}${streaming && !content ? ' typing' : ''}`}>
          {streaming && !content && <span className="typing-dots">Thinking<span className="dots">...</span></span>}
          {rendered}
          {file && (
            <div className="file-badge">Attachment: {file.name}</div>
          )}
        </div>
        {images && images.length > 0 && (
          <div className="msg-images">
            {images.map((url, i) => (
              <img
                key={i}
                src={url}
                className="msg-image"
                alt="Generated"
                onClick={() => window.open(url, '_blank')}
              />
            ))}
          </div>
        )}
        <div className="timestamp">
          {timestamp}
          {modelBadge && (
            <span className="model-badge">
              <span className="mb-dot" />
              {modelBadge.split(':')[0]}
            </span>
          )}
          {!isUser && provider && <ProviderBadge provider={provider} />}
        </div>
      </div>
    </div>
  );
}
