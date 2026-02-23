"""
Exa Search Integration.
Neural semantic search engine for high-quality results.
"""
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

logger = get_logger("exa")


@dataclass
class ExaResultItem:
    """Single result from Exa."""

    url: str
    title: str
    text: str
    score: float = 0.0
    source: str = "exa"
    published_date: str | None = None


@dataclass
class ExaResult:
    """Complete result from Exa search."""

    results: list[ExaResultItem] = field(default_factory=list)
    total_results: int = 0
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class ExaSearch:
    """Exa API client for neural semantic search."""

    BASE_URL = "https://api.exa.ai/search"

    def __init__(self):
        self.api_key = settings.exa_api_key
        self.logger = ToolCallLogger("exa")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
            },
        )

    async def search(self, query: str, num_results: int = 10) -> ExaResult:
        """Search via Exa neural search."""
        self.logger.log_call(
            action="search",
            params={"query": query[:100], "num_results": num_results},
        )

        try:
            logger.info(f"[EXA] Making neural search request with query: {query[:100]}")
            response = await self.client.post(
                self.BASE_URL,
                json={
                    "query": query,
                    "numResults": num_results,
                    "type": "neural",
                    "useAutoprompt": True,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                result = ExaResultItem(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    text=item.get("text", ""),
                    score=item.get("score", 0.0),
                    published_date=item.get("publishedDate"),
                )
                results.append(result)
                if result.url:
                    logger.info(f"[EXA]   Result: {result.title[:50]}... -> {result.url[:80]}")
                    self.logger.log_source(
                        source_api="exa",
                        source_url=result.url,
                        data_type="neural_result",
                    )

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(results)} results",
            )

            return ExaResult(
                results=results,
                total_results=len(results),
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[EXA] HTTP error: {error_msg}")
            self.logger.log_result(action="search", success=False, error=error_msg)
            return ExaResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"[EXA] Error: {e}")
            self.logger.log_result(action="search", success=False, error=str(e))
            return ExaResult(success=False, error=str(e))

    async def search_events(
        self,
        query: str,
        location: str,
        date_from: str | None = None,
        category: str | None = None,
    ) -> ExaResult:
        """Specialized event search with neural query - targets individual event pages."""
        if category and hasattr(category, "value"):
            category = category.value

        city = location.split(",")[0].strip()
        cat_str = category if category and category != "all" else "live"

        # Parse month for natural query
        month_str = ""
        if date_from:
            try:
                from dateutil import parser as dp
                d = dp.parse(date_from)
                month_str = d.strftime("%B %Y")
            except Exception:
                month_str = date_from

        # Neural search works best with natural language describing what we want
        event_query = f"Here is an event page for a {cat_str} event happening in {city} in {month_str} with tickets available"

        logger.info(f"[EXA] search_events query: {event_query}")
        return await self.search(query=event_query, num_results=15)

    async def health_check(self) -> bool:
        """Check if Exa API is accessible."""
        try:
            result = await self.search("test", num_results=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
