import { createContext, useContext, useEffect, useState } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("vizhi_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = async (username, password) => {
    setLoading(true);
    try {
      const { data } = await client.post("/auth/login", { username, password });
      localStorage.setItem("vizhi_access", data.access_token);
      localStorage.setItem("vizhi_refresh", data.refresh_token);
      const u = {
        username,
        role: data.role,
        scope_value: data.scope_value,
        full_name: data.full_name,
      };
      localStorage.setItem("vizhi_user", JSON.stringify(u));
      setUser(u);
      return u;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("vizhi_access");
    localStorage.removeItem("vizhi_refresh");
    localStorage.removeItem("vizhi_user");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
