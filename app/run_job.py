import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append('.')
load_dotenv()

from app.database.db import AsyncSessionLocal
from app.services.orchestrator import OrchestratorService


async def run_historical_update():

    try:
        async with AsyncSessionLocal() as session:
            orchestrator = OrchestratorService(session)
            await orchestrator.run_full_update(historical_mode=True)
    except Exception as e:
        sys.exit(1)


def main():
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(run_historical_update())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()