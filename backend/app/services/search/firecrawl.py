"""
Firecrawl Search Integration.
Web scraping/crawling API for deep content extraction.
"""
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

logger = get_logger("firecrawl")


@dataclass
class FirecrawlResultItem:
    """Single result from Firecrawl."""

    url: str
    title: str
    content: str  # Markdown content
    source: str = "firecrawl"


@dataclass
class FirecrawlResult:
    """Complete result from Firecrawl search."""

    results: list[FirecrawlResultItem] = field(default_factory=list)
    total_results: int = 0
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class FirecrawlSearch:
    """Firecrawl API client for web search with content extraction."""

    BASE_URL = "https://api.firecrawl.dev/v1/search"

    def __init__(self):
        self.api_key = settings.firecrawl_api_key
        self.logger = ToolCallLogger("firecrawl")
        self.client = httpx.AsyncClient(
            timeout=60.0,  # Higher timeout -- Firecrawl does actual web scraping
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def search(self, query: str, limit: int = 10) -> FirecrawlResult:
        """Search via Firecrawl API."""
        self.logger.log_call(
            action="search",
            params={"query": query[:100], "limit": limit},
        )

        try:
            logger.info(f"[FIRECRAWL] Making request with query: {query[:100]}")
            response = await self.client.post(
                self.BASE_URL,
                json={"query": query, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("data", []):
                metadata = item.get("metadata", {})
                result = FirecrawlResultItem(
                    url=item.get("url", ""),
                    title=metadata.get("title", "") or item.get("title", ""),
                    content=item.get("markdown", "") or item.get("content", ""),
                )
                results.append(result)
                if result.url:
                    logger.info(f"[FIRECRAWL]   Result: {result.title[:50]}... -> {result.url[:80]}")
                    self.logger.log_source(
                        source_api="firecrawl",
                        source_url=result.url,
                        data_type="search_result",
                    )

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(results)} results",
            )

            return FirecrawlResult(
                results=results,
                total_results=len(results),
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[FIRECRAWL] HTTP error: {error_msg}")
            self.logger.log_result(action="search", success=False, error=error_msg)
            return FirecrawlResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"[FIRECRAWL] Error: {e}")
            self.logger.log_result(action="search", success=False, error=str(e))
            return FirecrawlResult(success=False, error=str(e))

    async def search_events(
        self,
        query: str,
        location: str,
        date_from: str | None = None,
        category: str | None = None,
    ) -> FirecrawlResult:
        """Specialized event search via Firecrawl."""
        if category and hasattr(category, "value"):
            category = category.value

        event_query = f"events in {location}"
        if category and category != "all":
            event_query = f"{category} events in {location}"
        if date_from:
            event_query = f"{event_query} {date_from}"

        logger.info(f"[FIRECRAWL] search_events query: {event_query}")
        return await self.search(query=event_query, limit=10)

    async def health_check(self) -> bool:
        """Check if Firecrawl API is accessible."""
        try:
            result = await self.search("test", limit=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
