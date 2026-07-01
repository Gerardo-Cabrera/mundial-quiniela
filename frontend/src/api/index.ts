import apiClient from "@/api/client";
import type {
  Match, Player, Prediction, LeaderboardEntry,
  MatchPhase, MatchStatus,
} from "@/types";

// ── MATCHES ───────────────────────────────────────────────────────────────────

export const matchesApi = {
  getAll: async (params?: { phase?: MatchPhase; status?: MatchStatus }): Promise<Match[]> => {
    const { data } = await apiClient.get("/api/matches", { params });
    return data;
  },
  getOne: async (id: number): Promise<Match> => {
    const { data } = await apiClient.get(`/api/matches/${id}`);
    return data;
  },
  getPlayers: async (id: number): Promise<Player[]> => {
    const { data } = await apiClient.get(`/api/matches/${id}/players`);
    return data;
  },
};

// ── PREDICTIONS ───────────────────────────────────────────────────────────────

export const predictionsApi = {
  getMine: async (): Promise<Prediction[]> => {
    const { data } = await apiClient.get("/api/predictions");
    return data;
  },
  // Pronósticos de otro participante: el backend solo devuelve los de partidos
  // ya iniciados o finalizados (nunca los de partidos por empezar).
  getForUser: async (userId: number): Promise<Prediction[]> => {
    const { data } = await apiClient.get(`/api/predictions/user/${userId}`);
    return data;
  },
  save: async (payload: {
    match_id: number;
    predicted_home: number;
    predicted_away: number;
    first_goal_player_id?: number;
  }): Promise<Prediction> => {
    const { data } = await apiClient.post("/api/predictions", payload);
    return data;
  },
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/predictions/${id}`);
  },
};

// ── LEADERBOARD ───────────────────────────────────────────────────────────────

export const leaderboardApi = {
  get: async (): Promise<LeaderboardEntry[]> => {
    const { data } = await apiClient.get("/api/leaderboard");
    return data;
  },
};

// ── CONFIG ────────────────────────────────────────────────────────────────────

export const configApi = {
  getTeams: async (): Promise<{ allowed_teams: string[]; wc_teams: string[] }> => {
    const { data } = await apiClient.get("/api/config/teams");
    return data;
  },
};
