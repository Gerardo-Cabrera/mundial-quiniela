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
  must_change_password: boolean;
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
  penalty_home: number | null;
  penalty_away: number | null;
  elapsed: number | null;
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
  user_id: number;
  team_name: string;
  total_points: number;
  predictions_count: number;
}

export interface Token {
  access_token: string;
  token_type: string;
  user: User;
}

// ── JORNADA / MVPs ──────────────────────────────────────────────────────────
export interface MatchdayUserPoints {
  user_id: number;
  team_name: string;
  points: number;
}
export interface MatchdayEntry {
  date: string;                 // "yyyy-MM-dd" (día en zona del torneo)
  entries: MatchdayUserPoints[]; // desc por puntos
  mvp_points: number;
  mvps: string[];               // equipo(s) MVP del día; vacío si nadie puntuó
}
export interface MvpRankEntry {
  team_name: string;
  count: number;
}
export interface MatchdaysSummary {
  days: MatchdayEntry[];        // cronológico ascendente
  mvp_ranking: MvpRankEntry[];  // desc por count
}

// ── ACIERTOS (Stats) ──────────────────────────────────────────────────────────
export interface UserCount {
  team_name: string;
  count: number;
}
export interface FirstGoalMatch {
  match_id: number;
  home_team: string;
  away_team: string;
  match_date: string;
  scorer: string | null;   // goleador real del primer gol
  hitters: string[];       // equipos que lo acertaron
}
export interface ScoreCount {
  score: string;           // "2-1"
  count: number;
}
export interface StatsSummary {
  first_goal_matches: FirstGoalMatch[];  // resueltos, más reciente primero
  first_goal_ranking: UserCount[];        // aciertos de primer gol por usuario (desc)
  top_scores: ScoreCount[];               // marcador(es) real(es) más repetido(s)
  exact_ranking: UserCount[];             // aciertos de marcador exacto por usuario (desc)
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

// Un partido "jugado" = en vivo o finalizado (ya empezó). Solo mira el estado; el
// marcador y el primer gol son nullables y se comprueban por separado donde se usan.
// Concepto único usado por las tarjetas y la vista de Resultados.
export const isMatchPlayed = (match: Pick<Match, "status">): boolean =>
  match.status === "live" || match.status === "finished";

/**
 * Convierte una fecha "yyyy-MM-dd" a un Date local al mediodía. El mediodía evita
 * el corrimiento de día que produciría parsear la fecha "pelada" como UTC.
 */
export const isoDayToDate = (iso: string) => new Date(`${iso}T12:00:00`);

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

