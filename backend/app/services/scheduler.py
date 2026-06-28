"""
Cron jobs para sincronizar datos del Mundial y calcular puntos automáticamente.
Se ejecuta en background al iniciar la aplicación.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select, update, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from httpx import HTTPStatusError, RequestError
from app.database import AsyncSessionLocal
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.services import football_api
from app.services.scoring import calculate_match_points
from app.crud import team_crud, match_crud, player_crud
from app.config import settings
import logging

logger = logging.getLogger(__name__)
# coalesce + misfire_grace_time: tras una pausa del proceso (suspensión del equipo
# en desarrollo, reload, pausa larga del loop) las corridas perdidas se ejecutan al
# reanudar —colapsadas en una sola— en vez de descartarse en silencio. Los jobs son
# idempotentes, por lo que la corrida tardía es segura.
scheduler = AsyncIOScheduler(
    job_defaults={
        "coalesce": True,
        "misfire_grace_time": settings.JOB_MISFIRE_GRACE_SECONDS,
    }
)

# Última vez que el sync de fixtures sincronizó CON ÉXITO con la API (no la última vez
# que cambió un dato): pacea las corridas de respaldo cuando no hay partidos por terminar.
# Un fallo no lo avanza, para reintentar pronto en lugar de quedarse con datos viejos.
_last_fixtures_fetch: datetime | None = None

# ¿La última corrida de sync_fixtures detectó algún partido que ACABA de finalizar?
# Lo escribe `_do_sync_fixtures` y lo lee `sync_fixtures` para disparar el pipeline
# event-driven (primer gol + puntos) solo en la transición a FINISHED.
_fixtures_newly_finished: bool = False


async def _retry(coro_func, job_name: str) -> bool:
    """Ejecuta una coroutine con reintentos. Devuelve True si tuvo éxito y False si
    agotó los reintentos (los jobs que no necesitan el resultado lo ignoran)."""
    max_retries = settings.JOB_MAX_RETRIES
    retry_delay = settings.JOB_RETRY_DELAY_SECONDS
    for attempt in range(1, max_retries + 1):
        try:
            await coro_func()
            return True
        except (HTTPStatusError, RequestError) as e:
            logger.warning(
                "Job %s attempt %d/%d failed (network): %s",
                job_name, attempt, max_retries, str(e),
            )
        except SQLAlchemyError as e:
            logger.warning(
                "Job %s attempt %d/%d failed (database): %s",
                job_name, attempt, max_retries, str(e),
            )
        except Exception as e:
            logger.error(
                "Job %s attempt %d/%d failed (unexpected): %s",
                job_name, attempt, max_retries, str(e),
                exc_info=True,
            )
        if attempt < max_retries:
            await asyncio.sleep(retry_delay * attempt)
    logger.error("Job %s failed after %d retries.", job_name, max_retries)
    return False


async def _do_sync_fixtures():
    global _fixtures_newly_finished
    _fixtures_newly_finished = False
    fixtures = await football_api.fetch_fixtures()
    parsed = [football_api.parse_fixture(f) for f in fixtures]
    async with AsyncSessionLocal() as db:
        count, newly_finished_ids = await match_crud.upsert_many(db, parsed)
        await db.commit()
    _fixtures_newly_finished = bool(newly_finished_ids)
    logger.info(
        "Synced %d fixtures (%d recién finalizados).", count, len(newly_finished_ids)
    )


async def sync_fixtures():
    """Sincroniza fixtures, pero **solo cuando aporta** (sync adaptativo): consulta a
    la API cada SYNC_FIXTURES_MINUTES mientras haya un partido EN JUEGO (kickoff pasado
    y aún sin FINISHED) → marcador, primer gol y FT casi en tiempo real; y de forma
    espaciada (SYNC_FIXTURES_IDLE_MINUTES) el resto del tiempo para captar kickoffs y
    fixtures nuevos. Fuera de los partidos no malgasta cuota.

    Pipeline near-real-time: tras cada corrida con éxito resuelve el **primer gol**
    (de partidos en vivo o recién finalizados → el goleador aparece ya en pleno
    partido, a la cadencia del sync) y, si algún partido ACABA de finalizar, **puntúa
    de inmediato** sin esperar al timer de 30 min. Coste acotado (la query del primer
    gol salta los ya resueltos, ~1 request/partido); los timers periódicos siguen como
    red de seguridad para cuando la API tarda en publicar los eventos."""
    global _last_fixtures_fetch
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        # En juego = kickoff ya pasado y aún sin FINISHED (incluye un SCHEDULED cuyo
        # horario llegó → detecta el saque pronto). Mientras dure, se consulta seguido.
        in_play = await match_crud.has_match_pending_finish(db, before=now)
    idle_due = (
        _last_fixtures_fetch is None
        or now - _last_fixtures_fetch >= timedelta(minutes=settings.SYNC_FIXTURES_IDLE_MINUTES)
    )
    if not (in_play or idle_due):
        return
    logger.info("Starting fixture sync...")
    if await _retry(_do_sync_fixtures, "sync_fixtures"):
        # Solo avanza el reloj de pacing si el fetch tuvo éxito: tras un fallo de
        # red/API, idle_due sigue activo y se reintenta en la próxima corrida en
        # vez de esperar SYNC_FIXTURES_IDLE_MINUTES con datos viejos.
        _last_fixtures_fetch = now
        # Resolver el primer gol en cada corrida con éxito: un partido EN VIVO que
        # acaba de marcar obtiene su goleador a la cadencia del sync (no espera al
        # timer horario ni al FT). Barato: la query salta los que ya lo tienen (~1
        # request por partido).
        await _retry(_do_sync_first_goals, "sync_first_goals")
        if _fixtures_newly_finished:
            # Recién finalizado: puntuar ya, sin esperar al timer de 30 min.
            logger.info("Partido(s) recién finalizado(s): puntuando tras el FT.")
            await _retry(_do_calculate_points, "calculate_pending_points")


async def _do_sync_teams():
    teams = await football_api.fetch_teams()
    parsed = [football_api.parse_team(t) for t in teams]
    async with AsyncSessionLocal() as db:
        count = await team_crud.upsert_many(db, parsed)
        await db.commit()
    logger.info("Synced %d teams.", count)


async def sync_teams():
    """Sincroniza las selecciones del Mundial desde API-Football a la BD.
    Se ejecuta UNA sola vez al arrancar (no cambian durante el torneo); para
    re-sincronizar manualmente existe POST /config/teams/sync."""
    logger.info("Starting teams sync...")
    await _retry(_do_sync_teams, "sync_teams")


async def _do_sync_players():
    # Las plantillas dependen de qué selecciones haya en la tabla `teams`
    # (sincronizadas antes). Una petición /players/squads por equipo, acotada
    # con un semáforo para no saturar la API.
    async with AsyncSessionLocal() as db:
        teams = await team_crud.get_all(db)
        team_ids = [t.api_team_id for t in teams]

    if not team_ids:
        logger.info("Synced 0 players (no hay selecciones en BD todavía).")
        return

    semaphore = asyncio.Semaphore(5)

    async def fetch_one(team_api_id: int) -> list[dict]:
        async with semaphore:
            return await football_api.fetch_squad(team_api_id)

    squads = await asyncio.gather(
        *(fetch_one(tid) for tid in team_ids),
        return_exceptions=True,
    )
    parsed: list[dict] = []
    for team_api_id, squad in zip(team_ids, squads):
        if isinstance(squad, Exception):
            logger.warning("No se pudo obtener la plantilla del equipo %s: %s", team_api_id, squad)
            continue
        for entry in squad:
            parsed.extend(football_api.parse_squad(entry))

    async with AsyncSessionLocal() as db:
        count = await player_crud.upsert_many(db, parsed)
        await db.commit()
    logger.info("Synced %d players.", count)


async def _players_are_fresh() -> bool:
    """Plantillas 'frescas' = sincronizadas hace < SYNC_PLAYERS_HOURS **y completas**
    (toda selección con plantilla). La completitud evita que un sync parcial —algunos
    equipos fallaron pero se comiteó el resto— omita el reintento en el arranque."""
    async with AsyncSessionLocal() as db:
        last = await player_crud.last_synced_at(db)
        if last is None:
            return False
        if last.tzinfo is None:  # SQLite devuelve naive; asumir UTC
            last = last.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - last >= timedelta(hours=settings.SYNC_PLAYERS_HOURS):
            return False
        return await player_crud.all_teams_have_players(db)


async def sync_players(*, skip_if_fresh: bool = False):
    """Sincroniza las plantillas (jugadores) de las selecciones desde API-Football.
    Refresco periódico cada ~3 días (las plantillas cambian por lesiones/altas).

    El disparo de **arranque** usa `skip_if_fresh=True`: si ya se sincronizaron hace
    < SYNC_PLAYERS_HOURS se omite, para no re-quemar cuota de API (≈1 request por
    selección) en cada reinicio/redeploy. El refresco periódico (sin el flag) corre
    siempre, así la cadencia configurada no se altera."""
    if skip_if_fresh and await _players_are_fresh():
        logger.info("Players sync de arranque omitido: plantillas ya frescas.")
        return
    logger.info("Starting players sync...")
    await _retry(_do_sync_players, "sync_players")


async def _do_sync_first_goals():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Match).where(
                # En vivo o finalizado: el primer gol es definitivo en cuanto se
                # anota, así que se resuelve ya en pleno partido (no se espera al FT).
                # Coste acotado: la condición `first_goal_team IS NULL` hace que cada
                # partido se consulte ~1 vez (al resolverse deja de aparecer).
                Match.status.in_([MatchStatus.LIVE, MatchStatus.FINISHED]),
                Match.first_goal_team.is_(None),
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
                # Partidos 0-0 no tienen primer gol: no consultar eventos.
                (Match.home_score + Match.away_score) > 0,
            )
        )
        matches = result.scalars().all()

        semaphore = asyncio.Semaphore(5)

        async def fetch_events(fixture_id: int) -> list[dict]:
            async with semaphore:
                return await football_api.fetch_fixture_events(fixture_id)

        # return_exceptions: el fallo de un fixture (red, datos) NO aborta el
        # lote; se omite ese partido y se reintentará en la próxima corrida.
        events_per_match = await asyncio.gather(
            *(fetch_events(m.api_fixture_id) for m in matches),
            return_exceptions=True,
        )
        updated = 0
        for match, events in zip(matches, events_per_match):
            if isinstance(events, Exception):
                logger.warning(
                    "No se pudieron obtener eventos del fixture %s: %s",
                    match.api_fixture_id, events,
                )
                continue
            scorer = football_api.get_first_goal_scorer(events)
            if scorer is None:
                continue
            match.first_goal_team = scorer["team"]
            match.first_goal_player_id = scorer["player_id"]
            match.first_goal_player = scorer["player_name"]
            updated += 1
            # Auto-reparación: si alguna predicción ya fue puntuada sin este
            # dato (p.ej. por el plazo de gracia), se recalcula en el próximo job.
            await db.execute(
                update(Prediction)
                .where(
                    Prediction.match_id == match.id,
                    Prediction.is_calculated == True,  # noqa: E712
                )
                .values(is_calculated=False, points_earned=0)
            )

        await db.commit()
        logger.info("Updated first goals for %d matches.", updated)


async def sync_first_goals():
    """Para partidos finalizados sin primer gol, consulta eventos. Se ejecuta cada hora."""
    logger.info("Starting first goals sync...")
    await _retry(_do_sync_first_goals, "sync_first_goals")


async def _do_calculate_points():
    # No puntuar hasta conocer el primer gol (el sync de goles corre cada hora
    # y este job cada 30 min); si la API no lo entrega dentro del plazo de
    # gracia, se calcula sin él para no dejar puntos bloqueados.
    grace_cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.FIRST_GOAL_GRACE_HOURS
    )
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Prediction)
            .join(Match)
            .where(
                Match.status == MatchStatus.FINISHED,
                Prediction.is_calculated == False,  # noqa: E712
                or_(
                    Match.first_goal_team.is_not(None),
                    # Partidos 0-0 no tienen primer gol que esperar.
                    (Match.home_score + Match.away_score) == 0,
                    Match.match_date < grace_cutoff,
                ),
            )
            .options(selectinload(Prediction.match))
        )
        predictions = result.scalars().all()

        for pred in predictions:
            match = pred.match
            if match.home_score is None or match.away_score is None:
                continue

            breakdown = calculate_match_points(
                predicted_home=pred.predicted_home,
                predicted_away=pred.predicted_away,
                predicted_first_goal_player_id=pred.first_goal_player_id,
                actual_home=match.home_score,
                actual_away=match.away_score,
                actual_first_goal_player_id=match.first_goal_player_id,
                phase=match.phase,
            )
            pred.points_earned = breakdown["total"]
            pred.is_calculated = True

        await db.commit()
        logger.info("Calculated points for %d predictions.", len(predictions))


async def calculate_pending_points():
    """Calcula puntos de predicciones de partidos finalizados. Se ejecuta cada 30 minutos."""
    logger.info("Starting points calculation...")
    await _retry(_do_calculate_points, "calculate_pending_points")


def start_scheduler():
    # next_run_time: primera ejecución al arrancar (IntervalTrigger solo
    # dispararía tras el primer intervalo), escalonada para que los fixtures
    # lleguen antes que goles/puntos y sin golpear la API en paralelo.
    now = datetime.now()
    # Las selecciones no cambian durante el torneo → sync UNA sola vez al arrancar
    # (re-sync manual disponible vía POST /config/teams/sync). Las plantillas sí
    # cambian (lesiones, altas) → cada pocos días. Ambas antes que goles/puntos.
    scheduler.add_job(sync_teams,          DateTrigger(run_date=now),                               id="sync_teams",      replace_existing=True)
    # Plantillas: el refresco periódico siempre corre (cadencia intacta); el sync de
    # arranque es un one-shot que se OMITE si ya están frescas (no re-quema cuota en
    # cada reinicio). Por eso el periódico arranca a un intervalo completo, no a los 10s.
    scheduler.add_job(sync_players,        DateTrigger(run_date=now + timedelta(seconds=10)),       id="sync_players_startup", replace_existing=True, kwargs={"skip_if_fresh": True})
    scheduler.add_job(sync_players,        IntervalTrigger(hours=settings.SYNC_PLAYERS_HOURS),      id="sync_players",    replace_existing=True, next_run_time=now + timedelta(hours=settings.SYNC_PLAYERS_HOURS))
    scheduler.add_job(sync_fixtures,       IntervalTrigger(minutes=settings.SYNC_FIXTURES_MINUTES), id="sync_fixtures",   replace_existing=True, next_run_time=now + timedelta(seconds=20))
    scheduler.add_job(sync_first_goals,         IntervalTrigger(hours=settings.SYNC_GOALS_HOURS),        id="sync_goals",      replace_existing=True, next_run_time=now + timedelta(seconds=50))
    scheduler.add_job(calculate_pending_points, IntervalTrigger(minutes=settings.CALC_POINTS_MINUTES),   id="calc_points",     replace_existing=True, next_run_time=now + timedelta(seconds=80))
    scheduler.start()
    logger.info("Scheduler started with 6 jobs.")


def stop_scheduler():
    scheduler.shutdown()
