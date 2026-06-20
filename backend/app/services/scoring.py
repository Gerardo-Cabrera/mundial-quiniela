"""
Motor de puntuación de la quiniela del Mundial.
Centraliza todas las reglas de puntos para fácil mantenimiento.
"""
from app.models.match import MatchPhase


# ── TABLAS DE PUNTOS ──────────────────────────────────────────────────────────

GROUP_POINTS = {
    "win":        5,
    "draw":       6,
    "first_goal": 3,
    "exact":      8,
}

KNOCKOUT_POINTS = {
    "win":        8,
    "draw":       9,
    "first_goal": 5,
    "exact":      11,
}

# Fases de eliminación directa (pagan más que la fase de grupos).
KNOCKOUT_PHASES = {
    MatchPhase.ROUND_OF_32,
    MatchPhase.ROUND_OF_16,
    MatchPhase.QUARTER_FINALS,
    MatchPhase.SEMI_FINALS,
    MatchPhase.THIRD_PLACE,
    MatchPhase.FINAL,
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _get_outcome(home: int, away: int) -> str:
    if home > away:
        return "home"
    if away > home:
        return "away"
    return "draw"


def _get_points_table(phase: MatchPhase) -> dict:
    return KNOCKOUT_POINTS if phase in KNOCKOUT_PHASES else GROUP_POINTS


# ── PUNTUACIÓN DE PARTIDOS ────────────────────────────────────────────────────

def calculate_match_points(
    *,
    predicted_home: int,
    predicted_away: int,
    predicted_first_goal_player_id: int | None,
    actual_home: int,
    actual_away: int,
    actual_first_goal_player_id: int | None,
    phase: MatchPhase,
) -> dict:
    """
    Calcula los puntos de un pronóstico de partido.
    Retorna un dict con el desglose y el total.

    El primer gol se puntúa por **jugador** (primer goleador): se compara el
    `api_player_id` pronosticado contra el del goleador real. Comparar por id evita
    la ambigüedad de nombres.
    """
    p = _get_points_table(phase)
    breakdown = {"exact": 0, "outcome": 0, "first_goal": 0, "total": 0}

    exact_score = (predicted_home == actual_home and predicted_away == actual_away)

    if exact_score:
        breakdown["exact"] = p["exact"]
    else:
        pred_outcome   = _get_outcome(predicted_home, predicted_away)
        actual_outcome = _get_outcome(actual_home, actual_away)
        if pred_outcome == actual_outcome:
            breakdown["outcome"] = p["draw"] if actual_outcome == "draw" else p["win"]

    if (
        predicted_first_goal_player_id is not None
        and actual_first_goal_player_id is not None
        and predicted_first_goal_player_id == actual_first_goal_player_id
    ):
        breakdown["first_goal"] = p["first_goal"]

    breakdown["total"] = breakdown["exact"] + breakdown["outcome"] + breakdown["first_goal"]
    return breakdown
