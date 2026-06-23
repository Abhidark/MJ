import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI } from '@/services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('mj_auth_token'));
  const [authEnabled, setAuthEnabled] = useState(null); // null = loading
  const [checking, setChecking] = useState(true);

  const isAuthenticated = !!token;

  // Check backend auth status on mount
  const checkAuth = useCallback(async () => {
    try {
      const { data } = await authAPI.getStatus();
      setAuthEnabled(data.auth_enabled);
      // If auth disabled, no token needed
      if (!data.auth_enabled) {
        setChecking(false);
        return;
      }
      // If auth enabled but no token, user needs to login
      if (!token) {
        setChecking(false);
        return;
      }
      // Token exists — it will be validated by the interceptor on first API call
      setChecking(false);
    } catch {
      // Backend unreachable — skip auth
      setAuthEnabled(false);
      setChecking(false);
    }
  }, [token]);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Listen for 401 events from api.js interceptor
  useEffect(() => {
    const handler = () => {
      setToken(null);
      localStorage.removeItem('mj_auth_token');
    };
    window.addEventListener('auth:logout', handler);
    return () => window.removeEventListener('auth:logout', handler);
  }, []);

  const login = async (password) => {
    const { data } = await authAPI.login(password);
    if (data.success && data.token) {
      localStorage.setItem('mj_auth_token', data.token);
      setToken(data.token);
    }
    return data;
  };

  const logout = async () => {
    try { await authAPI.logout(); } catch { /* ok */ }
    localStorage.removeItem('mj_auth_token');
    setToken(null);
  };

  const changePassword = async (oldPwd, newPwd) => {
    const { data } = await authAPI.changePassword(oldPwd, newPwd);
    if (data.success) {
      // Server invalidates session on password change
      localStorage.removeItem('mj_auth_token');
      setToken(null);
    }
    return data;
  };

  const toggleAuth = async (enabled, password) => {
    const { data } = await authAPI.toggle(enabled, password);
    if (data.success) {
      setAuthEnabled(enabled);
    }
    return data;
  };

  // Show login screen if auth is enabled and user is not authenticated
  const needsLogin = authEnabled === true && !isAuthenticated;

  return (
    <AuthContext.Provider value={{
      token, isAuthenticated, authEnabled, checking,
      needsLogin, login, logout, changePassword, toggleAuth, checkAuth,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
