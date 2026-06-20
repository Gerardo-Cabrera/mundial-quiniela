from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.player import Player


class PlayerCRUD:
    async def get_for_teams(self, db: AsyncSession, team_names: list[str]) -> list[Player]:
        """Jugadores de los equipos dados (para el selector de primer goleador),
        ordenados por equipo y nombre."""
        if not team_names:
            return []
        result = await db.execute(
            select(Player)
            .where(Player.team_name.in_(team_names))
            .order_by(Player.team_name, Player.name)
        )
        return list(result.scalars().all())

    async def get_by_api_id(self, db: AsyncSession, api_player_id: int) -> Player | None:
        result = await db.execute(
            select(Player).where(Player.api_player_id == api_player_id)
        )
        return result.scalar_one_or_none()

    async def upsert_many(self, db: AsyncSession, players: list[dict]) -> int:
        """Inserta o actualiza jugadores por `api_player_id`. Idempotente."""
        result = await db.execute(select(Player))
        existing = {p.api_player_id: p for p in result.scalars().all()}

        for parsed in players:
            player = existing.get(parsed["api_player_id"])
            if player:
                for key, value in parsed.items():
                    setattr(player, key, value)
            else:
                db.add(Player(**parsed))
        await db.flush()
        return len(players)


player_crud = PlayerCRUD()
