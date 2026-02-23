"""
SerperAPI Search Integration.
Google Search Results API via serper.dev.
"""
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

logger = get_logger("serper")


@dataclass
class SerperResultItem:
    """Single search result from SerperAPI."""

    title: str
    link: str
    snippet: str
    position: int
    source: str = "serper"
    date: str | None = None


@dataclass
class SerperResult:
    """Complete result from SerperAPI search."""

    results: list[SerperResultItem] = field(default_factory=list)
    total_results: int = 0
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class SerperSearch:
    """SerperAPI client for Google search results via serper.dev."""

    BASE_URL = "https://google.serper.dev/search"

    def __init__(self):
        self.api_key = settings.serper_api_key
        self.logger = ToolCallLogger("serper")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json",
            },
        )

    async def search(
        self,
        query: str,
        location: str | None = None,
        num_results: int = 10,
    ) -> SerperResult:
        """Search via SerperAPI."""
        self.logger.log_call(
            action="search",
            params={"query": query[:100], "location": location, "num_results": num_results},
        )

        body: dict[str, Any] = {"q": query, "num": num_results}
        if location:
            # Extract country code hint from location
            body["gl"] = "ch"  # Default to Switzerland

        try:
            logger.info(f"[SERPER] Making request with query: {query[:100]}")
            response = await self.client.post(self.BASE_URL, json=body)
            response.raise_for_status()
            data = response.json()

            results = []
            for i, item in enumerate(data.get("organic", [])):
                result = SerperResultItem(
                    title=item.get("title", ""),
                    link=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    position=item.get("position", i + 1),
                    date=item.get("date"),
                )
                results.append(result)
                logger.info(f"[SERPER]   Result {i+1}: {result.title[:50]}... -> {result.link[:80]}")

                self.logger.log_source(
                    source_api="serper",
                    source_url=result.link,
                    data_type="organic_result",
                )

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(results)} results",
            )

            return SerperResult(
                results=results,
                total_results=len(results),
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[SERPER] HTTP error: {error_msg}")
            self.logger.log_result(action="search", success=False, error=error_msg)
            return SerperResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"[SERPER] Error: {e}")
            self.logger.log_result(action="search", success=False, error=str(e))
            return SerperResult(success=False, error=str(e))

    async def search_events(
        self,
        query: str,
        location: str,
        date_from: str | None = None,
        category: str | None = None,
    ) -> SerperResult:
        """Specialized event search via SerperAPI - targets individual event pages."""
        if category and hasattr(category, "value"):
            category = category.value

        # Build query targeting individual event pages on ticketing sites
        city = location.split(",")[0].strip()
        cat_str = category if category and category != "all" else "events"

        # Parse month/year from date for natural language
        month_str = ""
        if date_from:
            try:
                from dateutil import parser as dp
                d = dp.parse(date_from)
                month_str = d.strftime("%B %Y")
            except Exception:
                month_str = date_from

        event_query = f"{cat_str} {city} {month_str} tickets site:eventbrite.com OR site:eventfrog.ch OR site:ticketcorner.ch OR site:songkick.com"

        logger.info(f"[SERPER] search_events query: {event_query}")
        return await self.search(query=event_query, location=location, num_results=20)

    async def health_check(self) -> bool:
        """Check if SerperAPI is accessible."""
        try:
            result = await self.search("test", num_results=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
