import { create } from "zustand";
import { Api, tokenStore } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  restore: () => Promise<void>;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  loading: true,
  login: async (email, password) => {
    const res = await Api.login(email, password);
    tokenStore.set(res.access_token);
    set({ user: res.user });
  },
  logout: () => {
    tokenStore.clear();
    set({ user: null });
  },
  restore: async () => {
    if (!tokenStore.get()) {
      set({ loading: false });
      return;
    }
    try {
      const user = await Api.me();
      set({ user, loading: false });
    } catch {
      tokenStore.clear();
      set({ user: null, loading: false });
    }
  },
}));
