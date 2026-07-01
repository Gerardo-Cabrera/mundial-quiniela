from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    team_name: str
    total_points: int
    predictions_count: int
