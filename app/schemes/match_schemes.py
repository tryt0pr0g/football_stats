from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional

class ResponseMatchScheme(BaseModel):
    id: int
    date: date
    season: str
    home_team_name: str
    away_team_name: str
    home_score: Optional[int]
    away_score: Optional[int]
    home_xg: Optional[float]
    away_xg: Optional[float]
    is_finished: bool

    model_config = ConfigDict(from_attributes=True)