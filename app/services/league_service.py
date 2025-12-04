from sqlalchemy.ext.asyncio import AsyncSession
from app.scraper.fetcher import AsyncFetcher
from app.scraper.parser import StatsParser
from app.repositories.league_repo import LeagueRepository
from typing import List
from app.ORMmodels.models import LeagueModel


class LeagueService:
    def __init__(self, session: AsyncSession):
        self.repo = LeagueRepository(session)
        self.fetcher = AsyncFetcher()
        self.parser = StatsParser()
        self.session = session

    async def update_leagues(self):
        url = "https://fbref.com/en/comps/"
        print(f"[LeagueService] Скачиваем лиги...")

        try:
            html = await self.fetcher.get_html(url)
            leagues_data = self.parser.parse_leagues(html)

            if not leagues_data:
                print("Лиги не найдены.")
                return 0

            count = await self.repo.upsert_leagues(leagues_data)

            await self.session.commit()

            print(f"[LeagueService] Сохранено {count} лиг.")
            return count

        except Exception as e:
            await self.session.rollback()
            print(f"LeagueService Error: {e}")
            raise e

    async def get_leagues(self) -> List[LeagueModel]:
        return await self.repo.get_all()