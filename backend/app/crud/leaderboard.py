from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.leaderboard import LeaderboardEntry


class LeaderboardCRUD:
    async def get_leaderboard(self, db: AsyncSession) -> list[LeaderboardEntry]:
        match_pts_q = (
            select(
                Prediction.user_id,
                func.coalesce(func.sum(Prediction.points_earned), 0).label("match_points"),
                func.count(Prediction.id).label("predictions_count"),
            )
            .group_by(Prediction.user_id)
            .subquery()
        )

        result = await db.execute(
            select(
                User.id,
                User.team_name,
                func.coalesce(match_pts_q.c.match_points, 0).label("total_points"),
                func.coalesce(match_pts_q.c.predictions_count, 0).label("predictions_count"),
            )
            .outerjoin(match_pts_q, User.id == match_pts_q.c.user_id)
            .order_by(
                func.coalesce(match_pts_q.c.match_points, 0).desc(),
                # Desempate determinista: mismo orden en cada request.
                User.team_name,
            )
        )

        rows = result.all()

        # Ranking de competición: los empatados comparten rank y el siguiente
        # salta posiciones (1, 2, 2, 4...).
        entries: list[LeaderboardEntry] = []
        rank = 0
        prev_points: int | None = None
        for i, row in enumerate(rows):
            if row.total_points != prev_points:
                rank = i + 1
                prev_points = row.total_points
            entries.append(
                LeaderboardEntry(
                    rank=rank,
                    user_id=row.id,
                    team_name=row.team_name,
                    total_points=row.total_points,
                    predictions_count=row.predictions_count,
                )
            )
        return entries


leaderboard_crud = LeaderboardCRUD()
