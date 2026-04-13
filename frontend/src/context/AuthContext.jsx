// context/AuthContext.jsx — Estado global de autenticación
import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      authAPI.me()
        .then((res) => setUser(res.data))
        .catch(() => { localStorage.clear(); setUser(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await authAPI.login(email, password);
    const { access_token, role, user_id, full_name, habeas_data_accepted } = res.data;
    localStorage.setItem('token', access_token);
    const userData = { id: user_id, email, role, full_name, habeas_data_accepted };
    setUser(userData);
    return userData;
  };

  const logout = () => {
    localStorage.clear();
    setUser(null);
  };

  const acceptHabeasData = async () => {
    await authAPI.habeasData(true);
    setUser((prev) => ({ ...prev, habeas_data_accepted: true }));
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, acceptHabeasData }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
