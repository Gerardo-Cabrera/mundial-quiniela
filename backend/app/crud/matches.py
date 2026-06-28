from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction
from app.crud._upsert import upsert_by_key


def _as_utc(dt: datetime) -> datetime:
    """Normaliza a UTC-aware (SQLite devuelve naive; PostgreSQL, aware)."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class MatchCRUD:
    async def get_all(
        self,
        db: AsyncSession,
        *,
        phase: MatchPhase | None = None,
        status: MatchStatus | None = None,
    ) -> list[Match]:
        query = select(Match).order_by(Match.match_date)
        if phase:
            query = query.where(Match.phase == phase)
        if status:
            query = query.where(Match.status == status)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, match_id: int) -> Match | None:
        result = await db.execute(select(Match).where(Match.id == match_id))
        return result.scalar_one_or_none()

    async def get_day_first_kickoff(
        self, db: AsyncSession, match_date: datetime, tz: ZoneInfo
    ) -> datetime:
        """Kickoff más temprano del día (en `tz`) al que pertenece `match_date`.

        El día se calcula en la zona del torneo (no UTC) para que los partidos
        nocturnos no caigan en jornadas distintas. Acota la búsqueda a una ventana
        de ±1 día UTC (una jornada cabe de sobra) y filtra en Python → cross-DB
        (no usa funciones de zona horaria de SQL, que SQLite no tiene)."""
        ref = _as_utc(match_date)
        day = ref.astimezone(tz).date()
        result = await db.execute(
            select(Match.match_date).where(
                Match.match_date >= ref - timedelta(days=1),
                Match.match_date <= ref + timedelta(days=1),
            )
        )
        kickoffs = [
            _as_utc(d) for (d,) in result.all()
            if _as_utc(d).astimezone(tz).date() == day
        ]
        return min(kickoffs) if kickoffs else ref

    async def has_match_pending_finish(self, db: AsyncSession, *, before: datetime) -> bool:
        """¿Hay algún partido SCHEDULED/LIVE cuyo kickoff fue antes de `before`?

        Con `before=now` significa "hay un partido EN JUEGO" (kickoff pasado y aún sin
        FINISHED): mientras devuelva True conviene consultar la API seguido para reflejar
        marcador / primer gol / FT casi en tiempo real. Excluye FINISHED y POSTPONED para
        no consultar indefinidamente.
        """
        result = await db.execute(
            select(Match.id)
            .where(
                Match.status.in_([MatchStatus.SCHEDULED, MatchStatus.LIVE]),
                Match.match_date <= before,
            )
            .limit(1)
        )
        return result.first() is not None

    async def upsert_many(
        self, db: AsyncSession, fixtures: list[dict]
    ) -> tuple[int, list[int]]:
        """Inserta o actualiza partidos por api_fixture_id. Idempotente.

        Devuelve `(procesados, recien_finalizados)`: el segundo es la lista de ids
        de partidos que ACABAN de transicionar a FINISHED en este lote (estaban
        SCHEDULED/LIVE y ahora están FINISHED). El scheduler la usa para encadenar
        de inmediato el primer gol y el cálculo de puntos (pipeline near-real-time),
        sin esperar a los timers periódicos. Solo se detectan transiciones en
        UPDATES (un partido ya existente); un fixture insertado directo como FINISHED
        lo cubren los jobs de arranque.

        Si un partido ya FINISHED cambia de marcador (p. ej. el fallback de
        finalización lo marcó FINISHED con un marcador no-final, o la API lo
        corrige tarde) sus predicciones ya calculadas quedan con puntos obsoletos:
        se marcan para recálculo (igual que sync_first_goals)."""
        rescored_ids: list[int] = []
        newly_finished_ids: list[int] = []

        def _track_status_and_score(match: Match, parsed: dict) -> None:
            if parsed["status"] != MatchStatus.FINISHED:
                return
            if match.status != MatchStatus.FINISHED:
                newly_finished_ids.append(match.id)
            if (
                parsed["home_score"] != match.home_score
                or parsed["away_score"] != match.away_score
            ):
                rescored_ids.append(match.id)

        count = await upsert_by_key(
            db, Match, fixtures, "api_fixture_id", on_update=_track_status_and_score
        )

        if rescored_ids:
            await db.execute(
                update(Prediction)
                .where(
                    Prediction.match_id.in_(rescored_ids),
                    Prediction.is_calculated == True,  # noqa: E712
                )
                .values(is_calculated=False, points_earned=0)
            )
        return count, newly_finished_ids


match_crud = MatchCRUD()
