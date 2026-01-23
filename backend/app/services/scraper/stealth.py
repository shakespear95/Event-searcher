"""
Stealth Browser Configuration.
Implements anti-detection measures for web scraping.
"""
import asyncio
import random
from typing import Any

from fake_useragent import UserAgent
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("scraper.stealth")


class StealthBrowser:
    """
    Stealth browser using Playwright with anti-detection measures.

    Implements rules S7-S9:
    - S7: Uses residential proxies in production
    - S8: Rotates user agents per request
    - S9: Randomizes delays (human-like behavior)
    """

    def __init__(self):
        self.ua = UserAgent()
        self.browser: Browser | None = None
        self.playwright = None

        # Viewport sizes to rotate
        self.viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864},
            {"width": 1440, "height": 900},
            {"width": 1280, "height": 720},
        ]

        # Languages to rotate
        self.languages = ["en-US", "en-GB", "en", "de-DE", "de"]

    async def _get_random_user_agent(self) -> str:
        """Get a random real user agent."""
        try:
            return self.ua.random
        except Exception:
            # Fallback user agents
            fallbacks = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            ]
            return random.choice(fallbacks)

    async def _get_stealth_scripts(self) -> str:
        """JavaScript to inject for stealth mode."""
        return """
        // Remove webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });

        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [
                { name: 'Chrome PDF Plugin' },
                { name: 'Chrome PDF Viewer' },
                { name: 'Native Client' }
            ]
        });

        // Mock languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });

        // Mock permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Mock chrome runtime
        window.chrome = {
            runtime: {},
        };

        // Randomize canvas fingerprint slightly
        const originalGetContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            const context = originalGetContext.apply(this, arguments);
            if (type === '2d') {
                const originalFillText = context.fillText;
                context.fillText = function() {
                    arguments[1] += Math.random() * 0.01;
                    return originalFillText.apply(this, arguments);
                };
            }
            return context;
        };
        """

    async def start(self) -> None:
        """Start the browser."""
        if self.browser:
            return

        self.playwright = await async_playwright().start()

        launch_options: dict[str, Any] = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-position=0,0",
                "--ignore-certificate-errors",
                "--ignore-certificate-errors-spki-list",
            ],
        }

        # Add proxy if configured (Rule S7)
        if settings.proxy_url and settings.is_production:
            launch_options["proxy"] = {
                "server": settings.proxy_url,
            }
            logger.info("Using proxy for scraping")

        self.browser = await self.playwright.chromium.launch(**launch_options)
        logger.info("Stealth browser started")

    async def create_context(self) -> BrowserContext:
        """Create a new browser context with stealth settings."""
        if not self.browser:
            await self.start()

        user_agent = await self._get_random_user_agent()
        viewport = random.choice(self.viewports)
        locale = random.choice(self.languages)

        context = await self.browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            locale=locale,
            timezone_id="Europe/Zurich",
            geolocation={"latitude": 47.1410, "longitude": 9.5209},  # Liechtenstein
            permissions=["geolocation"],
            java_script_enabled=True,
            has_touch=False,
            is_mobile=False,
            color_scheme="light",
        )

        # Inject stealth scripts on every new page
        await context.add_init_script(await self._get_stealth_scripts())

        logger.debug(
            "Created stealth context",
            user_agent=user_agent[:50],
            viewport=viewport,
        )

        return context

    async def create_page(self, context: BrowserContext | None = None) -> Page:
        """Create a new page with stealth settings."""
        if context is None:
            context = await self.create_context()

        page = await context.new_page()

        # Block unnecessary resources for speed
        await page.route(
            "**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf}",
            lambda route: route.abort(),
        )

        # Block tracking scripts
        await page.route(
            "**/*google-analytics*/**",
            lambda route: route.abort(),
        )
        await page.route(
            "**/*facebook*/**",
            lambda route: route.abort(),
        )

        return page

    async def random_delay(self, min_seconds: float = 2, max_seconds: float = 5) -> None:
        """Random delay to mimic human behavior (Rule S9)."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def human_scroll(self, page: Page) -> None:
        """Simulate human-like scrolling."""
        # Scroll down gradually
        for _ in range(random.randint(2, 5)):
            await page.evaluate(
                f"window.scrollBy(0, {random.randint(100, 300)})"
            )
            await asyncio.sleep(random.uniform(0.3, 0.8))

    async def close(self) -> None:
        """Close the browser."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        logger.info("Stealth browser closed")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
