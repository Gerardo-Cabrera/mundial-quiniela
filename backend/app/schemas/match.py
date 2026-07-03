from pydantic import BaseModel
from datetime import datetime
from app.models.match import MatchPhase, MatchStatus
from typing import Optional


class MatchOut(BaseModel):
    id: int
    api_fixture_id: int
    home_team: str
    away_team: str
    home_team_logo: Optional[str]
    away_team_logo: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    elapsed: Optional[int]
    first_goal_team: Optional[str]
    first_goal_player_id: Optional[int]
    first_goal_player: Optional[str]
    phase: MatchPhase
    status: MatchStatus
    match_date: datetime

    model_config = {"from_attributes": True}
