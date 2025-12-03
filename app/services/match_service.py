import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.ORMmodels.models import LeagueModel
from app.repositories.match_repo import MatchRepository
from app.repositories.team_repo import TeamRepository
from app.repositories.stat_repo import StatRepository
from app.scraper.fetcher import AsyncFetcher
from app.scraper.parser import StatsParser


class MatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MatchRepository(session)
        self.team_repo = TeamRepository(session)
        self.stat_repo = StatRepository(session)
        self.fetcher = AsyncFetcher()
        self.parser = StatsParser()

    async def close(self):
        """Явное закрытие ресурсов сервиса"""
        await self.fetcher.close()

    async def update_matches(self, leagues: List[LeagueModel], season_config: Dict[int, dict] = None):
        """
        season_config: {league_id: {'url': '...', 'season_name': '2022-2023'}}
        """
        print(f"🚀 [MatchService] Запуск обновления расписания...")

        team_map = await self.team_repo.get_fbref_id_map()
        total_matches = 0
        season_config = season_config or {}

        for i, league in enumerate(leagues, 1):
            if not league.fbref_id or not league.slug: continue

            # Определяем URL и сезон
            if league.id in season_config:
                # Если качаем историю, URL расписания нужно сформировать хитро
                # URL сезона: .../2022-2023/2022-2023-Premier-League-Stats
                # URL расписания: .../2022-2023/schedule/2022-2023-Premier-League-Scores-and-Fixtures
                base_url = season_config[league.id]['url']
                current_season = season_config[league.id]['season_name']

                # Превращаем ссылку на Stats в ссылку на Schedule
                if "-Stats" in base_url:
                    url = base_url.replace("-Stats", "-Scores-and-Fixtures").replace(f"/{league.fbref_id}/",
                                                                                     f"/{league.fbref_id}/schedule/")
                else:
                    # Фолбэк, если ссылка странная
                    url = base_url
            else:
                # Текущий сезон
                current_season = "2024-2025"
                slug_schedule = league.slug.replace("-Stats", "-Scores-and-Fixtures")
                url = f"https://fbref.com/en/comps/{league.fbref_id}/schedule/{slug_schedule}"

            print(f"\n[{i}/{len(leagues)}] 🌍 Расписание ({current_season}): {league.title}")
            print(f"   🔗 URL: {url}")

            try:
                html = await self.fetcher.get_html(url)

                raw_matches = self.parser.parse_schedule(html, league.id, current_season)
                print(f"   🔎 Найдено записей: {len(raw_matches)}")

                unique_matches = {m['fbref_id']: m for m in raw_matches}
                deduplicated_matches = list(unique_matches.values())

                ready_matches = []
                for m in deduplicated_matches:
                    h_id = team_map.get(m['home_fbref_id'])
                    a_id = team_map.get(m['away_fbref_id'])
                    if h_id and a_id:
                        del m['home_fbref_id']
                        del m['away_fbref_id']
                        m['home_team_id'] = h_id
                        m['away_team_id'] = a_id
                        ready_matches.append(m)

                if ready_matches:
                    count = await self.repo.upsert_matches(ready_matches)
                    await self.session.commit()
                    total_matches += count
                    print(f"   💾 Сохранено: {count}")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                await self.session.rollback()
                continue

        await self.fetcher.close()
        print(f"\n🏁 [MatchService] Итог: {total_matches} матчей.")

    async def update_details_for_finished_matches(self):
        """Этап 2: Детали и статистика"""
        matches_orm = await self.repo.get_unparsed_matches(limit=5)

        if not matches_orm:
            print("🎉 Нет новых матчей для обработки.")
            return

        # ПРЕОБРАЗУЕМ ORM ОБЪЕКТЫ В СЛОВАРИ (DTO)
        # Это спасет нас от ошибки MissingGreenlet при rollback,
        # так как словари не "протухают" и не требуют сессии.
        matches_to_process = []
        for m in matches_orm:
            matches_to_process.append({
                "id": m.id,
                "fbref_id": m.fbref_id,
                "home_team_title": m.home_team.title,
                "away_team_title": m.away_team.title,
                "home_team_fbref_id": m.home_team.fbref_id,
                "away_team_fbref_id": m.away_team.fbref_id,
                "home_team_db_id": m.home_team_id,
                "away_team_db_id": m.away_team_id,
            })

        print(f"🚀 [MatchDetails] Начинаем обработку {len(matches_to_process)} матчей...")

        for i, match in enumerate(matches_to_process, 1):
            url = f"https://fbref.com/en/matches/{match['fbref_id']}"
            print(f"\n[{i}/{len(matches_to_process)}] ⚽ Матч: {match['home_team_title']} vs {match['away_team_title']}")
            print(f"   🔗 {url}")

            try:
                html = await self.fetcher.get_html(url)

                result = self.parser.parse_match_details(
                    html,
                    match['id'],
                    match['home_team_fbref_id'],
                    match['away_team_fbref_id']
                )

                players_data = result['players']
                stats_data = result['stats']

                print(f"   🔎 Игроков: {len(players_data)}, Статистики: {len(stats_data)}")

                if stats_data:
                    # 1. Игроки
                    fbref_to_db_map = await self.stat_repo.upsert_players(players_data)

                    # 2. Статистика
                    ready_stats = []
                    for s in stats_data:
                        pid = fbref_to_db_map.get(s['player_fbref_id_temp'])
                        if pid:
                            tid = match['home_team_db_id'] if s['team_fbref_id_temp'] == match[
                                'home_team_fbref_id'] else match['away_team_db_id']

                            s['player_id'] = pid
                            s['team_id'] = tid
                            del s['player_fbref_id_temp']
                            del s['team_fbref_id_temp']
                            ready_stats.append(s)

                    count = await self.stat_repo.upsert_stats(ready_stats)
                    print(f"   💾 Сохранено записей: {count}")

                    await self.repo.mark_as_parsed(match['id'])

                    await self.session.commit()  # Фиксируем успех для одного матча
                    print("   ✅ Матч успешно закрыт.")
                else:
                    print("   ⚠️ Статистика пустая")

            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
                await self.session.rollback()  # Откатываем этот матч
                continue

        # УБРАЛИ self.fetcher.close() ОТСЮДА