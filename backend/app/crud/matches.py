from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.match import Match, MatchPhase, MatchStatus
from app.models.prediction import Prediction


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

        Es decir, un partido que ya pudo haber terminado y aún no está FINISHED.
        Define la "ventana de finalización": mientras devuelva True conviene consultar
        la API seguido para captar el `FT` a tiempo. Excluye FINISHED y POSTPONED para
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

    async def upsert_many(self, db: AsyncSession, fixtures: list[dict]) -> int:
        """
        Inserta o actualiza partidos por api_fixture_id. Retorna cuántos se
        procesaron. Idempotente: reejecutable sin duplicar.

        Carga los partidos existentes en UNA sola query y resuelve el upsert en
        memoria (evita el patrón N+1 de un SELECT por fixture).
        """
        if not fixtures:
            return 0

        result = await db.execute(select(Match))
        existing = {m.api_fixture_id: m for m in result.scalars().all()}

        rescored_ids: list[int] = []
        for parsed in fixtures:
            match = existing.get(parsed["api_fixture_id"])
            if match:
                # Un partido ya FINISHED cuyo marcador cambia (p. ej. el fallback de
                # finalización lo marcó FINISHED con un marcador no-final, o la API lo
                # corrige tarde) deja con puntos obsoletos a sus predicciones ya
                # calculadas: se marcan para recálculo (igual que sync_first_goals).
                if parsed["status"] == MatchStatus.FINISHED and (
                    parsed["home_score"] != match.home_score
                    or parsed["away_score"] != match.away_score
                ):
                    rescored_ids.append(match.id)
                for key, value in parsed.items():
                    setattr(match, key, value)
            else:
                db.add(Match(**parsed))

        if rescored_ids:
            await db.execute(
                update(Prediction)
                .where(
                    Prediction.match_id.in_(rescored_ids),
                    Prediction.is_calculated == True,  # noqa: E712
                )
                .values(is_calculated=False, points_earned=0)
            )
        await db.flush()
        return len(fixtures)


match_crud = MatchCRUD()
