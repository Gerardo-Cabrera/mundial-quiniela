from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.team import Team
from app.crud._upsert import upsert_by_key


class TeamCRUD:
    async def get_all(self, db: AsyncSession) -> list[Team]:
        """Todas las selecciones (para sincronizar sus plantillas)."""
        result = await db.execute(select(Team).order_by(Team.name))
        return list(result.scalars().all())

    async def get_all_names(self, db: AsyncSession) -> list[str]:
        """Nombres de las selecciones ordenados alfabéticamente."""
        result = await db.execute(select(Team.name).order_by(Team.name))
        return [row[0] for row in result.all()]

    async def upsert_many(self, db: AsyncSession, teams: list[dict]) -> int:
        """Inserta o actualiza selecciones por api_team_id. Idempotente."""
        return await upsert_by_key(db, Team, teams, "api_team_id")


team_crud = TeamCRUD()
