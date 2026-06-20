from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Player(Base):
    """
    Jugador de una selección del Mundial, sincronizado desde API-Football
    (`/players/squads`). Es la fuente de verdad para el pronóstico del PRIMER
    GOLEADOR: el usuario elige un jugador de las plantillas de los dos equipos del
    partido y el scoring compara por `api_player_id` (robusto, sin ambigüedad de
    nombres) contra el goleador real que entrega la API en los eventos del partido.
    """
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # api_player_id: el MISMO id que la API usa en los eventos de gol → permite
    # puntuar comparando ids en vez de nombres.
    api_player_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))

    # Equipo (selección) al que pertenece. Se denormaliza el nombre para validar el
    # pronóstico (el jugador debe jugar en uno de los dos equipos del partido) y
    # para agrupar en el selector del frontend sin un join extra.
    team_api_id: Mapped[int] = mapped_column(Integer, index=True)
    team_name: Mapped[str] = mapped_column(String(100), index=True)

    position: Mapped[str | None] = mapped_column(String(30), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
