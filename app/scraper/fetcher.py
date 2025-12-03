import asyncio
import random
from curl_cffi.requests import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed


class AsyncFetcher:
    def __init__(self):
        self.session = AsyncSession(
            impersonate="chrome124",
            timeout=30.0
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def get_html(self, url: str) -> str:
        sleep_time = random.uniform(5.0, 8.0)
        await asyncio.sleep(sleep_time)

        try:
            response = await self.session.get(url)

            if response.status_code == 429:
                await asyncio.sleep(120)
                raise Exception("Rate Limit")

            if response.status_code == 403:
                raise Exception("Access Denied")

            return response.text

        except Exception as e:
            raise e

    async def close(self):
        try:
            await self.session.close()
        except Exception:
            pass