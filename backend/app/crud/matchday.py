from collections import defaultdict
from datetime import date, tzinfo
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.user import User
from app.core.time import as_utc
from app.schemas.matchday import (
    MatchdayEntry, MatchdayUserPoints, MatchdaysSummary, MvpRankEntry,
)


class MatchdayCRUD:
    async def get_summary(self, db: AsyncSession, tz: tzinfo) -> MatchdaysSummary:
        """Puntos por participante y MVP(s) de cada jornada, más el ranking de MVPs.
        La jornada = día calendario del partido en la zona del torneo. Solo cuenta
        predicciones ya calculadas (partido finalizado y puntuado)."""
        result = await db.execute(
            select(User.id, User.team_name, Match.match_date, Prediction.points_earned)
            .select_from(Prediction).join(Match).join(User)
            .where(Prediction.is_calculated.is_(True))
        )

        # día -> user_id -> [team_name, puntos acumulados ese día]
        by_day: dict[date, dict[int, list]] = defaultdict(dict)
        for user_id, team_name, match_date, points in result.all():
            day = as_utc(match_date).astimezone(tz).date()
            acc = by_day[day].setdefault(user_id, [team_name, 0])
            acc[1] += points

        days: list[MatchdayEntry] = []
        mvp_counts: dict[str, int] = defaultdict(int)
        for day in sorted(by_day):
            entries = sorted(
                (MatchdayUserPoints(user_id=uid, team_name=tn, points=pts)
                 for uid, (tn, pts) in by_day[day].items()),
                key=lambda e: (-e.points, e.team_name),
            )
            top = entries[0].points if entries else 0
            mvps = [e.team_name for e in entries if e.points == top] if top > 0 else []
            for tn in mvps:
                mvp_counts[tn] += 1
            days.append(MatchdayEntry(date=day, entries=entries, mvp_points=top, mvps=mvps))

        mvp_ranking = sorted(
            (MvpRankEntry(team_name=tn, count=c) for tn, c in mvp_counts.items()),
            key=lambda r: (-r.count, r.team_name),
        )
        return MatchdaysSummary(days=days, mvp_ranking=mvp_ranking)


matchday_crud = MatchdayCRUD()
