/**
 * Контекст авторизации.
 * Хранит текущий профиль пользователя и предоставляет методы входа/выхода.
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import type { ProfileResponse } from '../api/types';
import { authApi, profileApi } from '../api/client';

interface AuthContextValue {
  user: ProfileResponse | null;
  loading: boolean;
  login: (profileId: string) => Promise<void>;
  register: (name: string) => Promise<void>;
  logout: () => void;
  updateUser: (data: Partial<ProfileResponse>) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const STORAGE_KEY = 'alice_user_id';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<ProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // При монтировании — пробуем восстановить сессию из localStorage
  useEffect(() => {
    const savedId = localStorage.getItem(STORAGE_KEY);
    if (savedId) {
      profileApi
        .get(savedId)
        .then(setUser)
        .catch(() => localStorage.removeItem(STORAGE_KEY))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (profileId: string) => {
    const profile = await profileApi.get(profileId);
    setUser(profile);
    localStorage.setItem(STORAGE_KEY, profile.id);
  }, []);

  const register = useCallback(async (name: string) => {
    const profile = await authApi.register({
      name,
      disability_type: 'none',
      interaction_mode: 'both',
      preferences: {},
    });
    setUser(profile);
    localStorage.setItem(STORAGE_KEY, profile.id);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const updateUser = useCallback(
    async (data: Partial<ProfileResponse>) => {
      if (!user) return;
      const updated = await profileApi.update(user.id, data);
      setUser(updated);
    },
    [user],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
