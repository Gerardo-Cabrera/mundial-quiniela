from sqlalchemy import Integer, ForeignKey, String, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_prediction_user_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), index=True)

    predicted_home: Mapped[int] = mapped_column(Integer)
    predicted_away: Mapped[int] = mapped_column(Integer)
    # Pronóstico del PRIMER GOLEADOR: id del jugador (se puntúa por id) + su
    # nombre, denormalizado para mostrarlo sin un join.
    first_goal_player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_goal_player: Mapped[str | None] = mapped_column(String(100), nullable=True)

    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    is_calculated: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="predictions")
    match: Mapped["Match"] = relationship(back_populates="predictions")
