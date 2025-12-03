import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Импортируем ваш main_router, как в вашем коде
from app.api.main_router import main_router
from app.database.db import AsyncSessionLocal
from app.repositories.league_repo import LeagueRepository
from app.services.orchestrator import OrchestratorService

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Планировщик оставляем глобальным
scheduler = AsyncIOScheduler()

# Мы УБРАЛИ глобальную переменную orchestrator = OrchestratorService(),
# так как она требует сессию, которую нельзя держать открытой вечно.

# --- ФУНКЦИЯ-ОБЕРТКА ДЛЯ ЗАДАЧ ---
# Эта функция создает новую сессию и новый экземпляр сервиса для каждого запуска
async def run_scheduled_parsing():
    logger.info("⏰ Запуск запланированной задачи парсинга...")
    async with AsyncSessionLocal() as session:
        orchestrator = OrchestratorService(session)
        await orchestrator.run_full_update()

async def run_startup_check():
    """
    Проверяет, пустая ли база. Если пустая - запускает начальную загрузку.
    """
    async with AsyncSessionLocal() as session:
        repo = LeagueRepository(session)
        leagues = await repo.get_all()

        if not leagues:
            logger.info("🚀 БД пуста. Запускаем ПЕРВИЧНУЮ загрузку данных...")
            # Запускаем парсинг в фоне через нашу обертку
            asyncio.create_task(run_scheduled_parsing())
        else:
            logger.info(f"✅ В БД уже есть данные ({len(leagues)} лиг). Первичная загрузка пропущена.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- ПРИ ЗАПУСКЕ ---
    logger.info("🟢 Приложение запускается...")

    # 1. Проверка на "Первый запуск"
    await run_startup_check()

    # 2. Добавляем задачу в расписание
    # Используем функцию-обертку run_scheduled_parsing, а не метод экземпляра
    scheduler.add_job(
        run_scheduled_parsing,
        trigger=CronTrigger(hour=3, minute=0),  # Время сервера (обычно UTC)
        id="daily_update",
        replace_existing=True
    )

    # 3. Старт планировщика
    scheduler.start()
    logger.info("⏰ Планировщик запущен. Следующее обновление в 03:00.")

    yield  # Здесь приложение работает и принимает запросы

    # --- ПРИ ОСТАНОВКЕ ---
    logger.info("🔴 Приложение останавливается...")
    scheduler.shutdown()


# Создаем приложение с lifespan
app = FastAPI(title="Football Stats API", lifespan=lifespan)

# Подключаем ваш роутер
app.include_router(main_router, prefix="/api")
