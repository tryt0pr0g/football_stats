from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from typing import List, Dict, Any

from app.ORMmodels.models import LeagueModel


class LeagueRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_leagues(self, leagues_data: List[Dict[str, Any]]) -> int:
        if not leagues_data:
            return 0

        stmt = insert(LeagueModel).values(leagues_data)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['slug'],
            set_={
                "title": stmt.excluded.title,
                "country": stmt.excluded.country,
                "fbref_id": stmt.excluded.fbref_id
            }
        )

        await self.session.execute(upsert_stmt)
        await self.session.commit()
        return len(leagues_data)

    async def get_all(self) -> List[LeagueModel]:
        result = await self.session.execute(select(LeagueModel))
        return result.scalars().all()