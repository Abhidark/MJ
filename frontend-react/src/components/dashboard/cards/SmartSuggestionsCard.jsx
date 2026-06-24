/**
 * SmartSuggestionsCard — AI-generated contextual suggestion chips.
 */
import { useState, useEffect } from 'react';

const FALLBACK = [
  'Check system health',
  'Open VS Code',
  'What\'s the weather?',
  'Take a screenshot',
  'Tell me a joke',
  'Git status',
];

export default function SmartSuggestionsCard({ onAction }) {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/smart-suggestions')
      .then(r => r.json())
      .then(d => {
        setSuggestions(d.suggestions || FALLBACK);
        setLoading(false);
      })
      .catch(() => {
        setSuggestions(FALLBACK);
        setLoading(false);
      });
  }, []);

  return (
    <div className="smartsug-card">
      <div className="smartsug-header">
        <span>Smart Suggestions</span>
        <span className="live-dot-indicator" />
      </div>
      <div className="smartsug-chips">
        {loading ? (
          <span className="smartsug-loading">Loading suggestions...</span>
        ) : (
          suggestions.map((s, i) => (
            <button
              key={i}
              className="smartsug-chip"
              onClick={() => onAction && onAction(s)}
            >
              {s}
            </button>
          ))
        )}
      </div>
    </div>
  );
}
