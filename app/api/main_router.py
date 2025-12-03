from fastapi import APIRouter
from app.api.teams_router import teams_router


main_router = APIRouter()
main_router.include_router(leagues_router)
main_router.include_router(teams_router)