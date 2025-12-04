from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, func

from app.schemes.team_shemes import RequestTeamScheme
from app.ORMmodels.models import TeamModel, PlayerModel, PlayerMatchStatModel


class TeamRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_teams(self, teams_data: List[Dict[str, Any]]) -> int:
        if not teams_data:
            return 0

        stmt = insert(TeamModel).values(teams_data)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['fbref_id'],
            set_={
                "title": stmt.excluded.title,
                "logo_url": stmt.excluded.logo_url,
                "last_updated": func.now()
            }
        )

        await self.session.execute(upsert_stmt)
        return len(teams_data)

    async def get_all(self, limit: int = 1000, offset: int = 0) -> List[TeamModel]:
        stmt = select(TeamModel).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_fbref_id_map(self) -> Dict[str, int]:
        stmt = select(TeamModel.fbref_id, TeamModel.id)
        result = await self.session.execute(stmt)
        return {row.fbref_id: row.id for row in result.all() if row.fbref_id}

    async def get_team_with_players(self, team: RequestTeamScheme) -> Optional[TeamModel]:
        stmt_team = select(TeamModel).where(TeamModel.title == team.title)
        result_team = await self.session.execute(stmt_team)
        team_obj = result_team.scalar_one_or_none()

        if not team_obj:
            return None

        stmt_players = (
            select(PlayerModel)
            .join(PlayerMatchStatModel, PlayerModel.id == PlayerMatchStatModel.player_id)
            .where(PlayerMatchStatModel.team_id == team_obj.id)
            .distinct()
        )

        result_players = await self.session.execute(stmt_players)
        players = result_players.scalars().all()

        team_obj.players = players

        return team_obj