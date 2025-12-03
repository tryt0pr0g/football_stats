from pydantic import BaseModel, ConfigDict
from typing import Optional


class PlayerSchema(BaseModel):
    id: int
    name: str
    country: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)