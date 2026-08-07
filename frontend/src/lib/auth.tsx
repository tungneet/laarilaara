"use client";

/**
 * Client-side auth state: bearer tokens + current account.
 *
 * Tokens live in localStorage for local development simplicity. Before
 * production hardening, move refresh-token custody to httpOnly cookies
 * (tracked in the security backlog — localStorage is XSS-readable).
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { api, ApiError, setAccessToken } from "@/lib/api";

const STORAGE_KEY = "ll-auth";

export interface Account {
  id: string;
  email: string | null;
  phone: string | null;
  display_name: string | null;
  gender: string | null;
  status: string;
  tier: string;
  locale: string;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

interface LoginResponse extends TokenPair {
  expires_in: number;
}

function loadTokens(): TokenPair | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as TokenPair) : null;
  } catch {
    return null;
  }
}

function saveTokens(tokens: TokenPair | null) {
  try {
    if (tokens) localStorage.setItem(STORAGE_KEY, JSON.stringify(tokens));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode */
  }
}

interface AuthContextValue {
  account: Account | null;
  /** True while the persisted session is being restored on first load. */
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  startPhoneAuth: (phone: string) => Promise<void>;
  verifyPhoneAndLogin: (challengeId: string, code: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string, gender?: string) => Promise<void>;
  verifyChallenge: (challengeId: string, code: string) => Promise<void>;
  signOut: () => Promise<void>;
  signOutAll: () => Promise<void>;
  /** Re-fetch /v1/me and update the shared account object (e.g. after a settings save). */
  refreshAccount: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);

  // Restore a persisted session: try /v1/me, refresh once on 401.
  useEffect(() => {
    let cancelled = false;

    async function restore() {
      const tokens = loadTokens();
      if (!tokens) {
        setLoading(false);
        return;
      }
      setAccessToken(tokens.access_token);
      try {
        const me = await api.get<Account>("/v1/me");
        if (!cancelled) setAccount(me);
      } catch {
        try {
          const next = await api.post<LoginResponse>("/v1/auth/refresh", {
            refresh_token: tokens.refresh_token,
          });
          saveTokens(next);
          setAccessToken(next.access_token);
          const me = await api.get<Account>("/v1/me");
          if (!cancelled) setAccount(me);
        } catch {
          saveTokens(null);
          setAccessToken(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    const tokens = await api.post<LoginResponse>("/v1/auth/login", {
      email,
      password,
    });
    saveTokens(tokens);
    setAccessToken(tokens.access_token);
    setAccount(await api.get<Account>("/v1/me"));
  }, []);

  const loginWithGoogle = useCallback(async (idToken: string) => {
    const tokens = await api.post<LoginResponse>("/v1/auth/oauth/google", {
      id_token: idToken,
    });
    saveTokens(tokens);
    setAccessToken(tokens.access_token);
    setAccount(await api.get<Account>("/v1/me"));
  }, []);

  const startPhoneAuth = useCallback(async (phone: string) => {
    const response = await api.post<{ challenge_id: string }>("/v1/auth/phone/start", { phone });
    return response.challenge_id;
  }, []);

  const verifyPhoneAndLogin = useCallback(async (challengeId: string, code: string) => {
    const tokens = await api.post<LoginResponse>("/v1/auth/phone/verify", {
      challenge_id: challengeId,
      code,
    });
    saveTokens(tokens);
    setAccessToken(tokens.access_token);
    setAccount(await api.get<Account>("/v1/me"));
  }, []);

  const register = useCallback(async (email: string, password: string, displayName?: string, gender?: string) => {
    const response = await api.post<{ challenge_id: string }>("/v1/auth/register", {
      email,
      password,
      display_name: displayName || undefined,
      gender: gender || undefined,
    });
    return response.challenge_id;
  }, []);

  const verifyChallenge = useCallback(
    async (challengeId: string, code: string) => {
      await api.post(`/v1/auth/challenges/${challengeId}/verify`, { code });
    },
    [],
  );

  const signOut = useCallback(async () => {
    try {
      await api.post("/v1/auth/logout");
    } catch {
      /* already invalid server-side — clear locally regardless */
    }
    saveTokens(null);
    setAccessToken(null);
    setAccount(null);
  }, []);

  const signOutAll = useCallback(async () => {
    try {
      await api.post("/v1/auth/logout-all");
    } catch {
      /* already invalid server-side — clear locally regardless */
    }
    saveTokens(null);
    setAccessToken(null);
    setAccount(null);
  }, []);

  const refreshAccount = useCallback(async () => {
    setAccount(await api.get<Account>("/v1/me"));
  }, []);

  const value = useMemo(
    () => ({
      account,
      loading,
      signIn,
      loginWithGoogle,
      startPhoneAuth,
      verifyPhoneAndLogin,
      register,
      verifyChallenge,
      signOut,
      signOutAll,
      refreshAccount,
    }),
    [
      account,
      loading,
      signIn,
      loginWithGoogle,
      startPhoneAuth,
      verifyPhoneAndLogin,
      register,
      verifyChallenge,
      signOut,
      signOutAll,
      refreshAccount,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}

/** Human-readable message for a failed auth call. */
export function authErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    switch (err.code) {
      case "INVALID_CREDENTIALS":
        return "Incorrect email or password.";
      case "ACCOUNT_NOT_VERIFIED":
        return "This account's email is not verified yet.";
      case "GOOGLE_TOKEN_INVALID":
        return "Google sign-in failed. Please try again.";
      case "PHONE_NUMBER_INVALID":
        return "That doesn't look like a valid phone number. Use the format +14155550123.";
      case "CHALLENGE_INVALID":
        return "That verification code is invalid or has expired.";
      case "VALIDATION_FAILED":
        return err.problem?.errors?.[0]?.message ?? "Please check your input.";
      case "MESSAGE_CONTENT_BLOCKED":
        return "This message was blocked by our content safety check. Please rephrase it.";
      case "NARRATIVE_CONTENT_BLOCKED":
        return "This text was blocked by our content safety check. Please rephrase it.";
      default:
        return err.message;
    }
  }
  return "Something went wrong. Is the API server running?";
}
