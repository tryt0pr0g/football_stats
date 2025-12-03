from sqlalchemy.ext.asyncio import AsyncSession
from app.scraper.fetcher import AsyncFetcher
from app.scraper.parser import StatsParser
from app.repositories.league_repo import LeagueRepository

class LeagueService:
    def __init__(self, session: AsyncSession):
        self.repo = LeagueRepository(session)
        self.fetcher = AsyncFetcher()
        self.parser = StatsParser()

    async def update_leagues(self):
        url = "https://fbref.com/en/comps/"

        try:
            html = await self.fetcher.get_html(url)
            leagues_data = self.parser.parse_leagues(html)

            if not leagues_data:
                return

            await self.repo.session.commit()

        except Exception as e:
            await self.repo.session.rollback()
            raise e

    async def get_leagues(self):
        return await self.repo.get_all()