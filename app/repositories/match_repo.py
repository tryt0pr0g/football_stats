from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, select, update, or_
from sqlalchemy.orm import selectinload

from app.ORMmodels.models import MatchModel


class MatchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_matches(self, matches_data: List[Dict[str, Any]]) -> int:
        if not matches_data:
            return 0

        stmt = insert(MatchModel).values(matches_data)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['fbref_id'],
            set_={
                "date": stmt.excluded.date,
                "home_score": stmt.excluded.home_score,
                "away_score": stmt.excluded.away_score,
                "home_xg": stmt.excluded.home_xg,
                "away_xg": stmt.excluded.away_xg,
                "is_finished": stmt.excluded.is_finished,
                "updated_at": func.now()
            }
        )

        await self.session.execute(upsert_stmt)
        return len(matches_data)

    async def get_unparsed_matches(self, limit: int = 5) -> List[MatchModel]:
        stmt = (
            select(MatchModel)
            .options(selectinload(MatchModel.home_team), selectinload(MatchModel.away_team))
            .where(MatchModel.is_finished == True)
            .where(MatchModel.details_parsed == False)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_as_parsed(self, match_id: int):
        stmt = (
            update(MatchModel)
            .where(MatchModel.id == match_id)
            .values(details_parsed=True, updated_at=func.now())
        )
        await self.session.execute(stmt)

    # --- НОВЫЙ МЕТОД ---
    async def get_finished_matches_by_team(self, team_id: int, limit: int, offset: int) -> List[MatchModel]:
        """
        Возвращает сыгранные матчи команды (дома или в гостях) с пагинацией.
        Сортировка от новых к старым.
        """
        stmt = (
            select(MatchModel)
            .options(selectinload(MatchModel.home_team),
                     selectinload(MatchModel.away_team))  # Подгружаем названия команд
            .where(
                or_(
                    MatchModel.home_team_id == team_id,
                    MatchModel.away_team_id == team_id
                )
            )
            .where(MatchModel.is_finished == True)
            .order_by(MatchModel.date.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()