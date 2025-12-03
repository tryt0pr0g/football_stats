from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select

from app.ORMmodels.models import PlayerModel, PlayerMatchStatModel


class StatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_players(self, players_data: List[Dict[str, Any]]) -> Dict[str, int]:
        if not players_data:
            return {}

        stmt = insert(PlayerModel).values(players_data)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['fbref_id'],
            set_={
                "name": stmt.excluded.name,
                "country": stmt.excluded.country
            }
        )
        await self.session.execute(upsert_stmt)

        player_fbref_ids = [p['fbref_id'] for p in players_data]

        stmt_map = select(PlayerModel.fbref_id, PlayerModel.id).where(
            PlayerModel.fbref_id.in_(player_fbref_ids)
        )

        result = await self.session.execute(stmt_map)

        return {row.fbref_id: row.id for row in result.all()}

    async def upsert_stats(self, stats_data: List[Dict[str, Any]]) -> int:
        if not stats_data:
            return 0

        stmt = insert(PlayerMatchStatModel).values(stats_data)

        update_cols = {col.name: col for col in stmt.excluded if col.name not in ['id', 'match_id', 'player_id']}

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['match_id', 'player_id'],
            set_=update_cols
        )

        await self.session.execute(upsert_stmt)
        return len(stats_data)