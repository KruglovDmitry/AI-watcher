import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, setToken } from './api';

type AuthState = {
  username: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('watcher_token');
    if (!token) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then((user) => setUsername(user.username))
      .catch(() => setToken(null))
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      username,
      loading,
      login: async (loginUsername, password) => {
        const result = await api.login(loginUsername, password);
        setToken(result.access_token);
        setUsername(result.username);
      },
      logout: () => {
        setToken(null);
        setUsername(null);
      },
    }),
    [username, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('AuthProvider missing');
  return ctx;
}
