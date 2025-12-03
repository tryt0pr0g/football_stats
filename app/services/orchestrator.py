import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.league_service import LeagueService
from app.services.team_service import TeamService
from app.services.match_service import MatchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestratorService:
    def __init__(self, session: AsyncSession):
        self.league_service = LeagueService(session)
        self.team_service = TeamService(session)
        self.match_service = MatchService(session)

    async def run_full_update(self, historical_mode: bool = False):
        """
        historical_mode=True: Скачивает историю (прошлые + будущие сезоны).
        historical_mode=False: Скачивает только текущий сезон (по умолчанию).
        """
        logger.info(f"🔄 [ORCHESTRATOR] Запуск (История={historical_mode})...")

        # 1. Лиги
        await self.league_service.update_leagues()
        all_leagues = await self.league_service.get_leagues()

        if not all_leagues: return

        # ВМЕСТО ЭТОГО БЕРЕМ ВСЕ ЛИГИ С ID
        active_leagues = [l for l in all_leagues if l.fbref_id]
        logger.info(f"📦 К обработке готово {len(active_leagues)} лиг.")
        # --------------------

        if historical_mode:
            # --- ИСТОРИЧЕСКИЙ РЕЖИМ ---
            for i, league in enumerate(active_leagues, 1):
                logger.info(f"📜 [{i}/{len(active_leagues)}] История для {league.title}...")
                try:
                    history_url = f"https://fbref.com/en/comps/{league.fbref_id}/history/{league.slug.replace('-Stats', '-Seasons')}"
                    html = await self.league_service.fetcher.get_html(history_url)
                    seasons = self.league_service.parser.parse_league_history(html)

                    # Берем 5 последних сезонов (включая будущие)
                    target_seasons = seasons[:5]

                    for s in target_seasons:
                        logger.info(f"   📅 Сезон {s['season']}...")
                        team_cfg = {league.id: s['url']}
                        match_cfg = {league.id: {'url': s['url'], 'season_name': s['season']}}

                        await self.team_service.update_teams([league], season_url_override=team_cfg)
                        await self.match_service.update_matches([league], season_config=match_cfg)
                except Exception as e:
                    logger.error(f"❌ Ошибка истории лиги {league.title}: {e}")
                    continue

        else:
            # --- ОБЫЧНЫЙ РЕЖИМ ---
            await self.team_service.update_teams(active_leagues)
            await self.match_service.update_matches(active_leagues)

        # 4. Детали матчей
        logger.info("📦 [4/4] Сбор статистики...")
        # Можно запустить в цикле, пока есть необработанные матчи
        # (например, 50 итераций по 5 матчей = 250 матчей за запуск)
        for _ in range(10):
            await self.match_service.update_details_for_finished_matches()

        # Закрытие
        await self.league_service.fetcher.close()
        await self.team_service.fetcher.close()
        await self.match_service.fetcher.close()

        logger.info("✅ [ORCHESTRATOR] Завершено.")