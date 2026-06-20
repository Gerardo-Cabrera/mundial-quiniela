from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class ParticipantTeam(Base):
    """
    Equipo de un participante de la quiniela: los nombres con los que se registran
    los jugadores (p. ej. "Jax FC"). Es la fuente de verdad para validar el
    registro y para listar los equipos disponibles. NO son selecciones del Mundial
    (esas viven en la tabla `teams`). Se siembra en la migración 0003.
    """
    __tablename__ = "participant_teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
