from datetime import datetime
from pydantic import BaseModel


class UserCount(BaseModel):
    team_name: str
    count: int


class FirstGoalMatch(BaseModel):
    match_id: int
    home_team: str
    away_team: str
    match_date: datetime
    scorer: str | None          # goleador real del primer gol
    hitters: list[str]          # equipos que lo acertaron (puede ir vacío)


class ScoreCount(BaseModel):
    score: str                  # "2-1"
    count: int


class StatsSummary(BaseModel):
    first_goal_matches: list[FirstGoalMatch]  # resueltos, más reciente primero
    first_goal_ranking: list[UserCount]        # aciertos de primer gol por usuario (desc)
    top_scores: list[ScoreCount]               # marcador(es) real(es) más repetido(s)
    exact_ranking: list[UserCount]             # aciertos de marcador exacto por usuario (desc)
