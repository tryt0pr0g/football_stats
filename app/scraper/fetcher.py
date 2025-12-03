import asyncio
import random
from curl_cffi.requests import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed


class AsyncFetcher:
    def __init__(self):
        # Используем impersonate без ручных заголовков, чтобы избежать конфликтов
        self.session = AsyncSession(
            impersonate="chrome124",
            timeout=30.0
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def get_html(self, url: str) -> str:
        sleep_time = random.uniform(5.0, 8.0)
        print(f"😴 Спим {sleep_time:.2f} сек перед запросом...")
        await asyncio.sleep(sleep_time)

        try:
            response = await self.session.get(url)

            if response.status_code != 200:
                print(f"⚠️ ОШИБКА HTTP: {response.status_code} | URL: {url}")

            if response.status_code == 429:
                print("⛔ 429 Too Many Requests. Ждем 2 минуты...")
                await asyncio.sleep(120)
                raise Exception("Rate Limit")

            if response.status_code == 403:
                print("⛔ 403 Forbidden.")
                raise Exception("Access Denied")

            return response.text

        except Exception as e:
            # print(f"❌ Ошибка: {e}") # Можно раскомментировать для отладки
            raise e

    async def close(self):
        try:
            # Безопасное закрытие сессии
            await self.session.close()
        except Exception:
            # Игнорируем ошибки при закрытии (например, если она уже закрыта)
            pass