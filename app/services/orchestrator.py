import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.league_service import LeagueService
from app.services.team_service import TeamService
from app.services.match_service import MatchService



class OrchestratorService:
    def __init__(self, session: AsyncSession):
        self.league_service = LeagueService(session)
        self.team_service = TeamService(session)
        self.match_service = MatchService(session)

    async def run_full_update(self, historical_mode: bool = False):

        await self.league_service.update_leagues()
        all_leagues = await self.league_service.get_leagues()

        if not all_leagues: return

        active_leagues = [l for l in all_leagues if l.fbref_id]
        # --------------------

        if historical_mode:
            for i, league in enumerate(active_leagues, 1):
                try:
                    history_url = f"https://fbref.com/en/comps/{league.fbref_id}/history/{league.slug.replace('-Stats', '-Seasons')}"
                    html = await self.league_service.fetcher.get_html(history_url)
                    seasons = self.league_service.parser.parse_league_history(html)

                    target_seasons = seasons[:5]

                    for s in target_seasons:
                        team_cfg = {league.id: s['url']}
                        match_cfg = {league.id: {'url': s['url'], 'season_name': s['season']}}

                        await self.team_service.update_teams([league], season_url_override=team_cfg)
                        await self.match_service.update_matches([league], season_config=match_cfg)
                except Exception as e:
                    continue

        else:
            await self.team_service.update_teams(active_leagues)
            await self.match_service.update_matches(active_leagues)

        for _ in range(10):
            await self.match_service.update_details_for_finished_matches()

        await self.league_service.fetcher.close()
        await self.team_service.fetcher.close()
        await self.match_service.fetcher.close()