import { useState, useEffect, useCallback } from 'react';
import { weatherAPI } from '../../../services/api';

const WEATHER_ICONS = {
  sunny: '☀️', clear: '🌙', partlycloudy: '⛅', cloudy: '☁️',
  overcast: '☁️', mist: '🌫️', fog: '🌫️', rain: '🌧️',
  lightrain: '🌦️', heavyrain: '🌧️', snow: '❄️', thunder: '⛈️',
  drizzle: '🌦️', default: '🌤️',
};

function getIcon(text = '') {
  const t = text.toLowerCase().replace(/\s+/g, '');
  for (const [key, icon] of Object.entries(WEATHER_ICONS)) {
    if (t.includes(key)) return icon;
  }
  return WEATHER_ICONS.default;
}

export default function WeatherCard() {
  const [city, setCity] = useState(() => localStorage.getItem('mj_weather_city') || 'Gurgaon');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [input, setInput] = useState(city);

  const fetchWeather = useCallback(async (c) => {
    setLoading(true);
    setError('');
    try {
      const res = await weatherAPI.get(c);
      setData(res.data);
    } catch (e) {
      setError('Failed to load weather');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchWeather(city); }, [city, fetchWeather]);

  // Auto-refresh every 15 min
  useEffect(() => {
    const iv = setInterval(() => fetchWeather(city), 15 * 60 * 1000);
    return () => clearInterval(iv);
  }, [city, fetchWeather]);

  const handleCitySubmit = (e) => {
    e.preventDefault();
    const c = input.trim();
    if (c) {
      setCity(c);
      localStorage.setItem('mj_weather_city', c);
      setEditing(false);
    }
  };

  const current = data?.current;
  const forecast = data?.forecast || [];

  return (
    <div className="weather-card">
      {/* Header */}
      <div className="wc-header">
        <span className="wc-title">🌤️ WEATHER</span>
        <button className="wc-city-btn" onClick={() => setEditing(!editing)} title="Change city">
          {city} ✎
        </button>
      </div>

      {/* City input */}
      {editing && (
        <form onSubmit={handleCitySubmit} className="wc-city-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="City name..."
            className="wc-city-input"
            autoFocus
          />
          <button type="submit" className="wc-city-save">Go</button>
        </form>
      )}

      {/* Loading */}
      {loading && <div className="wc-loading">Loading weather...</div>}

      {/* Error */}
      {error && <div className="wc-error">{error}</div>}

      {/* Current weather */}
      {current && !loading && (
        <div className="wc-current">
          <div className="wc-temp-row">
            <span className="wc-icon">{getIcon(current.condition)}</span>
            <span className="wc-temp">{Math.round(current.temp_c)}°C</span>
          </div>
          <div className="wc-condition">{current.condition}</div>
          <div className="wc-details">
            <span>💧 {current.humidity}%</span>
            <span>💨 {current.wind_kph} km/h</span>
            <span>👁️ {current.vis_km || '--'} km</span>
          </div>
        </div>
      )}

      {/* Forecast */}
      {forecast.length > 0 && !loading && (
        <div className="wc-forecast">
          {forecast.slice(0, 3).map((day, i) => (
            <div key={i} className="wc-forecast-day">
              <div className="wc-fday">{i === 0 ? 'Today' : new Date(day.date).toLocaleDateString('en', { weekday: 'short' })}</div>
              <div className="wc-ficon">{getIcon(day.condition)}</div>
              <div className="wc-ftemp">
                <span className="wc-fhi">{Math.round(day.max_c)}°</span>
                <span className="wc-flo">{Math.round(day.min_c)}°</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
