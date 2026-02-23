"""
SerpAPI Search Integration.
Provides Google search results with raw links and snippets.
"""
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

# Add module-level logger for detailed output
logger = get_logger("serpapi")


@dataclass
class SerpAPIResultItem:
    """Single search result from SerpAPI."""

    title: str
    link: str
    snippet: str
    position: int
    source: str = "serpapi"
    displayed_link: str | None = None
    date: str | None = None
    thumbnail: str | None = None


@dataclass
class SerpAPIResult:
    """Complete result from SerpAPI search."""

    results: list[SerpAPIResultItem] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    total_results: int = 0
    search_time: float = 0.0
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class SerpAPISearch:
    """
    SerpAPI client for Google search results.

    Provides raw search results with links that can be
    scraped for additional details.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self):
        self.api_key = settings.serpapi_api_key
        self.logger = ToolCallLogger("serpapi")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        location: str | None = None,
        num_results: int = 20,
        search_type: str = "search",
    ) -> SerpAPIResult:
        """
        Search Google via SerpAPI.

        Args:
            query: Search query
            location: Geographic location for results
            num_results: Number of results to return
            search_type: Type of search (search, events, etc.)

        Returns:
            SerpAPIResult with search results
        """
        self.logger.log_call(
            action="search",
            params={
                "query": query,
                "location": location,
                "num_results": num_results,
                "type": search_type,
            },
        )

        params = {
            "api_key": self.api_key,
            "q": query,
            "num": num_results,
            "engine": "google",
        }

        if location:
            params["location"] = location
            params["gl"] = "li"  # Liechtenstein, adjust as needed

        try:
            logger.info(f"[SERPAPI] Making request to Google Search API with query: {query[:100]}")
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            events = []

            # Parse organic results
            if "organic_results" in data:
                logger.info(f"[SERPAPI] Found {len(data['organic_results'])} organic results")
                for i, item in enumerate(data["organic_results"]):
                    result = SerpAPIResultItem(
                        title=item.get("title", ""),
                        link=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        position=item.get("position", i + 1),
                        displayed_link=item.get("displayed_link"),
                        date=item.get("date"),
                        thumbnail=item.get("thumbnail"),
                    )
                    results.append(result)
                    logger.info(f"[SERPAPI]   Result {i+1}: {result.title[:50]}... -> {result.link[:80]}")

                    # Log source for traceability
                    self.logger.log_source(
                        source_api="serpapi",
                        source_url=result.link,
                        data_type="organic_result",
                    )
            else:
                logger.warning("[SERPAPI] No organic_results in response")

            # Parse events if available
            if "events_results" in data:
                events = data["events_results"]
                logger.info(f"[SERPAPI] Found {len(events)} event results")
                for i, event in enumerate(events):
                    logger.info(f"[SERPAPI]   Event {i+1}: {event.get('title', 'Unknown')[:50]}")
                    if "link" in event:
                        self.logger.log_source(
                            source_api="serpapi",
                            source_url=event["link"],
                            data_type="event_result",
                        )
            else:
                logger.info("[SERPAPI] No events_results in response")

            search_info = data.get("search_information", {})

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(results)} results, {len(events)} events",
            )

            return SerpAPIResult(
                results=results,
                events=events,
                total_results=search_info.get("total_results", len(results)),
                search_time=search_info.get("time_taken_displayed", 0),
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            self.logger.log_result(
                action="search",
                success=False,
                error=error_msg,
            )
            return SerpAPIResult(success=False, error=error_msg)

        except Exception as e:
            self.logger.log_result(
                action="search",
                success=False,
                error=str(e),
            )
            return SerpAPIResult(success=False, error=str(e))

    async def search_events(
        self,
        query: str,
        location: str,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
    ) -> SerpAPIResult:
        """
        Search for events using both Google Events and regular Google search.
        """
        # Handle enum values - extract .value if it's an enum
        if category and hasattr(category, 'value'):
            category = category.value
        elif category and 'EventCategory.' in str(category):
            # Handle string representation of enum like "EventCategory.SPORTS"
            category = str(category).replace('EventCategory.', '').lower()

        self.logger.log_call(
            action="search_events",
            params={
                "query": query[:50],
                "location": location,
                "date_from": date_from,
                "category": category,
            },
        )

        # Build event-specific query for regular Google search
        event_query = f"{location} events"
        if category and category != "all":
            event_query = f"{category} events {location}"
        if date_from:
            event_query = f"{event_query} {date_from}"

        logger.info(f"[SERPAPI] ========== SEARCH_EVENTS START ==========")
        logger.info(f"[SERPAPI] Location: {location}, Category: {category}, Date: {date_from}")
        logger.info(f"[SERPAPI] Built event query: {event_query}")

        results = []
        events = []

        # First, try regular Google search for event listings
        try:
            # Build more specific query targeting event aggregators and venue calendars
            full_query = f"{event_query} tickets eventbrite meetup"
            if date_from:
                # Add month/year context for better date-specific results
                full_query = f"{full_query} 2026"
            logger.info(f"[SERPAPI] Step 1: Regular Google Search with query: {full_query}")
            google_result = await self.search(
                query=full_query,
                location=location,
                num_results=20,
            )
            if google_result.success:
                results.extend(google_result.results)
                logger.info(f"[SERPAPI] Step 1 SUCCESS: Got {len(google_result.results)} organic results from Google Search")
                self.logger.log_result(
                    action="google_search",
                    success=True,
                    result=f"Found {len(google_result.results)} organic results",
                )
            else:
                logger.warning(f"[SERPAPI] Step 1 FAILED: Google Search returned success=False, error: {google_result.error}")
        except Exception as e:
            logger.error(f"[SERPAPI] Step 1 ERROR: Google Search exception: {str(e)}")
            self.logger.log_result(action="google_search", success=False, error=str(e))

        # Then try Google Events engine (needs simpler query - no dates)
        try:
            # Google Events works best with simple queries like "events in Zurich"
            google_events_query = f"events in {location}"
            if category and category != "all":
                google_events_query = f"{category} events in {location}"
            logger.info(f"[SERPAPI] Step 2: Google Events API with query: {google_events_query}")
            params = {
                "api_key": self.api_key,
                "q": google_events_query,
                "engine": "google_events",
            }

            response = await self.client.get(self.BASE_URL, params=params)
            logger.info(f"[SERPAPI] Step 2: Google Events API response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            event_results = data.get("events_results", [])
            events.extend(event_results)
            logger.info(f"[SERPAPI] Step 2 SUCCESS: Got {len(event_results)} events from Google Events API")

            # Convert events to results format
            for i, event in enumerate(event_results):
                result = SerpAPIResultItem(
                    title=event.get("title", ""),
                    link=event.get("link", ""),
                    snippet=event.get("description", ""),
                    position=len(results) + i + 1,
                    date=event.get("date", {}).get("when") if isinstance(event.get("date"), dict) else event.get("date"),
                )
                results.append(result)
                logger.info(f"[SERPAPI]   Event {i+1}: {result.title[:50]}... date: {result.date}")

                if result.link:
                    self.logger.log_source(
                        source_api="serpapi",
                        source_url=result.link,
                        data_type="google_event",
                    )

            self.logger.log_result(
                action="google_events",
                success=True,
                result=f"Found {len(event_results)} events",
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[SERPAPI] Step 2 HTTP ERROR: {e.response.status_code} - {e.response.text[:200]}")
            self.logger.log_result(
                action="google_events",
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.error(f"[SERPAPI] Step 2 ERROR: Google Events exception: {str(e)}")
            self.logger.log_result(
                action="google_events",
                success=False,
                error=str(e),
            )

        logger.info(f"[SERPAPI] ========== SEARCH_EVENTS COMPLETE ==========")
        logger.info(f"[SERPAPI] TOTAL: {len(results)} results, {len(events)} events")
        logger.info(f"[SERPAPI] Success: {len(results) > 0}")

        self.logger.log_result(
            action="search_events",
            success=True,
            result=f"Total: {len(results)} results, {len(events)} events",
        )

        return SerpAPIResult(
            results=results,
            events=events,
            total_results=len(results),
            success=len(results) > 0,
            raw_response=None,
        )

    async def search_local(
        self,
        query: str,
        location: str,
        radius_km: int = 25,
    ) -> SerpAPIResult:
        """
        Search for local places/venues using Google Local.
        """
        params = {
            "api_key": self.api_key,
            "q": query,
            "engine": "google_local",
            "location": location,
        }

        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            local_results = data.get("local_results", [])

            results = []
            for i, place in enumerate(local_results):
                result = SerpAPIResultItem(
                    title=place.get("title", ""),
                    link=place.get("link", "") or place.get("website", ""),
                    snippet=place.get("description", "") or place.get("type", ""),
                    position=i + 1,
                )
                results.append(result)

            self.logger.log_result(
                action="search_local",
                success=True,
                result=f"Found {len(results)} local results",
            )

            return SerpAPIResult(
                results=results,
                total_results=len(results),
                success=True,
                raw_response=data,
            )

        except Exception as e:
            self.logger.log_result(
                action="search_local",
                success=False,
                error=str(e),
            )
            return SerpAPIResult(success=False, error=str(e))

    async def health_check(self) -> bool:
        """Check if SerpAPI is accessible."""
        try:
            result = await self.search("test", num_results=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
