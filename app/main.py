import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    logger.info("Запуск запланированной задачи парсинга...")
    try:
        async with AsyncSessionLocal() as session:
            orchestrator = OrchestratorService(session)
            await orchestrator.run_full_update()
    except Exception as e:
        logger.error(f"Ошибка в процессе парсинга: {e}")


async def run_startup_check():
    if os.getenv("SCRAPING_ENABLED", "True").lower() == "false":
        logger.info("Парсинг отключен в конфигурации (SCRAPING_ENABLED=False). Пропускаем проверку.")
        return

    logger.info("Проверка состояния базы данных...")
    try:
        async with AsyncSessionLocal() as session:
            repo = LeagueRepository(session)
            leagues = await repo.get_all()

        if not leagues:
            logger.info("БД пуста. Запускаем ПЕРВИЧНУЮ загрузку данных...")
            asyncio.create_task(run_scheduled_parsing())
        else:
            logger.info(f"В БД уже есть данные ({len(leagues)} лиг).")
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🟢 Приложение запускается...")

    await run_startup_check()

    if os.getenv("SCRAPING_ENABLED", "True").lower() != "false":
        scheduler.add_job(
            run_scheduled_parsing,
            trigger=CronTrigger(hour=3, minute=0),
            id="daily_update",
            replace_existing=True
        )
        scheduler.start()
        logger.info("Планировщик запущен.")
    else:
        logger.info("Планировщик НЕ запущен (Режим только API).")

    yield

    logger.info("Приложение останавливается...")
    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="Football Stats API", lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(main_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Football Data Service is Running", "status": "active"}