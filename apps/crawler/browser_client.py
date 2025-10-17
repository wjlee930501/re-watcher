import asyncio
import random
from typing import Optional
from playwright.async_api import async_playwright, Browser, Page
from apps.common import settings, get_logger

logger = get_logger(__name__)


class BrowserClient:
    """Playwright browser client for JavaScript-heavy pages."""

    def __init__(self):
        self.headless = settings.playwright_headless
        self.user_agents = settings.user_agent_pool
        self.timeout = settings.request_timeout_ms
        self._browser: Optional[Browser] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start browser instance."""
        if not self._browser:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            logger.info("Browser started")

    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")

    async def fetch(self, url: str, wait_for_selector: Optional[str] = None) -> Optional[str]:
        """
        Fetch URL using Playwright browser.
        Returns HTML content or None if failed.
        """
        if not self._browser:
            await self.start()

        page: Optional[Page] = None
        try:
            # Create new page with random user agent
            page = await self._browser.new_page(
                user_agent=random.choice(self.user_agents)
            )

            # Set viewport (smaller for less resource usage)
            await page.set_viewport_size({"width": 1280, "height": 720})

            # Block unnecessary resources to save bandwidth and speed up loading
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,font,woff,woff2}", lambda route: route.abort())

            # Random delay before navigation
            await asyncio.sleep(random.uniform(0.3, 0.8))

            # Navigate to URL (use 'domcontentloaded' instead of 'networkidle' for faster loading)
            logger.info(f"Browser navigating to: {url}")
            response = await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

            if not response:
                logger.error(f"No response from page.goto: {url}")
                return None

            if response.status >= 400:
                logger.error(f"Browser got HTTP {response.status}: {url}")
                return None

            # Wait for specific selector if provided
            if wait_for_selector:
                try:
                    await page.wait_for_selector(wait_for_selector, timeout=5000)
                except Exception as e:
                    logger.warning(f"Selector wait timeout: {wait_for_selector}, continuing anyway")

            # Shorter wait for dynamic content (reduced from 1-2s to 0.5-1s)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            # Check for CAPTCHA
            content = await page.content()
            if self._detect_captcha(content):
                logger.warning(f"CAPTCHA detected on page: {url}")
                # Save screenshot for debugging
                try:
                    screenshot_path = f"{settings.snapshot_dir}/captcha_{random.randint(1000, 9999)}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.info(f"CAPTCHA screenshot saved: {screenshot_path}")
                except Exception as e:
                    logger.error(f"Failed to save screenshot: {e}")
                return None

            logger.info(f"Successfully fetched page with browser: {url}")
            return content

        except asyncio.TimeoutError:
            logger.error(f"Browser timeout for URL: {url}")
            return None

        except Exception as e:
            logger.error(f"Browser error for URL: {url}, error: {e}")
            return None

        finally:
            if page:
                await page.close()

    def _detect_captcha(self, html: str) -> bool:
        """Detect CAPTCHA in page content."""
        captcha_indicators = [
            "captcha",
            "recaptcha",
            "i'm not a robot",
            "verification",
            "자동 입력 방지",
            "보안문자"
        ]

        html_lower = html.lower()
        for indicator in captcha_indicators:
            if indicator in html_lower:
                return True

        return False
