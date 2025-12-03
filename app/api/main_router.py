from fastapi import APIRouter
from app.api.leagues_router import leagues_router
from app.api.players_router import players_router
from app.api.matches_router import matches_router
from app.api.teams_router import teams_router


main_router = APIRouter()
main_router.include_router(leagues_router)
main_router.include_router(players_router)
main_router.include_router(matches_router)
main_router.include_router(teams_router)