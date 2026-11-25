import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import { loginRequest } from '../api/auth';
import {
  clearSession,
  loadSession,
  saveSession,
  type AuthUser,
} from '../storage/secureStorage';

type AuthContextValue = {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function tokenIsUnexpired(token: string): boolean {
  try {
    const payloadPart = token.split('.')[1];

    if (!payloadPart) {
      return false;
    }

    const base64 = payloadPart
      .replace(/-/g, '+')
      .replace(/_/g, '/')
      .padEnd(Math.ceil(payloadPart.length / 4) * 4, '=');

    const payload = JSON.parse(atob(base64)) as { exp?: number };

    return typeof payload.exp === 'number' &&
      payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      try {
        const session = await loadSession();

        if (
          session &&
          session.user.role === 'salesman' &&
          tokenIsUnexpired(session.token)
        ) {
          if (active) {
            setUser(session.user);
          }
        } else {
          await clearSession();
        }
      } catch {
        await clearSession();
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email.trim(), password);

    // Save only after the backend confirms a valid Salesman login.
    await saveSession(result.token, result.user);
    setUser(result.user);
  }, []);

  const logout = useCallback(async () => {
    await clearSession();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }

  return context;
}
