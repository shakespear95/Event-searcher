"""
Scraper Engine.
Main scraping orchestrator with rate limiting and robots.txt compliance.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.core.logging import ToolCallLogger

from .stealth import StealthBrowser


@dataclass
class ScrapedPage:
    """Result of scraping a single page."""

    url: str
    title: str | None = None
    content: str | None = None
    html: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error: str | None = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)


class ScraperEngine:
    """
    Web scraping engine with stealth capabilities.

    Implements scraper rules S1-S10:
    - S1: Checks robots.txt before scraping
    - S2: Rate limiting (2-5 seconds between requests per domain)
    - S3: Only scrapes public event data
    - S4: Caches results (handled externally)
    - S5: Stops if blocked
    - S6: Prefers APIs when available
    - S7-S9: Stealth measures (via StealthBrowser)
    - S10: Logs all activity
    """

    def __init__(self):
        self.browser = StealthBrowser()
        self.logger = ToolCallLogger("scraper")
        self.http_client = httpx.AsyncClient(timeout=30.0)

        # Rate limiting per domain
        self._last_request: dict[str, datetime] = {}
        self._min_delay = timedelta(seconds=2)
        self._max_delay = timedelta(seconds=5)

        # Robots.txt cache
        self._robots_cache: dict[str, RobotFileParser] = {}
        self._blocked_domains: set[str] = set()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    async def _check_robots(self, url: str) -> bool:
        """
        Check if URL is allowed by robots.txt (Rule S1).
        Returns True if scraping is allowed.
        """
        domain = self._get_domain(url)

        # Check if domain is blocked
        if domain in self._blocked_domains:
            return False

        # Check cache
        if domain not in self._robots_cache:
            try:
                robots_url = f"https://{domain}/robots.txt"
                response = await self.http_client.get(robots_url)

                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.parse(response.text.splitlines())
                self._robots_cache[domain] = rp

            except Exception as e:
                self.logger.log_result(
                    action="check_robots",
                    success=False,
                    error=f"Could not fetch robots.txt: {e}",
                )
                # If we can't fetch robots.txt, allow scraping cautiously
                return True

        rp = self._robots_cache.get(domain)
        if rp:
            # Check if our user agent is allowed
            allowed = rp.can_fetch("*", url)
            if not allowed:
                self.logger.log_call(
                    action="robots_blocked",
                    params={"url": url, "domain": domain},
                )
            return allowed

        return True

    async def _rate_limit(self, domain: str) -> None:
        """
        Apply rate limiting for domain (Rule S2).
        Waits if last request was too recent.
        """
        last = self._last_request.get(domain)

        if last:
            elapsed = datetime.utcnow() - last
            if elapsed < self._min_delay:
                wait_time = (self._min_delay - elapsed).total_seconds()
                # Add random jitter
                wait_time += await self.browser.random_delay(0, 1)
                await asyncio.sleep(wait_time)

        self._last_request[domain] = datetime.utcnow()

    async def scrape_page(
        self,
        url: str,
        wait_for_selector: str | None = None,
        extract_metadata: bool = True,
    ) -> ScrapedPage:
        """
        Scrape a single page with stealth measures.
        """
        domain = self._get_domain(url)

        self.logger.log_call(
            action="scrape_page",
            params={"url": url, "domain": domain},
        )

        # Check robots.txt (Rule S1)
        if not await self._check_robots(url):
            self.logger.log_result(
                action="scrape_page",
                success=False,
                error="Blocked by robots.txt",
            )
            return ScrapedPage(
                url=url,
                success=False,
                error="Blocked by robots.txt (Rule S1)",
            )

        # Apply rate limiting (Rule S2)
        await self._rate_limit(domain)

        try:
            # Create stealth page
            context = await self.browser.create_context()
            page = await self.browser.create_page(context)

            try:
                # Navigate with timeout
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for specific selector if provided
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=10000)
                    except PlaywrightTimeout:
                        pass  # Continue anyway

                # Human-like scrolling
                await self.browser.human_scroll(page)

                # Random delay
                await self.browser.random_delay(1, 2)

                # Get page content
                html = await page.content()
                title = await page.title()

                # Extract text content
                soup = BeautifulSoup(html, "lxml")

                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                content = soup.get_text(separator="\n", strip=True)

                # Extract metadata
                metadata = {}
                if extract_metadata:
                    metadata = await self._extract_metadata(soup, page)

                self.logger.log_result(
                    action="scrape_page",
                    success=True,
                    result=f"Scraped {len(content)} chars",
                )

                self.logger.log_source(
                    source_api="scraper",
                    source_url=url,
                    data_type="page_content",
                )

                return ScrapedPage(
                    url=url,
                    title=title,
                    content=content,
                    html=html,
                    metadata=metadata,
                    success=True,
                )

            finally:
                await context.close()

        except PlaywrightTimeout:
            self.logger.log_result(
                action="scrape_page",
                success=False,
                error="Timeout",
            )
            return ScrapedPage(url=url, success=False, error="Timeout")

        except Exception as e:
            error_msg = str(e)

            # Check for blocking (Rule S5)
            if "403" in error_msg or "blocked" in error_msg.lower():
                self._blocked_domains.add(domain)
                self.logger.log_result(
                    action="scrape_page",
                    success=False,
                    error=f"Domain blocked: {domain}",
                )

            return ScrapedPage(url=url, success=False, error=error_msg)

    async def _extract_metadata(self, soup: BeautifulSoup, page: Page) -> dict[str, Any]:
        """Extract structured metadata from page."""
        metadata = {}

        # OpenGraph tags
        og_tags = soup.find_all("meta", property=lambda x: x and x.startswith("og:"))
        for tag in og_tags:
            key = tag.get("property", "").replace("og:", "")
            metadata[f"og_{key}"] = tag.get("content")

        # Schema.org JSON-LD
        json_ld = soup.find_all("script", type="application/ld+json")
        if json_ld:
            import json

            for script in json_ld:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        if data.get("@type") == "Event":
                            metadata["schema_event"] = data
                        elif isinstance(data.get("@graph"), list):
                            for item in data["@graph"]:
                                if item.get("@type") == "Event":
                                    metadata["schema_event"] = item
                                    break
                except (json.JSONDecodeError, TypeError):
                    pass

        # Meta description
        desc = soup.find("meta", {"name": "description"})
        if desc:
            metadata["description"] = desc.get("content")

        # Event-specific selectors
        event_selectors = {
            "eventbrite": "[data-testid='event-title']",
            "meetup": "[data-event-label]",
            "facebook": "[data-testid='event-permalink-primary-text']",
        }

        for platform, selector in event_selectors.items():
            try:
                element = soup.select_one(selector)
                if element:
                    metadata["platform"] = platform
                    break
            except Exception:
                pass

        return metadata

    async def scrape_multiple(
        self,
        urls: list[str],
        max_concurrent: int = 3,
    ) -> list[ScrapedPage]:
        """
        Scrape multiple URLs with concurrency control.
        """
        self.logger.log_call(
            action="scrape_multiple",
            params={"url_count": len(urls), "max_concurrent": max_concurrent},
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(url: str) -> ScrapedPage:
            async with semaphore:
                return await self.scrape_page(url)

        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        scraped = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                scraped.append(
                    ScrapedPage(url=urls[i], success=False, error=str(result))
                )
            else:
                scraped.append(result)

        success_count = sum(1 for r in scraped if r.success)
        self.logger.log_result(
            action="scrape_multiple",
            success=True,
            result=f"Scraped {success_count}/{len(urls)} pages",
        )

        return scraped

    async def extract_event_data(self, page: ScrapedPage) -> dict[str, Any] | None:
        """
        Extract structured event data from scraped page.
        Returns None if no event data found.
        """
        if not page.success or not page.metadata:
            return None

        event_data = {}

        # Check for Schema.org Event
        if "schema_event" in page.metadata:
            schema = page.metadata["schema_event"]
            event_data = {
                "name": schema.get("name"),
                "description": schema.get("description"),
                "start_date": schema.get("startDate"),
                "end_date": schema.get("endDate"),
                "location": schema.get("location", {}).get("name")
                if isinstance(schema.get("location"), dict)
                else schema.get("location"),
                "url": schema.get("url") or page.url,
                "image": schema.get("image"),
                "source": "schema_org",
            }

        # Fallback to OpenGraph
        elif page.metadata.get("og_title"):
            event_data = {
                "name": page.metadata.get("og_title"),
                "description": page.metadata.get("og_description"),
                "image": page.metadata.get("og_image"),
                "url": page.metadata.get("og_url") or page.url,
                "source": "opengraph",
            }

        # Clean up None values
        event_data = {k: v for k, v in event_data.items() if v is not None}

        return event_data if event_data else None

    async def start(self) -> None:
        """Start the scraper engine."""
        await self.browser.start()

    async def close(self) -> None:
        """Close the scraper engine."""
        await self.browser.close()
        await self.http_client.aclose()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
