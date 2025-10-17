import httpx
import random
import asyncio
from typing import Optional
from apps.common import settings, get_logger

logger = get_logger(__name__)


class HTTPClient:
    """HTTP client for crawling with retry and backoff logic."""

    def __init__(self):
        self.timeout = settings.request_timeout_ms / 1000  # Convert to seconds
        self.max_retry = settings.max_retry
        self.backoff_base_ms = settings.backoff_base_ms
        self.user_agents = settings.user_agent_pool

    def _get_random_user_agent(self) -> str:
        """Get random user agent from pool."""
        return random.choice(self.user_agents)

    async def fetch(self, url: str) -> Optional[str]:
        """
        Fetch URL with retry logic.
        Returns HTML content or None if failed.
        """
        headers = {
            "User-Agent": self._get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for attempt in range(self.max_retry):
                try:
                    # Random delay to mimic human behavior
                    await asyncio.sleep(random.uniform(0.3, 0.9))

                    response = await client.get(url, headers=headers)

                    if response.status_code == 200:
                        logger.info(f"Successfully fetched URL (attempt {attempt + 1}): {url}")
                        return response.text

                    elif response.status_code in [403, 429]:
                        # Rate limited or forbidden - exponential backoff
                        backoff_ms = self.backoff_base_ms * (2 ** attempt)
                        logger.warning(
                            f"HTTP {response.status_code} on attempt {attempt + 1}, "
                            f"backing off {backoff_ms}ms: {url}"
                        )
                        await asyncio.sleep(backoff_ms / 1000)
                        continue

                    elif response.status_code >= 500:
                        # Server error - retry
                        logger.warning(f"Server error {response.status_code} on attempt {attempt + 1}: {url}")
                        await asyncio.sleep(self.backoff_base_ms / 1000)
                        continue

                    else:
                        logger.error(f"HTTP {response.status_code} for URL: {url}")
                        return None

                except httpx.TimeoutException:
                    logger.warning(f"Timeout on attempt {attempt + 1}: {url}")
                    if attempt < self.max_retry - 1:
                        await asyncio.sleep(self.backoff_base_ms / 1000)
                        continue
                    return None

                except Exception as e:
                    logger.error(f"Error fetching URL on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retry - 1:
                        await asyncio.sleep(self.backoff_base_ms / 1000)
                        continue
                    return None

        logger.error(f"Failed to fetch URL after {self.max_retry} attempts: {url}")
        return None
