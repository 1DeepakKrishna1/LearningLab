// Zustand auth store. Holds the current user and exposes login/logout.
import { create } from 'zustand';
import { api, tokenStore } from '../api/client';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  loadMe: () => Promise<void>;
  hasRole: (...roles: string[]) => boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: false,
  initialized: false,

  async login(email, password) {
    set({ loading: true });
    try {
      const form = new URLSearchParams({ username: email, password });
      const resp = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      tokenStore.set(resp.data.access_token, resp.data.refresh_token);
      await get().loadMe();
    } finally {
      set({ loading: false });
    }
  },

  async logout() {
    try {
      await api.post('/auth/logout', { refresh_token: tokenStore.refresh });
    } catch {
      /* ignore */
    }
    tokenStore.clear();
    set({ user: null });
  },

  async loadMe() {
    if (!tokenStore.access) {
      set({ initialized: true });
      return;
    }
    try {
      const resp = await api.get<User>('/auth/me');
      set({ user: resp.data, initialized: true });
    } catch {
      tokenStore.clear();
      set({ user: null, initialized: true });
    }
  },

  hasRole(...roles) {
    const user = get().user;
    if (!user) return false;
    return user.roles.some((r) => roles.includes(r.name));
  },
}));
