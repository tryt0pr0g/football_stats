from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ORMmodels.models import LeagueModel
from app.repositories.team_repo import TeamRepository
from app.repositories.match_repo import MatchRepository
from app.scraper.fetcher import AsyncFetcher
from app.scraper.parser import StatsParser
from app.schemes.team_shemes import PaginationShm, RequestTeamScheme
from app.schemes.match_schemes import ResponseMatchScheme
from typing import Dict


class TeamService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TeamRepository(session)
        self.match_repo = MatchRepository(session)

        self._fetcher: Optional[AsyncFetcher] = None
        self._parser: Optional[StatsParser] = None

    @property
    def fetcher(self) -> AsyncFetcher:
        if self._fetcher is None:
            self._fetcher = AsyncFetcher()
        return self._fetcher

    @property
    def parser(self) -> StatsParser:
        if self._parser is None:
            self._parser = StatsParser()
        return self._parser

    async def update_teams(self, leagues: List[LeagueModel], season_url_override: Dict[int, str] = None):
        total_teams_saved = 0
        season_url_override = season_url_override or {}

        for i, league in enumerate(leagues, 1):
            if not league.fbref_id or not league.slug: continue

            if league.id in season_url_override:
                url = season_url_override[league.id]
            else:
                url = f"https://fbref.com/en/comps/{league.fbref_id}/{league.slug}"

            try:
                html = await self.fetcher.get_html(url)
                teams_data = self.parser.parse_teams(html)

                if teams_data:
                    count = await self.repo.upsert_teams(teams_data)
                    await self.session.commit()
                    total_teams_saved += count

            except Exception as e:
                await self.session.rollback()
                continue

        await self._fetcher.close()

    async def get_teams(self, pagination: PaginationShm):
        return await self.repo.get_all(pagination.limit, offset=pagination.offset)

    async def get_team_details(self, team: RequestTeamScheme):
        return await self.repo.get_team_with_players(team)

    async def get_team_matches(self, team_scheme: RequestTeamScheme, pagination: PaginationShm) -> List[
        ResponseMatchScheme]:
        team_model = await self.repo.get_team_with_players(team_scheme)

        if not team_model:
            return []

        matches = await self.match_repo.get_finished_matches_by_team(
            team_id=team_model.id,
            limit=pagination.limit,
            offset=pagination.offset
        )

        response = []
        for m in matches:
            response.append(ResponseMatchScheme(
                id=m.id,
                date=m.date,
                season=m.season,
                home_team_name=m.home_team.title,
                away_team_name=m.away_team.title,
                home_score=m.home_score,
                away_score=m.away_score,
                home_xg=m.home_xg,
                away_xg=m.away_xg,
                is_finished=m.is_finished
            ))

        return response