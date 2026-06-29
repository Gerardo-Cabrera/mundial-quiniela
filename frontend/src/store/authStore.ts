import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";
import apiClient from "@/api/client";
import { AUTH_STORAGE_KEY } from "@/config";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { data } = await apiClient.post("/api/auth/login", { email, password });
        set({ user: data.user, token: data.access_token, isAuthenticated: true });
      },

      changePassword: async (currentPassword, newPassword) => {
        const { data } = await apiClient.post("/api/auth/change-password", {
          current_password: currentPassword,
          new_password: newPassword,
        });
        // Respuesta = UserOut actualizado (must_change_password ya en false).
        set({ user: data });
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: AUTH_STORAGE_KEY,
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);
