from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.participant_team import ParticipantTeam


class ParticipantTeamCRUD:
    async def get_all_names(self, db: AsyncSession) -> list[str]:
        """Nombres de los equipos participantes, ordenados alfabéticamente."""
        result = await db.execute(
            select(ParticipantTeam.name).order_by(ParticipantTeam.name)
        )
        return [row[0] for row in result.all()]

    async def exists(self, db: AsyncSession, name: str) -> bool:
        """¿Existe un equipo participante con ese nombre exacto?"""
        result = await db.execute(
            select(ParticipantTeam.id).where(ParticipantTeam.name == name)
        )
        return result.first() is not None


participant_team_crud = ParticipantTeamCRUD()
