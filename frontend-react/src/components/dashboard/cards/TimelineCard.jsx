/**
 * TimelineCard — shows recent activity feed: chats, tool calls, system events.
 * Fetches chat history from backend; shows system events locally.
 */
import { useState, useEffect } from 'react';
import { chatAPI, systemAPI } from '@/services/api';

const EVENT_TYPES = {
  chat: { icon: '💬', color: '#00d4ff', label: 'Chat' },
  tool: { icon: '🔧', color: '#00ff88', label: 'Tool' },
  system: { icon: '⚡', color: '#ffaa00', label: 'System' },
  voice: { icon: '🎙️', color: '#c8a0ff', label: 'Voice' },
  error: { icon: '⚠️', color: '#ff4444', label: 'Error' },
  login: { icon: '🔐', color: '#00ffcc', label: 'Auth' },
};

function timeAgo(date) {
  const now = Date.now();
  const diff = now - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function TimelineEvent({ event }) {
  const typeInfo = EVENT_TYPES[event.type] || EVENT_TYPES.system;
  return (
    <div className="timeline-event">
      <div className="timeline-dot" style={{ background: typeInfo.color }} />
      <div className="timeline-line" />
      <div className="timeline-body">
        <div className="timeline-header">
          <span className="timeline-icon">{typeInfo.icon}</span>
          <span className="timeline-label" style={{ color: typeInfo.color }}>{typeInfo.label}</span>
          <span className="timeline-time">{event.time}</span>
        </div>
        <div className="timeline-text">{event.text}</div>
      </div>
    </div>
  );
}

export default function TimelineCard() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    let mounted = true;
    async function fetchTimeline() {
      const timeline = [];

      try {
        // Fetch recent chats
        const chatsRes = await chatAPI.getChats();
        const chats = chatsRes?.data?.chats || chatsRes?.data || [];
        if (Array.isArray(chats)) {
          chats.slice(0, 5).forEach(chat => {
            timeline.push({
              type: 'chat',
              text: chat.title || chat.name || `Chat session`,
              time: chat.updated_at || chat.created_at ? timeAgo(chat.updated_at || chat.created_at) : 'Recent',
              ts: new Date(chat.updated_at || chat.created_at || Date.now()).getTime(),
            });
          });
        }
      } catch { /* offline */ }

      try {
        // Fetch system health
        const healthRes = await systemAPI.getHealth();
        const health = healthRes?.data;
        if (health) {
          timeline.push({
            type: 'system',
            text: `System ${health.status || 'checked'} — uptime: ${health.uptime || 'unknown'}`,
            time: 'Now',
            ts: Date.now(),
          });
        }
      } catch { /* offline */ }

      // Add startup event
      timeline.push({
        type: 'system',
        text: 'MJ Dashboard loaded',
        time: 'Session start',
        ts: Date.now() - 1000,
      });

      // Sort by timestamp desc
      timeline.sort((a, b) => (b.ts || 0) - (a.ts || 0));

      if (mounted) {
        setEvents(timeline);
        setLoading(false);
      }
    }

    fetchTimeline();
    const interval = setInterval(fetchTimeline, 30000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const filtered = filter === 'all'
    ? events
    : events.filter(e => e.type === filter);

  if (loading) {
    return <div className="timeline-loading">Loading activity...</div>;
  }

  return (
    <div className="timeline-content">
      {/* Filter pills */}
      <div className="timeline-filters">
        {['all', 'chat', 'system', 'tool'].map(f => (
          <button
            key={f}
            className={`timeline-filter-btn${filter === f ? ' active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'all' ? 'All' : EVENT_TYPES[f]?.label || f}
          </button>
        ))}
      </div>

      {/* Events */}
      <div className="timeline-list">
        {filtered.length === 0 ? (
          <div className="timeline-empty">No activity yet</div>
        ) : (
          filtered.slice(0, 8).map((ev, i) => <TimelineEvent key={i} event={ev} />)
        )}
      </div>
    </div>
  );
}
