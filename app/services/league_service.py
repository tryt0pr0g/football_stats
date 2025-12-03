from sqlalchemy.ext.asyncio import AsyncSession
from app.scraper.fetcher import AsyncFetcher
from app.scraper.parser import StatsParser
# Проверь, чтобы имя файла совпадало (league_repo.py или league.py)
from app.repositories.league_repo import LeagueRepository

class LeagueService:
    def __init__(self, session: AsyncSession):
        # Инициализируем репозиторий с переданной сессией
        self.repo = LeagueRepository(session)
        self.fetcher = AsyncFetcher()
        self.parser = StatsParser()

    async def update_leagues(self):
        url = "https://fbref.com/en/comps/"
        print(f"📦 [LeagueService] Скачиваем лиги...")

        try:
            html = await self.fetcher.get_html(url)
            leagues_data = self.parser.parse_leagues(html)

            if not leagues_data:
                print("⚠️ Лиги не найдены.")
                return

            count = await self.repo.upsert_leagues(leagues_data)

            # COMMIT
            await self.repo.session.commit()
            print(f"✅ [LeagueService] Сохранено {count} лиг.")

        except Exception as e:
            await self.repo.session.rollback()
            raise e

    async def get_leagues(self):
        return await self.repo.get_all()