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


@pytest.mark.asyncio
async def test_user_predictions_reveal_by_started_day(auth_client: AsyncClient, monkeypatch):
    """Ver los pronósticos de otro participante se revela por JORNADA (día): una vez
    que su primer partido comenzó, se ven TODOS los del día —incluido uno que aún NO
    empieza—; las jornadas no iniciadas se ocultan. Se congela 'ahora' para que el
    resultado no dependa del reloj real."""
    from app.crud import matches as matches_module
    from app.models.prediction import Prediction

    # 'Ahora' fijo (17/06 18:00 UTC = 12:00 en TOURNAMENT_TZ). Solo se parchea el
    # módulo que consulta la hora en la ruta (get_started_day_match_ids).
    frozen_now = datetime(2026, 6, 17, 18, tzinfo=timezone.utc)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen_now if tz else frozen_now.replace(tzinfo=None)

    monkeypatch.setattr(matches_module, "datetime", _FrozenDatetime)

    # Jornada de hoy (17/06): el primer partido ya jugó y otro del MISMO día aún no
    # empieza (kickoff futuro respecto a 'ahora') → ambos se revelan.
    started = await _create_match(
        api_fixture_id=2001, status=MatchStatus.FINISHED,
        match_date=datetime(2026, 6, 17, 16, tzinfo=timezone.utc),
    )
    not_yet = await _create_match(
        api_fixture_id=2002, status=MatchStatus.SCHEDULED,
        match_date=datetime(2026, 6, 17, 22, tzinfo=timezone.utc),
    )
    # Jornada del día siguiente (no iniciada): oculta.
    future = await _create_match(
        api_fixture_id=2003, status=MatchStatus.SCHEDULED,
        match_date=datetime(2026, 6, 18, 22, tzinfo=timezone.utc),
    )
    async with TestSessionLocal() as session:
        session.add_all([
            Prediction(user_id=1, match_id=started, predicted_home=1, predicted_away=0),
            Prediction(user_id=1, match_id=not_yet, predicted_home=2, predicted_away=2),
            Prediction(user_id=1, match_id=future, predicted_home=3, predicted_away=3),
        ])
        await session.commit()

    data = (await auth_client.get("/api/predictions/user/1")).json()
    ids = {p["match_id"] for p in data}
    assert ids == {started, not_yet}   # el día iniciado completo, incl. el no empezado
    assert future not in ids            # jornada no iniciada, oculta


@pytest.mark.asyncio
async def test_matchdays_summary_mvp_and_ranking(auth_client: AsyncClient):
    """Resumen por jornada: puntos por participante, MVP del día y ranking de MVPs.
    Solo cuenta predicciones ya calculadas (excluye partidos no jugados)."""
    from app.models.prediction import Prediction

    await auth_client.post("/api/auth/register", json={
        "team_name": "Genkidama F.C", "email": "g2@test.com", "password": "pass1234",
    })
    # user 1 = Jax FC, user 2 = Genkidama F.C
    a1 = await _create_match(api_fixture_id=3001, status=MatchStatus.FINISHED, match_date=datetime(2026, 6, 17, 12, tzinfo=timezone.utc))
    a2 = await _create_match(api_fixture_id=3002, status=MatchStatus.FINISHED, match_date=datetime(2026, 6, 17, 12, tzinfo=timezone.utc))
    b1 = await _create_match(api_fixture_id=3003, status=MatchStatus.FINISHED, match_date=datetime(2026, 6, 18, 12, tzinfo=timezone.utc))
    c1 = await _create_match(api_fixture_id=3004, status=MatchStatus.SCHEDULED, match_date=datetime(2026, 6, 19, 12, tzinfo=timezone.utc))
    async with TestSessionLocal() as session:
        session.add_all([
            Prediction(user_id=1, match_id=a1, predicted_home=1, predicted_away=0, points_earned=5, is_calculated=True),
            Prediction(user_id=1, match_id=a2, predicted_home=1, predicted_away=0, points_earned=1, is_calculated=True),
            Prediction(user_id=2, match_id=a1, predicted_home=2, predicted_away=0, points_earned=3, is_calculated=True),
            Prediction(user_id=2, match_id=a2, predicted_home=2, predicted_away=0, points_earned=4, is_calculated=True),
            Prediction(user_id=1, match_id=b1, predicted_home=3, predicted_away=0, points_earned=8, is_calculated=True),
            Prediction(user_id=2, match_id=b1, predicted_home=1, predicted_away=1, points_earned=2, is_calculated=True),
            # No calculada (partido no jugado): NO debe aparecer ninguna jornada 06-19.
            Prediction(user_id=1, match_id=c1, predicted_home=1, predicted_away=0, points_earned=0, is_calculated=False),
        ])
        await session.commit()

    data = (await auth_client.get("/api/matchdays/")).json()
    assert [d["date"] for d in data["days"]] == ["2026-06-17", "2026-06-18"]  # cronológico, sin 06-19

    a = data["days"][0]
    assert a["mvp_points"] == 7 and a["mvps"] == ["Genkidama F.C"]
    assert [(e["team_name"], e["points"]) for e in a["entries"]] == [("Genkidama F.C", 7), ("Jax FC", 6)]

    assert data["days"][1]["mvps"] == ["Jax FC"] and data["days"][1]["mvp_points"] == 8

    # Cada uno fue MVP una vez; empate en count → desempate alfabético.
    assert data["mvp_ranking"] == [
        {"team_name": "Genkidama F.C", "count": 1},
        {"team_name": "Jax FC", "count": 1},
    ]


@pytest.mark.asyncio
async def test_stats_first_goal_and_exact(auth_client: AsyncClient):
    """Aciertos de primer gol (por partido + ranking), marcador más repetido y ranking
    de marcador exacto, sobre predicciones ya calculadas de partidos finalizados."""
    from app.models.prediction import Prediction

    await auth_client.post("/api/auth/register", json={
        "team_name": "Genkidama F.C", "email": "g3@test.com", "password": "pass1234",
    })  # user 2 (user 1 = Jax FC)

    m1 = await _create_match(api_fixture_id=4001, status=MatchStatus.FINISHED,
        home_score=2, away_score=1, first_goal_player_id=10, first_goal_player="L. Messi",
        match_date=datetime(2026, 6, 17, 20, tzinfo=timezone.utc))
    m2 = await _create_match(api_fixture_id=4002, status=MatchStatus.FINISHED,
        home_score=2, away_score=1, first_goal_player_id=20, first_goal_player="Neymar",
        match_date=datetime(2026, 6, 17, 18, tzinfo=timezone.utc))
    m3 = await _create_match(api_fixture_id=4003, status=MatchStatus.FINISHED,
        home_score=1, away_score=0, first_goal_player_id=10, first_goal_player="L. Messi",
        match_date=datetime(2026, 6, 16, 18, tzinfo=timezone.utc))
    async with TestSessionLocal() as session:
        session.add_all([
            Prediction(user_id=1, match_id=m1, predicted_home=2, predicted_away=1, first_goal_player_id=10, is_calculated=True),
            Prediction(user_id=1, match_id=m2, predicted_home=2, predicted_away=1, first_goal_player_id=99, is_calculated=True),
            Prediction(user_id=1, match_id=m3, predicted_home=0, predicted_away=0, first_goal_player_id=10, is_calculated=True),
            Prediction(user_id=2, match_id=m1, predicted_home=2, predicted_away=1, first_goal_player_id=99, is_calculated=True),
            Prediction(user_id=2, match_id=m2, predicted_home=1, predicted_away=1, first_goal_player_id=20, is_calculated=True),
        ])
        await session.commit()

    data = (await auth_client.get("/api/stats/")).json()

    # user1: exacto en m1 y m2 (2); user2: exacto solo en m1 (1).
    assert data["exact_ranking"] == [
        {"team_name": "Jax FC", "count": 2},
        {"team_name": "Genkidama F.C", "count": 1},
    ]
    # user1: primer gol en m1 y m3 (2); user2: primer gol en m2 (1).
    assert data["first_goal_ranking"] == [
        {"team_name": "Jax FC", "count": 2},
        {"team_name": "Genkidama F.C", "count": 1},
    ]
    # Marcador real más repetido: 2-1 (m1 y m2).
    assert data["top_scores"] == [{"score": "2-1", "count": 2}]
    # Primer gol por partido: solo los partidos con acierto (los 3 lo tienen aquí).
    hitters = {fg["match_id"]: fg["hitters"] for fg in data["first_goal_matches"]}
    assert hitters == {m1: ["Jax FC"], m2: ["Genkidama F.C"], m3: ["Jax FC"]}
    # Marcadores exactos acertados: m1 (2-1) por ambos, m2 (2-1) por Jax FC; m3 (1-0)
    # no lo acertó nadie → no aparece.
    exact = {e["match_id"]: (e["score"], e["hitters"]) for e in data["exact_matches"]}
    assert exact == {m1: ("2-1", ["Genkidama F.C", "Jax FC"]), m2: ("2-1", ["Jax FC"])}


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
async def test_late_predictions_switch(admin_client: AsyncClient):
    """El interruptor de pronósticos tardíos reabre la ventana entre el cierre normal
    (1 h antes) y el inicio del primer partido; nunca tras el inicio."""
    # Único partido de HOY, kickoff a 30 min → su jornada ya cerró (dentro de la hora previa).
    grace_id = await _create_match(
        api_fixture_id=2500,
        match_date=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    body = {"match_id": grace_id, "predicted_home": 1, "predicted_away": 0}

    # Interruptor OFF (por defecto): cerrado.
    assert (await admin_client.post("/api/predictions/", json=body)).status_code == 400

    # Interruptor ON.
    r = await admin_client.post("/api/config/settings", json={"late_predictions_enabled": True})
    assert r.status_code == 200 and r.json()["late_predictions_enabled"] is True

    # Ahora se admite (el primer partido aún no empieza).
    assert (await admin_client.post("/api/predictions/", json=body)).status_code == 201

    # Un partido cuya jornada ya inició sigue cerrado, incluso con el interruptor ON.
    started_id = await _create_match(
        api_fixture_id=2501,
        match_date=datetime(2026, 6, 17, 12, tzinfo=timezone.utc),  # otro día, ya pasado
    )
    started_body = {"match_id": started_id, "predicted_home": 0, "predicted_away": 0}
    assert (await admin_client.post("/api/predictions/", json=started_body)).status_code == 400


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
async def test_backfill_by_team_names(admin_client: AsyncClient):
    """El backfill identifica el partido por el PAR de equipos (sin match_id) y orienta
    el marcador al home/away del fixture aunque el par venga invertido."""
    match_id = await _create_match(
        home_team="Argentina", away_team="Brazil", status=MatchStatus.FINISHED,
        match_date=datetime.now(timezone.utc) - timedelta(days=2),
    )
    # En el orden del fixture.
    resp = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"home_team": "Argentina", "away_team": "Brazil", "predicted_home": 2, "predicted_away": 1}],
    })
    assert resp.status_code == 201
    assert resp.json()[0]["match_id"] == match_id
    assert (resp.json()[0]["predicted_home"], resp.json()[0]["predicted_away"]) == (2, 1)

    # Par INVERTIDO (Brazil 1 - Argentina 2): se orienta al fixture → 2 - 1.
    resp2 = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"home_team": "Brazil", "away_team": "Argentina", "predicted_home": 1, "predicted_away": 2}],
    })
    assert resp2.status_code == 201
    assert (resp2.json()[0]["predicted_home"], resp2.json()[0]["predicted_away"]) == (2, 1)

    # Equipos sin partido → 404; sin match_id ni equipos → 422 (validación de schema).
    bad = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"home_team": "Narnia", "away_team": "Wakanda", "predicted_home": 0, "predicted_away": 0}],
    })
    assert bad.status_code == 404
    invalid = await admin_client.post("/api/predictions/admin/backfill", json={
        "team_name": "Jax FC",
        "predictions": [{"predicted_home": 1, "predicted_away": 0}],
    })
    assert invalid.status_code == 422


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
