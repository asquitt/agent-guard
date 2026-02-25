'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import type { AuthUser, AuthOrganization } from '@/types';
import {
  loginApi,
  verifyMfaLoginApi,
  registerApi,
  getMeApi,
  logoutApi,
} from '@/lib/api';
import { ApiError, tryRefreshToken } from '@/lib/api/client';

/** Thrown when login requires MFA verification. */
export class MfaRequiredError extends Error {
  constructor(public mfaToken: string) {
    super('MFA verification required');
    this.name = 'MfaRequiredError';
  }
}

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes of inactivity

interface AuthState {
  user: AuthUser | null;
  organization: AuthOrganization | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  verifyMfaLogin: (mfaToken: string, code: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    fullName: string,
    orgName: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'accessToken';
const REFRESH_KEY = 'refreshToken';

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

function storeTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    organization: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const fetchMe = useCallback(async () => {
    try {
      const me = await getMeApi();
      setState({
        user: me.user,
        organization: me.organization,
        isLoading: false,
        isAuthenticated: true,
      });
    } catch (err) {
      // Try refresh if access token expired — delegate to shared tryRefreshToken
      if (err instanceof ApiError && err.status === 401) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
          try {
            const me = await getMeApi();
            setState({
              user: me.user,
              organization: me.organization,
              isLoading: false,
              isAuthenticated: true,
            });
            return;
          } catch {
            // Retry also failed — clear everything
          }
        }
      }
      clearTokens();
      setState({
        user: null,
        organization: null,
        isLoading: false,
        isAuthenticated: false,
      });
    }
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (token) {
      fetchMe();
    } else {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, [fetchMe]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await loginApi(email, password);
      if (response.mfa_required && response.mfa_token) {
        throw new MfaRequiredError(response.mfa_token);
      }
      if (response.access_token && response.refresh_token) {
        storeTokens(response.access_token, response.refresh_token);
        await fetchMe();
      }
    },
    [fetchMe],
  );

  const verifyMfaLogin = useCallback(
    async (mfaToken: string, code: string) => {
      const tokens = await verifyMfaLoginApi(mfaToken, code);
      storeTokens(tokens.access_token, tokens.refresh_token);
      await fetchMe();
    },
    [fetchMe],
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      fullName: string,
      orgName: string,
    ) => {
      const tokens = await registerApi(email, password, fullName, orgName);
      storeTokens(tokens.access_token, tokens.refresh_token);
      await fetchMe();
    },
    [fetchMe],
  );

  const logout = useCallback(async () => {
    try {
      await logoutApi();
    } catch {
      // Ignore — clear tokens regardless
    }
    clearTokens();
    setState({
      user: null,
      organization: null,
      isLoading: false,
      isAuthenticated: false,
    });
  }, []);

  // Session inactivity timeout — auto-logout after 30 min idle
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!state.isAuthenticated) return;

    function resetTimer() {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => {
        logout();
      }, SESSION_TIMEOUT_MS);
    }

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'] as const;
    events.forEach((e) => document.addEventListener(e, resetTimer));
    resetTimer();

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      events.forEach((e) => document.removeEventListener(e, resetTimer));
    };
  }, [state.isAuthenticated, logout]);

  const value = useMemo(
    () => ({ ...state, login, verifyMfaLogin, register, logout, fetchMe }),
    [state, login, verifyMfaLogin, register, logout, fetchMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
