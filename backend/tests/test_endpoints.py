"""
Integration tests para los endpoints de la API.
Usa SQLite en memoria vía conftest fixtures.
"""
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.config import settings
from app.models.match import Match, MatchPhase, MatchStatus
from app.models.user import User
from app.services import football_api
from tests.conftest import TestSessionLocal
from tests.test_scheduler import _returns, _goal_event


# ── AUTH ENDPOINTS ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Jax FC",
        "email": "new@test.com",
        "password": "pass1234",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["team_name"] == "Jax FC"
    assert data["email"] == "new@test.com"
    assert data["is_admin"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_register_invalid_team(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Equipo Falso XYZ",
        "email": "fake@test.com",
        "password": "pass1234",
    })
    assert resp.status_code == 400
    assert "no está en la lista" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "team_name": "Jax FC",
        "email": "dup@test.com",
        "password": "pass1234",
    }
    resp1 = await client.post("/api/auth/register", json=payload)
    assert resp1.status_code == 201

    payload2 = {**payload, "team_name": "Genkidama F.C"}
    resp2 = await client.post("/api/auth/register", json=payload2)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "team_name": "Megalink FC",
        "email": "login@test.com",
        "password": "pass1234",
    })

    resp = await client.post("/api/auth/login", json={
        "email": "login@test.com",
        "password": "pass1234",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login@test.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post("/api/auth/register", json={
        "team_name": "Soldier Boy",
        "email": "wrong@test.com",
        "password": "correctpass",
    })

    resp = await client.post("/api/auth/login", json={
        "email": "wrong@test.com",
        "password": "incorrectpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post("/api/auth/register", json={
        "team_name": "Jax FC",
        "email": "short@test.com",
        "password": "abc",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={
        "email": "ghost@test.com",
        "password": "anything",
    })
    assert resp.status_code == 401


# ── CHANGE PASSWORD ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_success(auth_client: AsyncClient):
    """Cambia la contraseña con la actual correcta: limpia must_change_password,
    invalida la vieja y habilita la nueva."""
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "testpass123", "new_password": "nuevapass456",
    })
    assert resp.status_code == 200
    assert resp.json()["must_change_password"] is False

    old = await auth_client.post("/api/auth/login", json={
        "email": "test@test.com", "password": "testpass123"})
    assert old.status_code == 401
    new = await auth_client.post("/api/auth/login", json={
        "email": "test@test.com", "password": "nuevapass456"})
    assert new.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "incorrecta", "new_password": "nuevapass456"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_must_differ(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/change-password", json={
        "current_password": "testpass123", "new_password": "testpass123"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    resp = await client.post("/api/auth/change-password", json={
        "current_password": "x", "new_password": "yyyyyyyy"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_exposes_forced_flag_and_change_clears_it(client: AsyncClient):
    """Una cuenta marcada (como las que crea el script) expone el flag en el login
    y lo limpia al cambiar la contraseña."""
    await client.post("/api/auth/register", json={
        "team_name": "Megalink FC", "email": "mc@test.com", "password": "12345678"})
    async with TestSessionLocal() as s:
        user = (await s.execute(select(User).where(User.email == "mc@test.com"))).scalar_one()
        user.must_change_password = True
        await s.commit()

    login = await client.post("/api/auth/login", json={
        "email": "mc@test.com", "password": "12345678"})
    assert login.status_code == 200
    assert login.json()["user"]["must_change_password"] is True

    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    chg = await client.post("/api/auth/change-password", json={
        "current_password": "12345678", "new_password": "nuevapass789"})
    assert chg.status_code == 200
    assert chg.json()["must_change_password"] is False


# ── PROTECTED ENDPOINTS (unauthorized) ───────────────────────────────────────


@pytest.mark.asyncio
async def test_matches_requires_auth(client: AsyncClient):
    resp = await client.get("/api/matches/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_requires_auth(client: AsyncClient):
    resp = await client.get("/api/predictions/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_leaderboard_requires_auth(client: AsyncClient):
    resp = await client.get("/api/leaderboard/")
    assert resp.status_code == 401



# ── PROTECTED ENDPOINTS (authenticated) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_matches_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/matches/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_predictions_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/predictions/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_leaderboard(auth_client: AsyncClient):
    resp = await auth_client.get("/api/leaderboard/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["team_name"] == "Jax FC"


@pytest.mark.asyncio
async def test_leaderboard_ties_share_rank(auth_client: AsyncClient):
    """Empatados comparten rank (1, 2, 2, ...) en orden alfabético determinista."""
    from app.models.prediction import Prediction

    for team, email in [("Genkidama F.C", "g@test.com"), ("Megalink FC", "m@test.com")]:
        resp = await auth_client.post("/api/auth/register", json={
            "team_name": team, "email": email, "password": "pass1234",
        })
        assert resp.status_code == 201

    # Solo Jax FC (user 1) suma puntos; los otros dos empatan en 0.
    match_id = await _create_match()
    async with TestSessionLocal() as session:
        session.add(Prediction(
            user_id=1, match_id=match_id,
            predicted_home=1, predicted_away=0,
            points_earned=5, is_calculated=True,
        ))
        await session.commit()

    data = (await auth_client.get("/api/leaderboard/")).json()
    assert [(e["team_name"], e["rank"], e["total_points"]) for e in data] == [
        ("Jax FC", 1, 5),
        ("Genkidama F.C", 2, 0),
        ("Megalink FC", 2, 0),
    ]


# ── PREDICTIONS VALIDATION ────────────────────────────────────────────────────


async def _create_match(**overrides) -> int:
    """Inserta un partido de prueba directamente en la BD y retorna su id."""
    defaults = dict(
        api_fixture_id=1001,
        home_team="Argentina",
        away_team="Brazil",
        phase=MatchPhase.GROUP_STAGE,
        status=MatchStatus.SCHEDULED,
        match_date=datetime.now(timezone.utc) + timedelta(days=1),
    )
    defaults.update(overrides)
    async with TestSessionLocal() as session:
        match = Match(**defaults)
        session.add(match)
        await session.commit()
        await session.refresh(match)
        return match.id


@pytest.mark.asyncio
async def test_prediction_rejects_negative_score(auth_client: AsyncClient):
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": 1,
        "predicted_home": -1,
        "predicted_away": 0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_rejects_absurd_score(auth_client: AsyncClient):
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": 1,
        "predicted_home": 99,
        "predicted_away": 0,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_rejects_scorer_on_goalless(auth_client: AsyncClient):
    """Un 0-0 con primer goleador es contradictorio → 422 (no llega al endpoint)."""
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": 1,
        "predicted_home": 0,
        "predicted_away": 0,
        "first_goal_player_id": 10,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_prediction_create_success(auth_client: AsyncClient):
    match_id = await _create_match()
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 2,
        "predicted_away": 1,
        "first_goal_player_id": 10,  # L. Messi (Argentina), sembrado en conftest
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["predicted_home"] == 2
    assert data["first_goal_player_id"] == 10
    assert data["first_goal_player"] == "L. Messi"
    assert data["is_calculated"] is False


@pytest.mark.asyncio
async def test_prediction_rejects_started_match(auth_client: AsyncClient):
    """Pasada la hora de cierre de la jornada (1 h antes del primer partido del
    día), no se admiten pronósticos. Partido único cuyo kickoff ya pasó."""
    match_id = await _create_match(
        match_date=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
    })
    assert resp.status_code == 400
    assert "jornada" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_prediction_closes_for_whole_day_after_first_kickoff(auth_client: AsyncClient):
    """Regla de jornada: si el PRIMER partido del día ya empezó, un partido
    POSTERIOR del mismo día queda cerrado aunque por sí solo aún sería válido
    (su propio kickoff es dentro de >1 h)."""
    tz = ZoneInfo(settings.TOURNAMENT_TZ)
    today = datetime.now(timezone.utc).astimezone(tz).date()
    # Primer partido del día (00:01 hora del torneo): su cierre ya pasó seguro.
    first_dt = datetime.combine(today, time(0, 1), tzinfo=tz).astimezone(timezone.utc)
    # Partido del MISMO día a las 23:59: por sí solo sería pronosticable, pero la
    # jornada cerró 1 h antes del primer partido.
    later_dt = datetime.combine(today, time(23, 59), tzinfo=tz).astimezone(timezone.utc)
    await _create_match(api_fixture_id=2001, match_date=first_dt)
    later_id = await _create_match(api_fixture_id=2002, match_date=later_dt)

    resp = await auth_client.post("/api/predictions/", json={
        "match_id": later_id,
        "predicted_home": 2,
        "predicted_away": 0,
    })
    assert resp.status_code == 400
    assert "jornada" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_prediction_rejects_finished_match(auth_client: AsyncClient):
    match_id = await _create_match(
        status=MatchStatus.FINISHED,
        match_date=datetime.now(timezone.utc) - timedelta(days=1),
    )
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_prediction_rejects_foreign_first_goal_player(auth_client: AsyncClient):
    """Un jugador que no juega en ninguno de los dos equipos del partido → 400."""
    match_id = await _create_match()
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
        "first_goal_player_id": 30,  # T. Müller (Germany), no juega Argentina vs Brazil
    })
    assert resp.status_code == 400
    assert "no pertenece" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_prediction_rejects_unknown_first_goal_player(auth_client: AsyncClient):
    """Un id de jugador inexistente → 400."""
    match_id = await _create_match()
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
        "first_goal_player_id": 99999,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_prediction_stores_first_goal_player_name(auth_client: AsyncClient):
    """Guarda el id y denormaliza el nombre del jugador para mostrarlo."""
    match_id = await _create_match()
    resp = await auth_client.post("/api/predictions/", json={
        "match_id": match_id,
        "predicted_home": 1,
        "predicted_away": 0,
        "first_goal_player_id": 20,  # Neymar (Brazil)
    })
    assert resp.status_code == 201
    assert resp.json()["first_goal_player"] == "Neymar"


@pytest.mark.asyncio
async def test_match_players_lists_both_squads(auth_client: AsyncClient):
    """Devuelve los jugadores de los dos equipos del partido (con su api_player_id),
    no los de otras selecciones."""
    match_id = await _create_match()  # Argentina vs Brazil
    resp = await auth_client.get(f"/api/matches/{match_id}/players")
    assert resp.status_code == 200
    ids = {p["api_player_id"] for p in resp.json()}
    assert ids == {10, 20}  # Messi (Arg) + Neymar (Bra); Müller (Germany) queda fuera


@pytest.mark.asyncio
async def test_match_players_search_filters_by_name(auth_client: AsyncClient):
    """`search` filtra la plantilla del partido por nombre/apellido (subcadena)."""
    match_id = await _create_match()  # Argentina vs Brazil
    resp = await auth_client.get(f"/api/matches/{match_id}/players", params={"search": "messi"})
    assert resp.status_code == 200
    data = resp.json()
    assert [p["api_player_id"] for p in data] == [10]  # solo L. Messi


@pytest.mark.asyncio
async def test_match_players_search_treats_wildcards_as_literal(auth_client: AsyncClient):
    """Los comodines de LIKE se escapan: 'search=%' es subcadena literal, no "todos"."""
    match_id = await _create_match()  # Argentina vs Brazil (ningún nombre lleva '%')
    resp = await auth_client.get(f"/api/matches/{match_id}/players", params={"search": "%"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── CONFIG / TEAMS ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_config_teams_returns_participants_and_selecciones(client: AsyncClient):
    """Devuelve los participantes (registro) y las selecciones del Mundial (BD)."""
    resp = await client.get("/api/config/teams")
    assert resp.status_code == 200
    data = resp.json()
    assert "Jax FC" in data["allowed_teams"]
    assert "Argentina" in data["wc_teams"]


# ── PREDICTIONS BACKFILL (admin) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backfill_requires_admin(auth_client: AsyncClient):
    resp = await auth_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"match_id": 1, "predicted_home": 1, "predicted_away": 0}],
    })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_backfill_loads_prediction_for_finished_match(admin_client: AsyncClient):
    """El backfill admin carga pronósticos de partidos ya jugados (sin validar
    fecha) y los deja pendientes de cálculo."""
    match_id = await _create_match(
        status=MatchStatus.FINISHED,
        match_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    resp = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "first_goal_player_id": 10,
        }],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert len(data) == 1
    assert data[0]["first_goal_player"] == "L. Messi"
    assert data[0]["is_calculated"] is False

    # Reejecutar actualiza (idempotente), no duplica.
    resp2 = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"match_id": match_id, "predicted_home": 3, "predicted_away": 0}],
    })
    assert resp2.status_code == 201
    mine = (await admin_client.get("/api/predictions/")).json()
    assert len(mine) == 1
    assert mine[0]["predicted_home"] == 3


@pytest.mark.asyncio
async def test_backfill_finished_match_triggers_scoring(admin_client: AsyncClient, monkeypatch):
    """Si el partido ya finalizó, el backfill dispara el pipeline (primer gol +
    puntos) y devuelve la predicción YA calculada, sin esperar al timer de respaldo."""
    match_id = await _create_match(
        status=MatchStatus.FINISHED,
        home_score=2,
        away_score=1,
        match_date=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    # El job de primer gol consulta eventos: simular que la API devuelve el gol de Messi.
    monkeypatch.setattr(
        football_api, "fetch_fixture_events",
        _returns([_goal_event(10, "L. Messi", "Argentina")]),
    )
    resp = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{
            "match_id": match_id,
            "predicted_home": 2,
            "predicted_away": 1,
            "first_goal_player_id": 10,
        }],
    })
    assert resp.status_code == 201
    pred = resp.json()[0]
    assert pred["is_calculated"] is True
    # Exacto (8) + victoria (5) + primer goleador (3) en fase de grupos = 16.
    assert pred["points_earned"] == 16
    assert pred["match"]["first_goal_player"] == "L. Messi"


@pytest.mark.asyncio
async def test_backfill_unknown_team(admin_client: AsyncClient):
    resp = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Equipo Fantasma",
        "predictions": [{"match_id": 1, "predicted_home": 1, "predicted_away": 0}],
    })
    assert resp.status_code == 404


# ── HEALTH ENDPOINTS ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
