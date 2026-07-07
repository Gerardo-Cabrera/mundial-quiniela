from pydantic import BaseModel, Field, model_validator
from typing import Optional
from app.schemas.match import MatchOut


def _reject_scorer_on_goalless(predicted_home: int, predicted_away: int, first_goal_player_id: Optional[int]) -> None:
    """Un 0-0 no tiene primer gol: rechaza la combinación contradictoria (la comparten
    el flujo de usuario y el backfill)."""
    if first_goal_player_id is not None and predicted_home == 0 and predicted_away == 0:
        raise ValueError("Un pronóstico 0-0 no puede llevar primer goleador.")


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    # Pronóstico del primer goleador: id de API-Football del jugador (debe jugar
    # en uno de los dos equipos del partido). Opcional.
    first_goal_player_id: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def _check(self):
        _reject_scorer_on_goalless(self.predicted_home, self.predicted_away, self.first_goal_player_id)
        return self


class PredictionBackfillItem(BaseModel):
    """Item de backfill: identifica el partido por `match_id` **o** por el par de
    equipos (`home_team`/`away_team`), para no depender de conocer el id. El marcador se
    orienta al home/away del fixture aunque el par venga invertido."""
    match_id: Optional[int] = Field(default=None)
    home_team: Optional[str] = Field(default=None, max_length=100)
    away_team: Optional[str] = Field(default=None, max_length=100)
    predicted_home: int = Field(ge=0, le=20)
    predicted_away: int = Field(ge=0, le=20)
    first_goal_player_id: Optional[int] = Field(default=None)

    @model_validator(mode="after")
    def _check(self):
        if self.match_id is None and not (self.home_team and self.away_team):
            raise ValueError("Indica match_id, o home_team y away_team.")
        _reject_scorer_on_goalless(self.predicted_home, self.predicted_away, self.first_goal_player_id)
        return self


class PredictionBackfillRequest(BaseModel):
    """Carga admin de pronósticos de un participante para partidos ya jugados
    (el torneo empezó y los pronósticos se hicieron antes del kickoff)."""
    team_name: str = Field(min_length=1, max_length=100)
    predictions: list[PredictionBackfillItem] = Field(min_length=1)


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
