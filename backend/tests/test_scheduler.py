"""
Tests de los jobs del scheduler: cálculo de puntos y sync de primer gol.

Regresión del bug de carrera: calculate_pending_points (cada 30 min) puntuaba
partidos finalizados antes de que sync_first_goals (cada hora) trajera el dato
del primer gol, perdiendo esos puntos permanentemente.

El primer gol se puntúa por JUGADOR (primer goleador): se compara el
`first_goal_player_id` pronosticado contra el del goleador real.
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import RequestError
from sqlalchemy import select, delete

from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.models.player import Player
from app.models.team import Team
from app.services import scheduler as scheduler_module
from app.services import football_api
from app.crud import match_crud
from tests.conftest import TestSessionLocal

# id del jugador que se usa como goleador pronosticado en los seeds.
SCORER_ID = 100


def _returns(value):
    """Devuelve una coroutine que resuelve a `value` (para monkeypatch de I/O)."""
    async def _coro(*args, **kwargs):
        return value
    return _coro


def _goal_event(player_id: int, player_name: str, team: str, elapsed: int = 20) -> dict:
    return {
        "time": {"elapsed": elapsed, "extra": None},
        "type": "Goal",
        "detail": "Normal Goal",
        "team": {"name": team},
        "player": {"id": player_id, "name": player_name},
    }


def _raw_fixture(
    fixture_id: int,
    *,
    home: str = "Argentina",
    away: str = "Brazil",
    home_score: int | None = None,
    away_score: int | None = None,
    status: str = "NS",
    round_: str = "Group Stage - 1",
    date: str = "2026-06-11T18:00:00+00:00",
) -> dict:
    """Construye un fixture en el formato crudo de API-Football (para parse_fixture)."""
    return {
        "fixture": {"id": fixture_id, "status": {"short": status}, "date": date},
        "teams": {
            "home": {"name": home, "logo": None},
            "away": {"name": away, "logo": None},
        },
        "goals": {"home": home_score, "away": away_score},
        "league": {"round": round_},
    }


@pytest.fixture(autouse=True)
def _use_test_db(monkeypatch):
    """Los jobs usan AsyncSessionLocal directamente: apuntarlos a la BD de test."""
    monkeypatch.setattr(scheduler_module, "AsyncSessionLocal", TestSessionLocal)


async def _seed(
    *,
    home_score: int = 2,
    away_score: int = 1,
    actual_first_goal_team: str | None = None,
    actual_first_goal_player_id: int | None = None,
    match_date: datetime | None = None,
    predicted_home: int = 2,
    predicted_away: int = 1,
    predicted_first_goal_player_id: int | None = SCORER_ID,
) -> int:
    """Crea usuario + partido finalizado + predicción. Retorna el id de la predicción.

    `actual_first_goal_team` marca que el primer gol ya está resuelto (gate del
    cálculo); `actual_first_goal_player_id` es el goleador real contra el que se
    puntúa el `predicted_first_goal_player_id`.
    """
    async with TestSessionLocal() as session:
        user = User(team_name="Jax FC", email="sched@test.com", hashed_password="x")
        session.add(user)
        await session.flush()

        match = Match(
            api_fixture_id=5001,
            home_team="Argentina",
            away_team="Brazil",
            home_score=home_score,
            away_score=away_score,
            first_goal_team=actual_first_goal_team,
            first_goal_player_id=actual_first_goal_player_id,
            phase=MatchPhase.GROUP_STAGE,
            status=MatchStatus.FINISHED,
            match_date=match_date or datetime.now(timezone.utc) - timedelta(hours=3),
        )
        session.add(match)
        await session.flush()

        prediction = Prediction(
            user_id=user.id,
            match_id=match.id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            first_goal_player_id=predicted_first_goal_player_id,
        )
        session.add(prediction)
        await session.commit()
        return prediction.id


async def _get_prediction(prediction_id: int) -> Prediction:
    async with TestSessionLocal() as session:
        return await session.get(Prediction, prediction_id)


@pytest.mark.asyncio
async def test_calc_waits_for_first_goal():
    """Partido reciente con goles pero sin primer gol sincronizado: no puntuar aún."""
    pred_id = await _seed(actual_first_goal_team=None)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is False
    assert pred.points_earned == 0


@pytest.mark.asyncio
async def test_calc_scores_with_first_goal_known():
    """Con el goleador acertado: exacto (8) + victoria (5) + primer goleador (3) = 16."""
    pred_id = await _seed(
        actual_first_goal_team="Argentina",
        actual_first_goal_player_id=SCORER_ID,
    )

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 16


@pytest.mark.asyncio
async def test_calc_first_goal_wrong_player():
    """Acierta el marcador pero falla el goleador: exacto (8) + victoria (5) = 13."""
    pred_id = await _seed(
        actual_first_goal_team="Argentina",
        actual_first_goal_player_id=999,  # goleador real distinto al pronosticado
        predicted_first_goal_player_id=SCORER_ID,
    )

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 13


@pytest.mark.asyncio
async def test_calc_zero_zero_does_not_wait():
    """Un 0-0 no tiene primer gol que esperar: se puntúa de inmediato."""
    pred_id = await _seed(home_score=0, away_score=0, predicted_home=0, predicted_away=0)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 14  # exacto (8) + empate (6) en fase de grupos


@pytest.mark.asyncio
async def test_calc_grace_period_unblocks():
    """Si la API nunca entrega el primer gol, tras el plazo de gracia se
    puntúa sin él para no dejar puntos bloqueados."""
    old_date = datetime.now(timezone.utc) - timedelta(
        hours=scheduler_module.settings.FIRST_GOAL_GRACE_HOURS + 12
    )
    pred_id = await _seed(actual_first_goal_team=None, match_date=old_date)

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 13  # exacto (8) + victoria (5), sin goleador


@pytest.mark.asyncio
async def test_sync_first_goals_self_heals(monkeypatch):
    """Si una predicción se puntuó sin el primer gol, al llegar el dato se
    resetea y el siguiente cálculo otorga los puntos completos."""
    pred_id = await _seed(actual_first_goal_team=None)

    # Simular el estado del bug: ya calculada sin el punto de primer gol
    # (exacto 8 + victoria 5 = 13).
    async with TestSessionLocal() as session:
        pred = await session.get(Prediction, pred_id)
        pred.is_calculated = True
        pred.points_earned = 13
        await session.commit()

    async def fake_fetch_events(fixture_id: int) -> list[dict]:
        return [
            {"time": {"elapsed": 55, "extra": None}, "type": "Card",
             "detail": "Yellow Card", "team": {"name": "Brazil"}},
            _goal_event(SCORER_ID, "Messi", "Argentina", elapsed=23),
        ]

    monkeypatch.setattr(football_api, "fetch_fixture_events", fake_fetch_events)

    await scheduler_module._do_sync_first_goals()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is False  # marcada para recálculo

    await scheduler_module._do_calculate_points()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 16  # ahora con el punto de primer gol


# ── SYNC FIXTURES (upsert por lotes) ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_fixtures_upserts_idempotently(monkeypatch):
    """Inserta partidos nuevos y, al reejecutar con el mismo api_fixture_id,
    actualiza en sitio sin duplicar (upsert por lotes en una sola query)."""
    monkeypatch.setattr(football_api, "fetch_fixtures", _returns([
        _raw_fixture(7001),
        _raw_fixture(7002, home="France", away="Spain"),
    ]))

    await scheduler_module._do_sync_fixtures()

    async with TestSessionLocal() as session:
        rows = (await session.execute(select(Match))).scalars().all()
        assert len(rows) == 2

    # Reejecutar: el 7001 ahora finalizó 2-1 → debe actualizarse, no duplicarse.
    monkeypatch.setattr(football_api, "fetch_fixtures", _returns([
        _raw_fixture(7001, home_score=2, away_score=1, status="FT"),
    ]))

    await scheduler_module._do_sync_fixtures()

    async with TestSessionLocal() as session:
        rows = {
            m.api_fixture_id: m
            for m in (await session.execute(select(Match))).scalars().all()
        }
        assert len(rows) == 2  # sin duplicar
        assert rows[7001].home_score == 2
        assert rows[7001].away_score == 1
        assert rows[7001].status == MatchStatus.FINISHED


@pytest.mark.asyncio
async def test_upsert_handles_duplicate_keys_in_batch():
    """Dos filas con la misma clave en un mismo lote no rompen el flush (UNIQUE):
    se inserta una sola y la última ocurrencia gana."""
    f1 = football_api.parse_fixture(_raw_fixture(9100, home_score=1, away_score=0, status="FT"))
    f2 = football_api.parse_fixture(_raw_fixture(9100, home_score=2, away_score=2, status="FT"))
    async with TestSessionLocal() as session:
        await match_crud.upsert_many(session, [f1, f2])
        await session.commit()
        rows = (
            await session.execute(select(Match).where(Match.api_fixture_id == 9100))
        ).scalars().all()
    assert len(rows) == 1            # no se duplicó
    assert rows[0].home_score == 2   # última gana
    assert rows[0].away_score == 2


@pytest.mark.asyncio
async def test_sync_fixtures_pipeline_scores_on_newly_finished(monkeypatch):
    """Pipeline near-real-time: cuando un partido pasa a FINISHED, sync_fixtures
    encadena primer gol + puntos en la MISMA corrida (sin esperar a los timers)."""
    async with TestSessionLocal() as session:
        user = User(team_name="Jax FC", email="pipe@test.com", hashed_password="x")
        session.add(user)
        await session.flush()
        match = Match(
            api_fixture_id=9300, home_team="Argentina", away_team="Brazil",
            phase=MatchPhase.GROUP_STAGE, status=MatchStatus.LIVE,
            match_date=datetime.now(timezone.utc) - timedelta(minutes=130),
        )
        session.add(match)
        await session.flush()
        session.add(Prediction(
            user_id=user.id, match_id=match.id,
            predicted_home=2, predicted_away=1, first_goal_player_id=SCORER_ID,
        ))
        await session.commit()

    # La API ahora reporta el partido FINISHED 2-1 y sus eventos con el primer gol.
    recent = (datetime.now(timezone.utc) - timedelta(minutes=130)).isoformat()
    monkeypatch.setattr(football_api, "fetch_fixtures", _returns([
        _raw_fixture(9300, home_score=2, away_score=1, status="FT", date=recent),
    ]))
    monkeypatch.setattr(football_api, "fetch_fixture_events",
                        _returns([_goal_event(SCORER_ID, "Messi", "Argentina", elapsed=10)]))
    monkeypatch.setattr(scheduler_module, "_last_fixtures_fetch", None)  # idle_due → corre

    await scheduler_module.sync_fixtures()

    pred = await _get_prediction(
        (await _first_prediction_id())
    )
    assert pred.is_calculated is True
    assert pred.points_earned == 16  # exacto 8 + victoria 5 + primer gol 3, sin esperar timers


async def _first_prediction_id() -> int:
    async with TestSessionLocal() as session:
        return (await session.execute(select(Prediction.id))).scalars().first()


@pytest.mark.asyncio
async def test_sync_first_goals_resolves_live_match(monkeypatch):
    """El primer gol se resuelve también en partidos EN VIVO (no solo finalizados):
    aparece en pleno partido, sin esperar al FT."""
    async with TestSessionLocal() as session:
        session.add(Match(
            api_fixture_id=9400, home_team="Argentina", away_team="Brazil",
            home_score=1, away_score=0, status=MatchStatus.LIVE,
            phase=MatchPhase.GROUP_STAGE,
            match_date=datetime.now(timezone.utc) - timedelta(minutes=20),
        ))
        await session.commit()
    monkeypatch.setattr(football_api, "fetch_fixture_events",
                        _returns([_goal_event(SCORER_ID, "Messi", "Argentina", elapsed=12)]))

    await scheduler_module._do_sync_first_goals()

    async with TestSessionLocal() as session:
        m = (await session.execute(
            select(Match).where(Match.api_fixture_id == 9400)
        )).scalars().first()
    assert m.first_goal_player_id == SCORER_ID
    assert m.first_goal_team == "Argentina"


@pytest.mark.asyncio
async def test_sync_first_goals_gives_up_after_grace(monkeypatch):
    """Pasado el plazo de gracia no se insiste: un partido viejo con goles pero sin
    primer gol (la API nunca dio los eventos) deja de consultarse."""
    calls = {"n": 0}
    async def counting_events(*a, **k):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_fixture_events", counting_events)
    async with TestSessionLocal() as session:
        session.add(Match(
            api_fixture_id=9500, home_team="A", away_team="B",
            home_score=1, away_score=0, status=MatchStatus.FINISHED,
            phase=MatchPhase.GROUP_STAGE,
            match_date=datetime.now(timezone.utc) - timedelta(days=10),
        ))
        await session.commit()

    await scheduler_module._do_sync_first_goals()
    assert calls["n"] == 0  # fuera de la ventana de gracia → no consulta eventos


async def _seed_calculated(points: int) -> int:
    """Predicción ya puntuada de un partido FINISHED (api_fixture_id=5001)."""
    pred_id = await _seed(
        home_score=2, away_score=1,
        actual_first_goal_team="Argentina", actual_first_goal_player_id=SCORER_ID,
    )
    async with TestSessionLocal() as session:
        pred = await session.get(Prediction, pred_id)
        pred.is_calculated = True
        pred.points_earned = points
        await session.commit()
    return pred_id


@pytest.mark.asyncio
async def test_upsert_resets_calc_when_finished_score_changes():
    """Si un partido ya FINISHED cambia de marcador tras puntuar, sus predicciones se
    resetean para recálculo (corrige el bug de puntos obsoletos)."""
    pred_id = await _seed_calculated(points=16)
    corrected = football_api.parse_fixture(
        _raw_fixture(5001, home_score=3, away_score=1, status="FT")
    )
    async with TestSessionLocal() as session:
        await match_crud.upsert_many(session, [corrected])
        await session.commit()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is False
    assert pred.points_earned == 0


@pytest.mark.asyncio
async def test_upsert_keeps_calc_when_score_unchanged():
    """Re-sincronizar sin cambio de marcador NO resetea (evita recálculos en cada corrida)."""
    pred_id = await _seed_calculated(points=16)
    same = football_api.parse_fixture(
        _raw_fixture(5001, home_score=2, away_score=1, status="FT")
    )
    async with TestSessionLocal() as session:
        await match_crud.upsert_many(session, [same])
        await session.commit()

    pred = await _get_prediction(pred_id)
    assert pred.is_calculated is True
    assert pred.points_earned == 16


@pytest.mark.asyncio
async def test_has_match_pending_finish():
    """True si hay un partido SCHEDULED/LIVE cuyo kickoff fue antes del corte."""
    now = datetime.now(timezone.utc)
    async with TestSessionLocal() as session:
        session.add_all([
            Match(api_fixture_id=8001, home_team="A", away_team="B",
                  phase=MatchPhase.GROUP_STAGE, status=MatchStatus.LIVE,
                  match_date=now - timedelta(minutes=120)),   # podría estar terminando
            Match(api_fixture_id=8002, home_team="C", away_team="D",
                  phase=MatchPhase.GROUP_STAGE, status=MatchStatus.LIVE,
                  match_date=now - timedelta(minutes=10)),     # recién empezado
            Match(api_fixture_id=8003, home_team="E", away_team="F",
                  phase=MatchPhase.GROUP_STAGE, status=MatchStatus.FINISHED,
                  match_date=now - timedelta(minutes=200)),    # ya finalizado
        ])
        await session.commit()
    async with TestSessionLocal() as db:
        assert await match_crud.has_match_pending_finish(db, before=now - timedelta(minutes=105)) is True


@pytest.mark.asyncio
async def test_has_match_pending_finish_false_when_recent_or_finished():
    """False si solo hay partidos recién empezados o ya finalizados."""
    now = datetime.now(timezone.utc)
    async with TestSessionLocal() as session:
        session.add_all([
            Match(api_fixture_id=8004, home_team="C", away_team="D",
                  phase=MatchPhase.GROUP_STAGE, status=MatchStatus.LIVE,
                  match_date=now - timedelta(minutes=10)),
            Match(api_fixture_id=8005, home_team="E", away_team="F",
                  phase=MatchPhase.GROUP_STAGE, status=MatchStatus.FINISHED,
                  match_date=now - timedelta(minutes=200)),
        ])
        await session.commit()
    async with TestSessionLocal() as db:
        assert await match_crud.has_match_pending_finish(db, before=now - timedelta(minutes=105)) is False


@pytest.mark.asyncio
async def test_sync_fixtures_skips_when_nothing_pending(monkeypatch):
    """No consulta la API si no hay partido por terminar y ya sincronizó hace poco."""
    calls = {"n": 0}
    async def counting_fetch(*a, **k):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_fixtures", counting_fetch)
    monkeypatch.setattr(scheduler_module, "_last_fixtures_fetch",
                        datetime.now(timezone.utc) - timedelta(minutes=1))
    await scheduler_module.sync_fixtures()
    assert calls["n"] == 0


@pytest.mark.asyncio
async def test_sync_fixtures_fetches_while_match_in_play(monkeypatch):
    """Consulta la API mientras haya un partido EN JUEGO (kickoff pasado, aún en vivo),
    aunque acabe de sincronizar → near-real-time durante el partido."""
    calls = {"n": 0}
    async def counting_fetch(*a, **k):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_fixtures", counting_fetch)
    monkeypatch.setattr(scheduler_module, "_last_fixtures_fetch", datetime.now(timezone.utc))
    async with TestSessionLocal() as session:
        session.add(Match(api_fixture_id=8006, home_team="A", away_team="B",
                          phase=MatchPhase.GROUP_STAGE, status=MatchStatus.LIVE,
                          match_date=datetime.now(timezone.utc) - timedelta(minutes=30)))
        await session.commit()
    await scheduler_module.sync_fixtures()
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_sync_fixtures_failure_keeps_idle_clock(monkeypatch):
    """Un fetch fallido NO avanza _last_fixtures_fetch: el respaldo idle sigue activo
    y se reintenta en la próxima corrida en vez de quedarse con datos viejos."""
    monkeypatch.setattr(scheduler_module.settings, "JOB_MAX_RETRIES", 1)
    async def failing_fetch(*a, **k):
        raise RequestError("boom")
    monkeypatch.setattr(football_api, "fetch_fixtures", failing_fetch)
    monkeypatch.setattr(scheduler_module, "_last_fixtures_fetch", None)  # idle_due -> consulta
    await scheduler_module.sync_fixtures()
    assert scheduler_module._last_fixtures_fetch is None


def test_parse_fixture_finish_fallback_group_stage():
    """Un partido de grupos aún LIVE pasado el plazo de finalización (135 min) se da por finalizado."""
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    raw = _raw_fixture(9001, home_score=0, away_score=1, status="1H",
                       round_="Group Stage - 1", date=old)
    assert football_api.parse_fixture(raw)["status"] == MatchStatus.FINISHED


def test_parse_fixture_no_fallback_for_knockout():
    """En eliminatorias manda la API (prórroga/penales pueden superar el plazo): sigue LIVE."""
    old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    raw = _raw_fixture(9002, home_score=1, away_score=1, status="ET",
                       round_="Round of 16", date=old)
    assert football_api.parse_fixture(raw)["status"] == MatchStatus.LIVE


def test_parse_fixture_no_fallback_within_window():
    """Un partido de grupos aún dentro del plazo (a 2 h, antes de los 135 min) sigue
    LIVE: no se finaliza prematuramente por ir en añadido largo."""
    within = (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat()
    raw = _raw_fixture(9003, home_score=0, away_score=0, status="2H",
                       round_="Group Stage - 1", date=within)
    assert football_api.parse_fixture(raw)["status"] == MatchStatus.LIVE


@pytest.mark.asyncio
async def test_sync_first_goals_skips_failed_fixtures(monkeypatch):
    """Si la consulta de eventos falla para un partido, los demás se procesan
    igual (return_exceptions): un fallo aislado no aborta todo el lote."""
    async with TestSessionLocal() as session:
        session.add_all([
            Match(
                api_fixture_id=8001, home_team="Argentina", away_team="Brazil",
                home_score=1, away_score=0, phase=MatchPhase.GROUP_STAGE,
                status=MatchStatus.FINISHED,
                match_date=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
            Match(
                api_fixture_id=8002, home_team="France", away_team="Spain",
                home_score=2, away_score=1, phase=MatchPhase.GROUP_STAGE,
                status=MatchStatus.FINISHED,
                match_date=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
        ])
        await session.commit()

    async def fake_fetch_events(fixture_id: int) -> list[dict]:
        if fixture_id == 8001:
            raise RequestError("fallo de red simulado")
        return [_goal_event(777, "Mbappé", "France", elapsed=10)]

    monkeypatch.setattr(football_api, "fetch_fixture_events", fake_fetch_events)

    await scheduler_module._do_sync_first_goals()

    async with TestSessionLocal() as session:
        rows = {
            m.api_fixture_id: m
            for m in (await session.execute(select(Match))).scalars().all()
        }
        assert rows[8001].first_goal_team is None         # falló → se omite
        assert rows[8002].first_goal_team == "France"     # éxito procesado igual
        assert rows[8002].first_goal_player_id == 777
        assert rows[8002].first_goal_player == "Mbappé"


# ── SYNC PLAYERS (guard de arranque) ─────────────────────────────────────────


async def _seed_full_coverage() -> None:
    """Estado coherente y completo: cada selección con plantilla, reciente."""
    async with TestSessionLocal() as session:
        await session.execute(delete(Player))
        await session.execute(delete(Team))
        session.add(Team(api_team_id=1, name="Argentina"))
        session.add(Player(api_player_id=10, name="L. Messi", team_api_id=1, team_name="Argentina"))
        await session.commit()


@pytest.mark.asyncio
async def test_sync_players_startup_skips_when_fresh(monkeypatch):
    """El sync de arranque se omite si las plantillas están frescas y completas —
    no re-quema cuota de API en cada reinicio/redeploy."""
    calls = {"n": 0}
    async def counting_fetch(team_api_id):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_squad", counting_fetch)
    await _seed_full_coverage()

    await scheduler_module.sync_players(skip_if_fresh=True)
    assert calls["n"] == 0  # frescas y completas → no consultó la API


@pytest.mark.asyncio
async def test_sync_players_startup_runs_when_empty(monkeypatch):
    """Con plantillas vacías (primer arranque) el sync de arranque sí corre."""
    calls = {"n": 0}
    async def counting_fetch(team_api_id):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_squad", counting_fetch)
    async with TestSessionLocal() as session:
        await session.execute(delete(Player))  # vaciar plantillas (hay selecciones sembradas)
        await session.commit()

    await scheduler_module.sync_players(skip_if_fresh=True)
    assert calls["n"] >= 1  # sin plantillas frescas → sincroniza


@pytest.mark.asyncio
async def test_sync_players_startup_runs_on_partial_coverage(monkeypatch):
    """Si un fallo parcial dejó una selección sin plantilla, el arranque NO se omite
    (reintenta) aunque otras plantillas sean recientes."""
    calls = {"n": 0}
    async def counting_fetch(team_api_id):
        calls["n"] += 1
        return []
    monkeypatch.setattr(football_api, "fetch_squad", counting_fetch)
    async with TestSessionLocal() as session:
        await session.execute(delete(Player))
        await session.execute(delete(Team))
        session.add_all([Team(api_team_id=1, name="Argentina"), Team(api_team_id=2, name="Brazil")])
        session.add(Player(api_player_id=10, name="L. Messi", team_api_id=1, team_name="Argentina"))
        await session.commit()  # Brazil sin plantilla → cobertura incompleta

    await scheduler_module.sync_players(skip_if_fresh=True)
    assert calls["n"] >= 1  # incompleto → sincroniza
