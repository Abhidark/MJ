import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';

export default function LoginScreen() {
  const { login } = useAuth();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!password.trim() || loading) return;
    setLoading(true);
    setError('');
    try {
      const result = await login(password);
      if (!result.success) {
        setError(result.message || 'Authentication failed');
        setPassword('');
        inputRef.current?.focus();
      }
    } catch (err) {
      setError(err.response?.data?.message || 'Connection failed');
      setPassword('');
      inputRef.current?.focus();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mj-login-overlay">
      <form className="mj-login-box" onSubmit={handleSubmit}>
        <div className="mj-login-orb" />
        <div className="mj-login-title">M J</div>
        <div className="mj-login-sub">Personal AI Assistant</div>
        <input
          ref={inputRef}
          type="password"
          className="mj-login-input"
          placeholder="Enter Password"
          autoComplete="off"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="mj-login-btn"
          disabled={loading || !password.trim()}
        >
          {loading ? 'Authenticating...' : 'Authenticate'}
        </button>
        <div className="mj-login-error">{error}</div>
        <div className="mj-login-hint">Default: jarvis</div>
      </form>
    </div>
  );
}
