from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    team_name: str
    total_points: int
    predictions_count: int
