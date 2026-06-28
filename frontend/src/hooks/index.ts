import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { matchesApi, predictionsApi, leaderboardApi, configApi } from "@/api";
import type { MatchPhase, MatchStatus } from "@/types";

// ── CONFIG ────────────────────────────────────────────────────────────────────

export const useTeamsConfig = () =>
  useQuery({
    queryKey: ["config", "teams"],
    queryFn:  configApi.getTeams,
    staleTime: Infinity,
  });

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

// ── LEADERBOARD ───────────────────────────────────────────────────────────────

export const useLeaderboard = () =>
  useQuery({
    queryKey: ["leaderboard"],
    queryFn:  leaderboardApi.get,
    refetchInterval: 60_000, // refresca cada minuto (el backend puntúa al instante tras el FT; el timer de 30 min es respaldo)
  });
