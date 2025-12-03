from fastapi import APIRouter, HTTPException, Depends
from typing import List

from app.schemes.team_shemes import PaginationShm, ResponseTeamScheme, RequestTeamScheme, ResponseTeamInfoScheme
from app.schemes.match_schemes import ResponseMatchScheme  # <--- Импорт
from app.database.session import Session
from app.services.team_service import TeamService

teams_router = APIRouter()


@teams_router.get(
    '/get_teams',
    response_model=List[ResponseTeamScheme]
)
async def get_teams(pagination: PaginationShm = Depends(), session: Session = None) -> List[ResponseTeamScheme]:
    # Примечание: PaginationShm лучше использовать с Depends(), чтобы параметры были в query string (?limit=10&offset=0)
    # Но если вы передаете JSON body в GET запросе (что не стандартно, но работает), оставьте как было.
    # Я исправлю на Depends для query параметров, так правильнее для GET.

    service = TeamService(session)
    teams = await service.get_teams(pagination)
    return teams


@teams_router.get(
    "/{team_title}",
    response_model=ResponseTeamInfoScheme
)
async def read_team_details(
        team_title: str,
        session: Session
) -> ResponseTeamInfoScheme:
    # Создаем схему из path-параметра
    team_req = RequestTeamScheme(title=team_title)

    service = TeamService(session)
    team = await service.get_team_details(team_req)

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return team


# --- НОВЫЙ ЭНДПОИНТ ---
@teams_router.get(
    "/{team_title}/matches",
    response_model=List[ResponseMatchScheme]
)
async def read_team_matches(
        team_title: str,
        pagination: PaginationShm = Depends(),  # Query params: ?limit=10&offset=0
        session: Session = None
) -> List[ResponseMatchScheme]:
    team_req = RequestTeamScheme(title=team_title)
    service = TeamService(session)

    matches = await service.get_team_matches(team_req, pagination)

    if not matches and pagination.offset == 0:
        # Если на первой странице пусто - возможно команды нет
        # Проверим существование команды
        team = await service.get_team_details(team_req)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    return matches