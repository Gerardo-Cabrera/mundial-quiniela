from sqlalchemy import String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
import enum


class MatchPhase(str, enum.Enum):
    GROUP_STAGE = "group_stage"
    ROUND_OF_32 = "round_of_32"
    ROUND_OF_16 = "round_of_16"
    QUARTER_FINALS = "quarter_finals"
    SEMI_FINALS = "semi_finals"
    THIRD_PLACE = "third_place"
    FINAL = "final"


class MatchStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    FINISHED = "finished"
    POSTPONED = "postponed"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    api_fixture_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)

    home_team: Mapped[str] = mapped_column(String(100))
    away_team: Mapped[str] = mapped_column(String(100))
    home_team_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    away_team_logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minuto de juego en vivo (API-Football status.elapsed); None fuera de juego.
    elapsed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Primer gol del partido (resuelto por el job de eventos). `first_goal_team`
    # es el equipo del goleador (informativo y marca de "ya resuelto");
    # `first_goal_player_id`/`first_goal_player` son el goleador real, que es
    # contra quien se puntúa el pronóstico de primer goleador.
    first_goal_team: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_goal_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_goal_player: Mapped[str | None] = mapped_column(String(100), nullable=True)

    phase: Mapped[MatchPhase] = mapped_column(SAEnum(MatchPhase), default=MatchPhase.GROUP_STAGE)
    status: Mapped[MatchStatus] = mapped_column(SAEnum(MatchStatus), default=MatchStatus.SCHEDULED)

    match_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match", lazy="select")
