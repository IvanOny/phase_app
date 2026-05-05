import { useState, useEffect, useCallback } from 'react';
import { loginApi } from '../api/client.js';

const TOKEN_KEY = 'phase-app-token';

/**
 * Parse the expiry segment out of a "expiry.hmac" token string.
 * Returns true if the token is present and not expired.
 * expiry == 0 means the token never expires.
 */
function isTokenValid(token) {
  if (!token) return false;
  try {
    const [expiryStr] = token.split('.');
    const expiry = parseInt(expiryStr, 10);
    if (expiry === 0) return true; // non-expiring
    return Date.now() / 1000 < expiry;
  } catch {
    return false;
  }
}

/**
 * Auth hook. Stores the token in localStorage so it survives page refresh.
 * Call this once in App.jsx; pass login/logout/isAuthenticated down as props.
 *
 * Listens for the custom 'auth:logout' DOM event dispatched by apiFetch
 * when the server returns 401, so the UI reacts automatically.
 */
export function useAuth() {
  const [token, setToken] = useState(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    return isTokenValid(stored) ? stored : null;
  });

  // React to 401s fired from apiFetch (outside React tree)
  useEffect(() => {
    function handleForcedLogout() {
      setToken(null);
    }
    window.addEventListener('auth:logout', handleForcedLogout);
    return () => window.removeEventListener('auth:logout', handleForcedLogout);
  }, []);

  const login = useCallback(async (username, password) => {
    // loginApi throws on bad credentials — let the caller handle the error
    const newToken = await loginApi(username, password);
    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
  }, []);

  return {
    isAuthenticated: token !== null,
    login,
    logout,
  };
}
