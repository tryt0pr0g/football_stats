import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.league_service import LeagueService
from app.services.match_service import MatchService


class OrchestratorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.league_service = LeagueService(session)
        self.match_service = MatchService(session)

    async def run_full_update(self, historical_mode: bool = False):
        try:
            await self.league_service.update_leagues()
        except Exception as e:
            pass

        leagues = await self.league_service.repo.get_all()

        for i, league in enumerate(leagues, 1):
            batch_counter = 0
            while True:
                processed = await self.match_service.update_details_for_finished_matches(limit=5)

                if processed == 0:
                    break

                batch_counter += processed

                await asyncio.sleep(2)

            await asyncio.sleep(5)

        await self.match_service.close()
        await self.league_service.close()