from pydantic import BaseModel, Field
from typing import Optional
from app.schemas.match import MatchOut


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    # Pronóstico del primer goleador: id de API-Football del jugador (debe jugar
    # en uno de los dos equipos del partido). Opcional.
    first_goal_player_id: Optional[int] = Field(default=None)


class PredictionBackfillRequest(BaseModel):
    """Carga admin de pronósticos de un participante para partidos ya jugados
    (el torneo empezó y los pronósticos se hicieron antes del kickoff).
    Cada item tiene la misma forma que PredictionCreate."""
    team_name: str = Field(min_length=1, max_length=100)
    predictions: list[PredictionCreate] = Field(min_length=1)


class PredictionOut(BaseModel):
    id: int
    match_id: int
    predicted_home: int
    predicted_away: int
    first_goal_player_id: Optional[int]
    first_goal_player: Optional[str]
    points_earned: int
    is_calculated: bool
    match: MatchOut

    model_config = {"from_attributes": True}
