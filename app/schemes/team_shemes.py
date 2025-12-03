from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from app.schemes.player_schemes import PlayerSchema


class RequestTeamScheme(BaseModel):
    title: str

    model_config = ConfigDict(from_attributes=True)


class PaginationShm(BaseModel):
    offset: int = Field(ge=0, default=0)
    limit: int = Field(ge=0, default=100)


class ResponseTeamScheme(BaseModel):
    id: int
    title: str
    logo_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ResponseTeamInfoScheme(ResponseTeamScheme):
    players: List[PlayerSchema] = []