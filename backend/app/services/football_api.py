"""
Servicio de integración con API-Football para obtener datos del Mundial.
Docs: https://www.api-football.com/documentation-v3
"""
import httpx
from datetime import datetime, timedelta, timezone
from app.config import settings
from app.models.match import MatchPhase, MatchStatus
import logging

logger = logging.getLogger(__name__)

BASE_URL = settings.football_base_url

# Cliente compartido para reutilizar conexiones (lazy init).
_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            headers=settings.football_headers,
            timeout=settings.API_FOOTBALL_TIMEOUT,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None

# Mapeo de rondas de API-Football → MatchPhase interna.
# En el Mundial la fase de grupos llega como "Group Stage - 1/2/3" (jornadas):
# se resuelve por prefijo en _resolve_phase().
ROUND_MAP = {
    "Round of 32":      MatchPhase.ROUND_OF_32,
    "Round of 16":      MatchPhase.ROUND_OF_16,
    "Quarter-finals":   MatchPhase.QUARTER_FINALS,
    "Semi-finals":      MatchPhase.SEMI_FINALS,
    "3rd Place Final":  MatchPhase.THIRD_PLACE,
    "Final":            MatchPhase.FINAL,
}


def _resolve_phase(raw_round: str) -> MatchPhase:
    """Traduce el nombre de ronda de API-Football a una fase interna.
    La fase de grupos llega con sufijo de jornada ('Group Stage - 1')."""
    if raw_round.startswith("Group Stage"):
        return MatchPhase.GROUP_STAGE
    phase = ROUND_MAP.get(raw_round)
    if phase is None:
        logger.warning("Ronda desconocida de API-Football: %r (usando GROUP_STAGE)", raw_round)
        return MatchPhase.GROUP_STAGE
    return phase

# Mapeo de status de API-Football → MatchStatus interna
STATUS_MAP = {
    "NS":  MatchStatus.SCHEDULED,   # Not Started
    "1H":  MatchStatus.LIVE,
    "HT":  MatchStatus.LIVE,
    "2H":  MatchStatus.LIVE,
    "ET":  MatchStatus.LIVE,
    "P":   MatchStatus.LIVE,
    "FT":  MatchStatus.FINISHED,
    "AET": MatchStatus.FINISHED,
    "PEN": MatchStatus.FINISHED,
    "PST": MatchStatus.POSTPONED,
}


def _extract_response(data: dict, endpoint: str) -> list[dict]:
    """Extrae 'response' validando el campo 'errors' de API-Football.

    API-Football devuelve HTTP 200 incluso cuando la petición no trae datos por
    un problema de plan, cuota o parámetros: el motivo viaja en 'errors' (dict o
    lista). Sin esto, esos casos se verían como "0 resultados" sin explicación.
    """
    errors = data.get("errors")
    # 'errors' es [] cuando no hay error; dict no vacío (o lista no vacía) si lo hay.
    if errors:
        logger.warning("API-Football /%s devolvió errores: %s", endpoint, errors)
    return data.get("response", [])


async def _get(endpoint: str, params: dict) -> list[dict]:
    """GET a un endpoint de API-Football: lanza ante error HTTP y devuelve
    'response' validando el campo 'errors' (que llega con HTTP 200). El nombre del
    endpoint sirve también de etiqueta para los logs de `_extract_response`."""
    response = await get_client().get(f"{BASE_URL}/{endpoint}", params=params)
    response.raise_for_status()
    return _extract_response(response.json(), endpoint)


async def fetch_fixtures(season: int | None = None) -> list[dict]:
    """Obtiene todos los fixtures del Mundial para la temporada indicada."""
    return await _get("fixtures", {"league": settings.LEAGUE_ID, "season": season or settings.SEASON})


async def fetch_teams(season: int | None = None) -> list[dict]:
    """Obtiene las selecciones participantes del Mundial para la temporada indicada."""
    return await _get("teams", {"league": settings.LEAGUE_ID, "season": season or settings.SEASON})


def parse_team(team_data: dict) -> dict:
    """Transforma el formato de API-Football (/teams) al formato interno."""
    t = team_data["team"]
    return {
        "api_team_id": t["id"],
        "name":        t["name"],
        "code":        t.get("code"),
        "country":     t.get("country"),
        "logo":        t.get("logo"),
    }


async def fetch_squad(team_api_id: int) -> list[dict]:
    """Obtiene la plantilla (squad) de un equipo desde `/players/squads`.
    No depende de la temporada: devuelve el plantel actual del equipo."""
    return await _get("players/squads", {"team": team_api_id})


def parse_squad(squad_data: dict, team_name: str | None = None) -> list[dict]:
    """Transforma una entrada de `/players/squads` en filas de la tabla `players`.

    Estructura de entrada: {"team": {id, name}, "players": [{id, name, position, photo}]}.

    `team_name` (opcional): nombre canónico de la selección (el de los partidos). El
    endpoint de plantillas a veces usa otro nombre para la misma selección (p. ej.
    'Czech Republic' aquí vs 'Czechia' en los fixtures); pasarlo evita que la plantilla
    quede 'huérfana' y no haga match con su partido.
    """
    team = squad_data["team"]
    team_api_id = team["id"]
    team_name = team_name or team["name"]
    parsed: list[dict] = []
    for p in squad_data.get("players", []):
        if p.get("id") is None:
            continue
        parsed.append({
            "api_player_id": p["id"],
            "name":          p.get("name") or f"#{p['id']}",
            "team_api_id":   team_api_id,
            "team_name":     team_name,
            "position":      p.get("position"),
            "photo":         p.get("photo"),
        })
    return parsed


async def fetch_fixture_events(fixture_id: int) -> list[dict]:
    """Obtiene los eventos de un partido (goles, tarjetas, etc.) para determinar el primer gol."""
    return await _get("fixtures/events", {"fixture": fixture_id})


def parse_fixture(fixture_data: dict) -> dict:
    """
    Transforma el formato de API-Football al formato interno.
    """
    f = fixture_data["fixture"]
    teams = fixture_data["teams"]
    goals = fixture_data["goals"]
    league = fixture_data["league"]

    raw_round  = league.get("round", "Group Stage")
    phase      = _resolve_phase(raw_round)
    raw_status = f["status"]["short"]
    status     = STATUS_MAP.get(raw_status, MatchStatus.SCHEDULED)
    match_date = datetime.fromisoformat(f["date"])

    # Fallback de finalización: un partido de grupos aún LIVE pasados
    # MATCH_FINISH_FALLBACK_MINUTES del kickoff se da por finalizado. Las eliminatorias
    # pueden ir a prórroga/penales, así que ahí se respeta el estado de la API.
    if (
        status == MatchStatus.LIVE
        and phase == MatchPhase.GROUP_STAGE
        and datetime.now(timezone.utc) - match_date
            > timedelta(minutes=settings.MATCH_FINISH_FALLBACK_MINUTES)
    ):
        status = MatchStatus.FINISHED

    return {
        "api_fixture_id": f["id"],
        "home_team":      teams["home"]["name"],
        "away_team":      teams["away"]["name"],
        "home_team_logo": teams["home"]["logo"],
        "away_team_logo": teams["away"]["logo"],
        "home_score":     goals["home"],
        "away_score":     goals["away"],
        "elapsed":        f["status"].get("elapsed"),
        "phase":          phase,
        "status":         status,
        "match_date":     match_date,
    }


def get_first_goal_scorer(events: list[dict]) -> dict | None:
    """
    Determina quién anotó el primer gol a partir de los eventos del partido.
    Devuelve {"team", "player_id", "player_name"} o None si no hubo gol.

    El `player_id` es el id de API-Football del goleador: el mismo namespace que
    la tabla `players`, de modo que el scoring del primer goleador se hace por id.
    """
    for event in sorted(events, key=lambda e: (e["time"]["elapsed"], e["time"].get("extra") or 0)):
        if event["type"] == "Goal" and event["detail"] != "Missed Penalty":
            player = event.get("player") or {}
            return {
                "team":        event["team"]["name"],
                "player_id":   player.get("id"),
                "player_name": player.get("name"),
            }
    return None
