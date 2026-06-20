from pydantic import BaseModel
from typing import Optional


class PlayerOut(BaseModel):
    api_player_id: int
    name: str
    team_name: str
    position: Optional[str] = None

    model_config = {"from_attributes": True}
