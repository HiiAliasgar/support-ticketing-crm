import { createContext, useContext, useEffect, useState } from "react";
import { currentUser, getToken, login as apiLogin, logout as apiLogout, setToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = getToken();
    if (!token) {
      setReady(true);
      return;
    }
    currentUser()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => setToken(null))
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (username, password) => {
    const result = await apiLogin(username, password);
    setToken(result.token);
    setUser(result.user);
    return result.user;
  };

  const logout = async () => {
    await apiLogout().catch(() => ({}));
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{ user, ready, isAdmin: user?.role === "admin", login, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}