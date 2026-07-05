import { createContext, useContext, useEffect, useState } from "react";
import api from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("ialloc_user");
    return raw ? JSON.parse(raw) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("ialloc_token");
    if (token && !user) {
      api
        .get("/auth/me")
        .then((r) => persist(token, r.data))
        .catch(() => logout())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persist(token, u) {
    localStorage.setItem("ialloc_token", token);
    localStorage.setItem("ialloc_user", JSON.stringify(u));
    setUser(u);
  }

  async function login(email, password) {
    const { data } = await api.post("/auth/login", { email, password });
    persist(data.access_token, data.user);
    return data.user;
  }

  async function register(payload) {
    const { data } = await api.post("/auth/register", payload);
    persist(data.access_token, data.user);
    return data.user;
  }

  function logout() {
    localStorage.removeItem("ialloc_token");
    localStorage.removeItem("ialloc_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
