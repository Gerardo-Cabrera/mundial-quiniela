from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Team(Base):
    """
    Selección del Mundial sincronizada desde API-Football. Es la fuente de verdad
    de qué selecciones existen y con qué nombre exacto, para los pronósticos de
    cada jornada y el catálogo de equipos.
    """
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    api_team_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    # name: nombre EXACTO de API-Football (en inglés). Debe coincidir con el de
    # los partidos para que los pronósticos cuadren.
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
