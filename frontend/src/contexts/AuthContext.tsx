import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import client, { setAuthToken } from "../api/client";

type User = { id?: string; email?: string; role?: string } | null;

type AuthContextType = {
  user: User;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (token: string, user?: User) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const TOKEN_KEY = "ci_access_token";

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const stored = localStorage.getItem(TOKEN_KEY);
        if (stored) {
          setAuthToken(stored);
          setToken(stored);
        }
        const { data } = await client.get<{ sub: string; role?: string }>("/auth/me");
        setUser({ id: data.sub, role: data.role });
        setError(null);
      } catch (err: any) {
        // If token invalid or missing, ensure clean state
        localStorage.removeItem(TOKEN_KEY);
        setAuthToken(null);
        setUser(null);
        setError(err?.message || "Not authenticated");
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      error,
      login: (tok: string, usr?: User) => {
        setToken(tok);
        if (tok) {
          localStorage.setItem(TOKEN_KEY, tok);
          setAuthToken(tok);
        } else {
          localStorage.removeItem(TOKEN_KEY);
          setAuthToken(null);
        }
        setUser(usr || { role: "viewer" });
        setError(null);
      },
      logout: () => {
        localStorage.removeItem(TOKEN_KEY);
        setAuthToken(null);
        setToken(null);
        setUser(null);
        setError(null);
      },
    }),
    [error, loading, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
};
