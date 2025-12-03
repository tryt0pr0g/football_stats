import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.api.main_router import main_router
from app.database.db import AsyncSessionLocal
from app.repositories.league_repo import LeagueRepository
from app.services.orchestrator import OrchestratorService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def run_scheduled_parsing():
    async with AsyncSessionLocal() as session:
        orchestrator = OrchestratorService(session)
        await orchestrator.run_full_update()

async def run_startup_check():
    async with AsyncSessionLocal() as session:
        repo = LeagueRepository(session)
        leagues = await repo.get_all()

        if not leagues:
            asyncio.create_task(run_scheduled_parsing())


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_startup_check()
    scheduler.add_job(
        run_scheduled_parsing,
        trigger=CronTrigger(hour=3, minute=0),  # Время сервера (обычно UTC)
        id="daily_update",
        replace_existing=True
    )

    scheduler.start()

    yield

    logger.info("🔴 Приложение останавливается...")
    scheduler.shutdown()


app = FastAPI(title="Football Stats API", lifespan=lifespan)

app.include_router(main_router, prefix="/api")
