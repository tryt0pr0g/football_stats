from app.database.db import AsyncSessionLocal
from fastapi import Depends
from typing import Annotated




async def get_session():
    async with AsyncSessionLocal() as session:
        yield session

Session = Annotated[AsyncSessionLocal, Depends(get_session)]