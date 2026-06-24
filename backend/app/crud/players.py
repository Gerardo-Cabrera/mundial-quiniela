from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.player import Player
from app.crud._upsert import upsert_by_key


class PlayerCRUD:
    async def get_for_teams(
        self, db: AsyncSession, team_names: list[str], name_query: str | None = None
    ) -> list[Player]:
        """Jugadores de los equipos dados (para el selector de primer goleador),
        ordenados por equipo y nombre. `name_query` (opcional) filtra por subcadena
        del nombre, sin distinguir mayúsculas (sirve para nombre y/o apellido)."""
        if not team_names:
            return []
        stmt = select(Player).where(Player.team_name.in_(team_names))
        query = (name_query or "").strip()
        if query:
            # Escapa los comodines de LIKE (\ primero, luego % y _) para tratar la
            # entrada como subcadena LITERAL, no como patrón (si no, 'search=%'
            # equivaldría a "sin filtro").
            pattern = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            stmt = stmt.where(Player.name.ilike(f"%{pattern}%", escape="\\"))
        result = await db.execute(stmt.order_by(Player.team_name, Player.name))
        return list(result.scalars().all())

    async def get_by_api_id(self, db: AsyncSession, api_player_id: int) -> Player | None:
        result = await db.execute(
            select(Player).where(Player.api_player_id == api_player_id)
        )
        return result.scalar_one_or_none()

    async def upsert_many(self, db: AsyncSession, players: list[dict]) -> int:
        """Inserta o actualiza jugadores por `api_player_id`. Idempotente."""
        return await upsert_by_key(db, Player, players, "api_player_id")

    async def last_synced_at(self, db: AsyncSession) -> datetime | None:
        """`max(updated_at)` de la tabla, o None si está vacía. Permite saltar el
        sync de plantillas en el arranque si ya están frescas."""
        return await db.scalar(select(func.max(Player.updated_at)))


player_crud = PlayerCRUD()
