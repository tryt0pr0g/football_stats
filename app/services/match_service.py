from typing import List, Dict
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
        await self.fetcher.close()

    async def update_matches(self, leagues: List[LeagueModel], season_config: Dict[int, dict] = None) -> int:
        team_map = await self.team_repo.get_fbref_id_map()
        total_matches = 0
        season_config = season_config or {}

        for i, league in enumerate(leagues, 1):
            if not league.fbref_id or not league.slug: continue

            if league.id in season_config:
                base_url = season_config[league.id]['url']
                current_season = season_config[league.id]['season_name']
                if "-Stats" in base_url:
                    url = base_url.replace("-Stats", "-Scores-and-Fixtures").replace(f"/{league.fbref_id}/",
                                                                                     f"/{league.fbref_id}/schedule/")
                else:
                    url = base_url
            else:
                current_season = "2024-2025"
                slug_schedule = league.slug.replace("-Stats", "-Scores-and-Fixtures")
                url = f"https://fbref.com/en/comps/{league.fbref_id}/schedule/{slug_schedule}"

            try:
                html = await self.fetcher.get_html(url)

                raw_matches = self.parser.parse_schedule(html, league.id, current_season)

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

            except Exception as e:
                await self.session.rollback()
                continue

        return total_matches

    async def update_details_for_finished_matches(self, limit: int = 5) -> int:
        matches_orm = await self.repo.get_unparsed_matches(limit=limit)

        if not matches_orm:
            return 0

        processed_count = 0

        matches_to_process = []
        for m in matches_orm:
            matches_to_process.append({
                "id": m.id,
                "fbref_id": m.fbref_id,
                "home_team_db_id": m.home_team_id,
                "away_team_db_id": m.away_team_id,
                "home_team_fbref_id": m.home_team.fbref_id,
                "away_team_fbref_id": m.away_team.fbref_id,
            })

        for i, match in enumerate(matches_to_process, 1):
            url = f"https://fbref.com/en/matches/{match['fbref_id']}"

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

                if stats_data:
                    fbref_to_db_map = await self.stat_repo.upsert_players(players_data)

                    ready_stats = []
                    for s in stats_data:
                        pid = fbref_to_db_map.get(s['player_fbref_id_temp'])
                        if pid:
                            tid = match['home_team_db_id'] if s['team_fbref_id_temp'] == match[
                                'home_team_fbref_id'] else match['away_team_db_id']
                            s['player_id'] = pid
                            s['team_id'] = tid

                            s.pop('player_fbref_id_temp', None)
                            s.pop('team_fbref_id_temp', None)
                            ready_stats.append(s)

                    if ready_stats:
                        await self.stat_repo.upsert_stats(ready_stats)

                        await self.repo.mark_as_parsed(match['id'])
                        await self.session.commit()

                        processed_count += 1

            except Exception as e:
                await self.session.rollback()
                continue

        return processed_count