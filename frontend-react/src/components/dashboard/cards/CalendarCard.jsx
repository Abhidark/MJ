import { useState, useMemo } from 'react';

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

export default function CalendarCard() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());

  const calendarDays = useMemo(() => {
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const daysInPrev = new Date(year, month, 0).getDate();

    const days = [];

    // Previous month trailing days
    for (let i = firstDay - 1; i >= 0; i--) {
      days.push({ day: daysInPrev - i, current: false, today: false });
    }

    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
      const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
      days.push({ day: d, current: true, today: isToday });
    }

    // Next month leading days
    const remaining = 42 - days.length; // 6 rows
    for (let d = 1; d <= remaining; d++) {
      days.push({ day: d, current: false, today: false });
    }

    return days;
  }, [year, month, today]);

  const prevMonth = () => {
    if (month === 0) { setMonth(11); setYear(y => y - 1); }
    else setMonth(m => m - 1);
  };

  const nextMonth = () => {
    if (month === 11) { setMonth(0); setYear(y => y + 1); }
    else setMonth(m => m + 1);
  };

  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth());
  };

  return (
    <div className="cal-card">
      <div className="cal-header">
        <span className="cal-title">📅 CALENDAR</span>
      </div>

      {/* Month navigation */}
      <div className="cal-nav">
        <button className="cal-nav-btn" onClick={prevMonth}>◀</button>
        <span className="cal-month-label" onClick={goToday} title="Go to today">
          {MONTHS[month]} {year}
        </span>
        <button className="cal-nav-btn" onClick={nextMonth}>▶</button>
      </div>

      {/* Day headers */}
      <div className="cal-grid">
        {DAYS.map(d => (
          <div key={d} className="cal-day-header">{d}</div>
        ))}

        {/* Calendar days */}
        {calendarDays.map((d, i) => (
          <div
            key={i}
            className={`cal-day ${d.current ? '' : 'other-month'} ${d.today ? 'today' : ''}`}
          >
            {d.day}
          </div>
        ))}
      </div>
    </div>
  );
}
