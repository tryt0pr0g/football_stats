import asyncio
import sys
import os
from dotenv import load_dotenv

# Путь к приложению для импортов
sys.path.append('.')
# Загрузка переменных окружения из .env (для локального запуска)
load_dotenv()

from app.database.db import AsyncSessionLocal
from app.services.orchestrator import OrchestratorService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_historical_update():
    """Запускает полную историческую загрузку данных по всем лигам."""
    logger.info("🚀 [JOB] Запуск полной исторической загрузки (ВСЕ ЛИГИ)...")

    try:
        async with AsyncSessionLocal() as session:
            orchestrator = OrchestratorService(session)
            # Включаем historical_mode=True для полной загрузки
            await orchestrator.run_full_update(historical_mode=True)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка выполнения Job: {e}")
        # Вызываем sys.exit(1), чтобы Cloud Run Job пометил задачу как невыполненную
        sys.exit(1)

    logger.info("✅ [JOB] Историческая загрузка завершена.")


def main():
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(run_historical_update())
    except KeyboardInterrupt:
        logger.warning("🛑 Остановлено пользователем")
        sys.exit(0)


if __name__ == "__main__":
    main()