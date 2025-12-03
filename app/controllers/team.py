import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append('.')
load_dotenv()

from app.services.league import LeagueService
from app.services.team import TeamService
from app.database.session import get_session


async def main():
    # 1. Инициализируем сервисы
    league_service = LeagueService(get_session())
    team_service = TeamService(get_session())

    print("📦 Шаг 1: Получение списка лиг из БД...")
    # Мы просим сервис лиг дать нам данные.
    # TeamService вообще не знает, откуда они взялись.
    leagues = await league_service.get_leagues()

    if not leagues:
        print("❌ Лиги не найдены в БД. Сначала запустите сбор лиг!")
        return

    print(f"📦 Получено {len(leagues)} лиг. Передаем в TeamService...")

    # 2. Запускаем обработку команд
    # Мы можем передать сюда ВСЕ лиги, или отфильтровать (например, только АПЛ)
    # my_leagues = [l for l in leagues if "Premier League" in l.title]

    await team_service.update_teams(leagues)


if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Остановлено")