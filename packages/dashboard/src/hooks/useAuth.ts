import { useState, useEffect, useCallback } from "react";

interface AuthUser {
  token: string;
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
}

const STORAGE_KEY = "resilience_auth";

export function useAuth() {
  const [auth, setAuth] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as AuthUser;
        if (parsed.token && parsed.user) {
          setAuth(parsed);
        }
      }
    } catch {
      localStorage.removeItem(STORAGE_KEY);
    } finally {
      setLoading(false);
    }
  }, []);

  const login = useCallback((token: string, user: AuthUser["user"]) => {
    const data: AuthUser = { token, user };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    setAuth(data);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }, []);

  return { auth, loading, login, logout };
}
