from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.team import Team


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
        """
        Inserta o actualiza selecciones por api_team_id. Retorna cuántas se
        procesaron. Idempotente: reejecutable sin duplicar.
        """
        result = await db.execute(select(Team))
        existing = {t.api_team_id: t for t in result.scalars().all()}

        for parsed in teams:
            team = existing.get(parsed["api_team_id"])
            if team:
                for key, value in parsed.items():
                    setattr(team, key, value)
            else:
                db.add(Team(**parsed))
        await db.flush()
        return len(teams)


team_crud = TeamCRUD()
