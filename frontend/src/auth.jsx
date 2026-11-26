import { createContext, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { api, saveToken, token } from "./api";
const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function refresh() {
    const me = await api("/me");
    setUser(me);
    return me;
  }
  useEffect(() => {
    const expire = () => {
      setUser(null);
      setError("Сессия завершилась. Войдите снова.");
    };
    window.addEventListener("session-expired", expire);
    if (token())
      refresh()
        .catch((e) => setError(e.message))
        .finally(() => setLoading(false));
    else setLoading(false);
    return () => window.removeEventListener("session-expired", expire);
  }, []);
  async function login(accessToken) {
    saveToken(accessToken);
    await refresh();
    setError("");
  }
  async function logout() {
    await api("/auth/logout", { method: "POST" });
    saveToken(null);
    setUser(null);
  }
  return (
    <AuthContext.Provider
      value={{ user, loading, error, login, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function Protected({ children, moderator = false }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <p className="loading" role="status">
        Проверяем вход…
      </p>
    );
  if (!user)
    return (
      <Navigate
        to="/login"
        state={{ from: location.pathname + location.search }}
        replace
      />
    );
  if (moderator && user.role !== "moderator")
    return (
      <div className="empty">
        <h1>Этот раздел для модераторов</h1>
        <p>Ваш аккаунт не имеет доступа.</p>
      </div>
    );
  return children;
}
