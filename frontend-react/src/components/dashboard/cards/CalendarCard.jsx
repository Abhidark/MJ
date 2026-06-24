/**
 * CalendarCard — month calendar with event management.
 * Events stored in localStorage via calendarAPI.
 * Click a date to view/add events. Dates with events show indicator dots.
 */
import { useState, useMemo, useCallback } from 'react';
import { calendarAPI } from '@/services/api';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

const EVENT_COLORS = [
  { label: 'Cyan', value: '#00d4ff' },
  { label: 'Green', value: '#00ff88' },
  { label: 'Orange', value: '#ffaa00' },
  { label: 'Red', value: '#ff4444' },
  { label: 'Purple', value: '#c8a0ff' },
];

function dateKey(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
}

function EventForm({ date, onAdd, onClose }) {
  const [title, setTitle] = useState('');
  const [time, setTime] = useState('09:00');
  const [color, setColor] = useState(EVENT_COLORS[0].value);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) return;
    onAdd({ date, title: title.trim(), time, color });
    setTitle('');
  };

  return (
    <form className="cal-event-form" onSubmit={handleSubmit}>
      <input
        className="cal-event-input"
        placeholder="Event title..."
        value={title}
        onChange={e => setTitle(e.target.value)}
        autoFocus
      />
      <input
        className="cal-event-time"
        type="time"
        value={time}
        onChange={e => setTime(e.target.value)}
      />
      <div className="cal-color-picks">
        {EVENT_COLORS.map(c => (
          <button
            key={c.value}
            type="button"
            className={`cal-color-dot${color === c.value ? ' active' : ''}`}
            style={{ background: c.value }}
            onClick={() => setColor(c.value)}
          />
        ))}
      </div>
      <div className="cal-event-actions">
        <button type="submit" className="cal-event-save">+ Add</button>
        <button type="button" className="cal-event-cancel" onClick={onClose}>Cancel</button>
      </div>
    </form>
  );
}

function EventList({ events, onDelete }) {
  if (events.length === 0) {
    return <div className="cal-no-events">No events</div>;
  }
  return (
    <div className="cal-events-list">
      {events
        .sort((a, b) => (a.time || '').localeCompare(b.time || ''))
        .map(ev => (
          <div key={ev.id} className="cal-event-item">
            <span className="cal-event-dot" style={{ background: ev.color || '#00d4ff' }} />
            <span className="cal-event-time-label">{ev.time || '--:--'}</span>
            <span className="cal-event-title">{ev.title}</span>
            <button className="cal-event-del" onClick={() => onDelete(ev.id)}>✕</button>
          </div>
        ))
      }
    </div>
  );
}

export default function CalendarCard() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [selectedDate, setSelectedDate] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [eventVersion, setEventVersion] = useState(0); // trigger re-render on event change

  const allEvents = useMemo(() => calendarAPI.getEvents(), [eventVersion]);

  const eventDates = useMemo(() => {
    const map = {};
    allEvents.forEach(ev => {
      if (!map[ev.date]) map[ev.date] = [];
      map[ev.date].push(ev);
    });
    return map;
  }, [allEvents]);

  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();
    const days = [];

    for (let i = firstDay - 1; i >= 0; i--) {
      const pm = month === 0 ? 11 : month - 1;
      const py = month === 0 ? year - 1 : year;
      days.push({ day: daysInPrev - i, current: false, today: false, key: dateKey(py, pm, daysInPrev - i) });
    }
    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
      days.push({ day: d, current: true, today: isToday, key: dateKey(year, month, d) });
    }
    const remaining = 42 - days.length;
    const nm = month === 11 ? 0 : month + 1;
    const ny = month === 11 ? year + 1 : year;
    for (let d = 1; d <= remaining; d++) {
      days.push({ day: d, current: false, today: false, key: dateKey(ny, nm, d) });
    }
    return days;
  }, [year, month, today]);

  const prevMonth = () => {
    setSelectedDate(null); setShowForm(false);
    if (month === 0) { setMonth(11); setYear(y => y - 1); }
    else setMonth(m => m - 1);
  };

  const nextMonth = () => {
    setSelectedDate(null); setShowForm(false);
    if (month === 11) { setMonth(0); setYear(y => y + 1); }
    else setMonth(m => m + 1);
  };

  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
    setSelectedDate(dateKey(today.getFullYear(), today.getMonth(), today.getDate()));
  };

  const handleDayClick = useCallback((dayObj) => {
    setSelectedDate(prev => prev === dayObj.key ? null : dayObj.key);
    setShowForm(false);
  }, []);

  const handleAddEvent = useCallback((event) => {
    calendarAPI.addEvent(event);
    setEventVersion(v => v + 1);
    setShowForm(false);
  }, []);

  const handleDeleteEvent = useCallback((id) => {
    calendarAPI.deleteEvent(id);
    setEventVersion(v => v + 1);
  }, []);

  const selectedEvents = selectedDate ? (eventDates[selectedDate] || []) : [];
  const selectedLabel = selectedDate
    ? new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
    : '';

  return (
    <div className="cal-card">
      <div className="cal-header">
        <span className="cal-title">📅 CALENDAR</span>
        <span className="cal-event-count">{allEvents.length} events</span>
      </div>

      <div className="cal-nav">
        <button className="cal-nav-btn" onClick={prevMonth}>◀</button>
        <span className="cal-month-label" onClick={goToday} title="Go to today">
          {MONTHS[month]} {year}
        </span>
        <button className="cal-nav-btn" onClick={nextMonth}>▶</button>
      </div>

      <div className="cal-grid">
        {DAYS.map(d => (
          <div key={d} className="cal-day-header">{d}</div>
        ))}

        {calendarDays.map((d, i) => {
          const hasEvents = eventDates[d.key] && eventDates[d.key].length > 0;
          const isSelected = selectedDate === d.key;
          return (
            <div
              key={i}
              className={`cal-day ${d.current ? '' : 'other-month'} ${d.today ? 'today' : ''} ${isSelected ? 'selected' : ''}`}
              onClick={() => handleDayClick(d)}
            >
              {d.day}
              {hasEvents && <span className="cal-dot" style={{ background: eventDates[d.key][0].color || '#00d4ff' }} />}
            </div>
          );
        })}
      </div>

      {/* Selected date panel */}
      {selectedDate && (
        <div className="cal-selected-panel">
          <div className="cal-selected-header">
            <span className="cal-selected-date">{selectedLabel}</span>
            <button className="cal-add-btn" onClick={() => setShowForm(f => !f)}>
              {showForm ? '✕' : '+ Event'}
            </button>
          </div>

          {showForm && (
            <EventForm
              date={selectedDate}
              onAdd={handleAddEvent}
              onClose={() => setShowForm(false)}
            />
          )}

          <EventList events={selectedEvents} onDelete={handleDeleteEvent} />
        </div>
      )}
    </div>
  );
}
