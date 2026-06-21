// ── ENUMS ─────────────────────────────────────────────────────────────────────

export type MatchPhase =
  | "group_stage"
  | "round_of_32"
  | "round_of_16"
  | "quarter_finals"
  | "semi_finals"
  | "third_place"
  | "final";

export type MatchStatus = "scheduled" | "live" | "finished" | "postponed";

// ── MODELS ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  team_name: string;
  email: string;
  is_admin: boolean;
  created_at: string;
}

export interface Match {
  id: number;
  api_fixture_id: number;
  home_team: string;
  away_team: string;
  home_team_logo: string | null;
  away_team_logo: string | null;
  home_score: number | null;
  away_score: number | null;
  first_goal_team: string | null;
  first_goal_player_id: number | null;
  first_goal_player: string | null;
  phase: MatchPhase;
  status: MatchStatus;
  match_date: string;
}

export interface Player {
  api_player_id: number;
  name: string;
  team_name: string;
  position: string | null;
}

export interface Prediction {
  id: number;
  match_id: number;
  predicted_home: number;
  predicted_away: number;
  first_goal_player_id: number | null;
  first_goal_player: string | null;
  points_earned: number;
  is_calculated: boolean;
  match: Match;
}

export interface LeaderboardEntry {
  rank: number;
  team_name: string;
  total_points: number;
  predictions_count: number;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

// Las etiquetas visibles de fases y estados viven en los archivos de traducción
// (`i18n/locales/*.json`, claves `phase.*` / `status.*`), no aquí.

// ── HELPERS ─────────────────────────────────────────────────────────────────

/**
 * Indica si el pronóstico de primer goleador acertó. Compara por id de jugador
 * (igual que el scoring del backend) para evitar la ambigüedad de nombres.
 */
export function isFirstGoalHit(
  prediction: Pick<Prediction, "first_goal_player_id">,
  match: Pick<Match, "first_goal_player_id">,
): boolean {
  return (
    prediction.first_goal_player_id != null &&
    match.first_goal_player_id != null &&
    prediction.first_goal_player_id === match.first_goal_player_id
  );
}

// Cierre de pronósticos: 1 h antes del primer partido del día (la jornada).
const PREDICTION_LEAD_MS = 60 * 60 * 1000;

export interface MatchDay {
  day: string;          // clave yyyy-MM-dd (fecha local del navegador)
  matches: Match[];     // ordenados por hora de inicio
  firstKickoff: number; // ms del primer partido del día
  open: boolean;        // jornada aún abierta para pronosticar
}

/**
 * Agrupa partidos por día (fecha local) ordenados ascendente y marca si la
 * jornada sigue abierta. Fuente única usada por las vistas de Partidos y
 * Resultados (evita duplicar el agrupado y la regla de cierre).
 */
export function groupMatchesByDay(matches: Match[]): MatchDay[] {
  const byDay = new Map<string, Match[]>();
  for (const m of matches) {
    const d = new Date(m.match_date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const list = byDay.get(key);
    if (list) list.push(m);
    else byDay.set(key, [m]);
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, list]) => {
      const sorted = [...list].sort(
        (x, y) => +new Date(x.match_date) - +new Date(y.match_date),
      );
      const firstKickoff = +new Date(sorted[0].match_date);
      return { day, matches: sorted, firstKickoff, open: Date.now() < firstKickoff - PREDICTION_LEAD_MS };
    });
}

