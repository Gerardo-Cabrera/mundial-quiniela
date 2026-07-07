import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import toast from "react-hot-toast";
import { matchesApi, predictionsApi, leaderboardApi, matchdaysApi, statsApi, configApi } from "@/api";
import { useAuthStore } from "@/store/authStore";
import { SESSION_IDLE_MS, LAST_ACTIVITY_KEY } from "@/config";
import type { MatchPhase, MatchStatus } from "@/types";

// ── CONFIG ────────────────────────────────────────────────────────────────────

export const useTeamsConfig = () =>
  useQuery({
    queryKey: ["config", "teams"],
    queryFn:  configApi.getTeams,
    staleTime: Infinity,
  });

// Ajustes globales (interruptor de pronósticos tardíos). Refresco periódico para que
// el cambio del admin llegue a los demás usuarios.
export const useSettings = () =>
  useQuery({
    queryKey: ["config", "settings"],
    queryFn:  configApi.getSettings,
    refetchInterval: 60_000,
  });

export const useSetLatePredictions = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: configApi.setLatePredictions,
    onSuccess: (data) => qc.setQueryData(["config", "settings"], data),
  });
};

// ── MATCHES ───────────────────────────────────────────────────────────────────

export const useMatches = (filters?: { phase?: MatchPhase; status?: MatchStatus }) =>
  useQuery({
    queryKey: ["matches", filters],
    queryFn:  () => matchesApi.getAll(filters),
    refetchInterval: 60_000, // refresca cada minuto
  });

export const useMatch = (id: number) =>
  useQuery({
    queryKey: ["matches", id],
    queryFn:  () => matchesApi.getOne(id),
    enabled:  !!id,
  });

// Plantillas de los dos equipos del partido (para elegir el primer goleador).
export const useMatchPlayers = (id: number, enabled = true) =>
  useQuery({
    queryKey: ["matches", id, "players"],
    queryFn:  () => matchesApi.getPlayers(id),
    enabled:  !!id && enabled,
    staleTime: 5 * 60_000,
  });

// ── PREDICTIONS ───────────────────────────────────────────────────────────────

export const useMyPredictions = () =>
  useQuery({
    queryKey: ["predictions", "mine"],
    queryFn:  predictionsApi.getMine,
  });

// Pronósticos (solo de partidos iniciados/finalizados) de otro participante.
export const useUserPredictions = (userId: number | null) =>
  useQuery({
    queryKey: ["predictions", "user", userId],
    queryFn:  () => predictionsApi.getForUser(userId!),
    enabled:  userId != null,
  });

export const useSavePrediction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.save,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["predictions"] });
    },
  });
};

export const useDeletePrediction = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["predictions"] });
    },
  });
};

// Admin: backfill. La carga puede recalcular puntos de partidos ya finalizados, así
// que se refrescan las vistas derivadas.
export const useBackfill = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: predictionsApi.backfill,
    onSuccess: () =>
      ["leaderboard", "matchdays", "stats", "predictions"].forEach((k) =>
        qc.invalidateQueries({ queryKey: [k] })),
  });
};

// ── LEADERBOARD ───────────────────────────────────────────────────────────────

export const useLeaderboard = () =>
  useQuery({
    queryKey: ["leaderboard"],
    queryFn:  leaderboardApi.get,
    refetchInterval: 60_000, // refresca cada minuto (el backend puntúa al instante tras el FT; el timer de 30 min es respaldo)
  });

// ── JORNADA / MVPs ──────────────────────────────────────────────────────────────

// Un solo endpoint alimenta ambas vistas (puntos por jornada + MVPs).
export const useMatchdays = () =>
  useQuery({
    queryKey: ["matchdays"],
    queryFn:  matchdaysApi.get,
    refetchInterval: 60_000,
  });

// Aciertos: primer gol + marcador exacto (un solo endpoint).
export const useStats = () =>
  useQuery({
    queryKey: ["stats"],
    queryFn:  statsApi.get,
    refetchInterval: 60_000,
  });

// ── SESIÓN ────────────────────────────────────────────────────────────────────

/**
 * Cierra la sesión tras SESSION_IDLE_MS sin **interacción del usuario**. No cuenta
 * el tráfico de fondo (el polling de 60 s mantendría la sesión viva para siempre),
 * solo eventos de puntero/teclado/scroll. La última actividad se persiste, así que
 * también se aplica al reabrir la app tras el periodo de inactividad. Se monta una
 * sola vez en el layout autenticado.
 */
export const useInactivityLogout = () => {
  const { isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    if (!isAuthenticated) return;

    const bump = () => localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    const enforce = (): boolean => {
      const last = Number(localStorage.getItem(LAST_ACTIVITY_KEY) || Date.now());
      if (Date.now() - last < SESSION_IDLE_MS) return false;
      localStorage.removeItem(LAST_ACTIVITY_KEY);
      logout();
      navigate("/login");
      toast(t("auth.sessionExpired"), { icon: "🔒" });
      return true;
    };

    if (!localStorage.getItem(LAST_ACTIVITY_KEY)) bump();
    if (enforce()) return; // reabierta tras el periodo de inactividad

    // Throttle: registrar actividad como mucho cada 30 s (evita escribir en cada
    // scroll/pointermove). Antes de registrar, comprueba caducidad: así volver a una
    // pestaña ya vencida cierra la sesión en vez de revivirla.
    let lastBump = 0;
    const onActivity = () => {
      if (enforce()) return;
      const now = Date.now();
      if (now - lastBump > 30_000) { lastBump = now; bump(); }
    };
    const events = ["pointerdown", "keydown", "scroll", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, onActivity, { passive: true }));
    document.addEventListener("visibilitychange", onActivity);
    const id = window.setInterval(enforce, 30_000);

    return () => {
      clearInterval(id);
      events.forEach((e) => window.removeEventListener(e, onActivity));
      document.removeEventListener("visibilitychange", onActivity);
    };
  }, [isAuthenticated, logout, navigate, t]);
};
