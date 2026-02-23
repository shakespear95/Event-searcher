"""
Perplexity Search Integration.
The "Truth Engine" - provides verified search results with source URLs.
"""
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

# Add module-level logger for detailed output
logger = get_logger("perplexity")


@dataclass
class PerplexityResult:
    """Single result from Perplexity search."""

    content: str
    sources: list[str]
    citations: list[dict[str, str]]
    success: bool
    error: str | None = None
    raw_response: Any = None


class PerplexitySearch:
    """
    Perplexity API client for event search.

    Perplexity is our "Truth Engine" - it provides synthesized answers
    with verified source URLs (Rule PR1).
    """

    BASE_URL = "https://api.perplexity.ai"

    def __init__(self):
        self.api_key = settings.perplexity_api_key
        self.logger = ToolCallLogger("perplexity")
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

    async def search(
        self,
        query: str,
        location: str | None = None,
        focus: str = "internet",
        max_results: int = 20,
    ) -> PerplexityResult:
        """
        Search for events using Perplexity.

        Args:
            query: Search query (optimized by Claude)
            location: Geographic focus
            focus: Search focus (internet, academic, etc.)
            max_results: Maximum number of results

        Returns:
            PerplexityResult with content and source URLs
        """
        self.logger.log_call(
            action="search",
            params={
                "query": query,
                "location": location,
                "focus": focus,
            },
        )

        # Build the search prompt
        search_prompt = query
        if location:
            search_prompt = f"{query} in {location}"

        # Add instructions for event-specific results
        system_prompt = """You are an event discovery assistant. When searching for events:
1. Focus on specific, upcoming events with dates and locations
2. Include official event pages and verified sources
3. Prioritize lesser-known "hidden gem" events over mainstream ones
4. Always cite your sources with URLs
5. If an event has no verifiable source, do not include it

Format each event with: Name, Date/Time, Location, Description, Source URL"""

        try:
            logger.info(f"[PERPLEXITY] ========== SEARCH START ==========")
            logger.info(f"[PERPLEXITY] Query: {search_prompt[:150]}...")
            logger.info(f"[PERPLEXITY] Making API request to Perplexity...")

            response = await self.client.post(
                f"{self.BASE_URL}/chat/completions",
                json={
                    "model": "sonar",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": search_prompt},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "search_domain_filter": [],
                    "return_citations": True,
                    "return_images": False,
                    "search_recency_filter": "month",
                },
            )

            logger.info(f"[PERPLEXITY] Response status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            # Extract content and citations
            content = ""
            sources = []
            citations = []

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                logger.info(f"[PERPLEXITY] Got content response ({len(content)} chars)")
                # Log a preview of the content
                logger.info(f"[PERPLEXITY] Content preview: {content[:500]}...")

            if "citations" in data:
                sources = data["citations"]
                citations = [{"url": url, "index": i} for i, url in enumerate(sources)]
                logger.info(f"[PERPLEXITY] Found {len(sources)} source citations:")
                for i, src in enumerate(sources):
                    logger.info(f"[PERPLEXITY]   Source {i+1}: {src}")
            else:
                logger.warning("[PERPLEXITY] No citations in response")

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(sources)} sources",
            )

            # Log each source for traceability
            for source in sources:
                self.logger.log_source(
                    source_api="perplexity",
                    source_url=source,
                    data_type="event_search",
                )

            logger.info(f"[PERPLEXITY] ========== SEARCH COMPLETE ==========")

            return PerplexityResult(
                content=content,
                sources=sources,
                citations=citations,
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[PERPLEXITY] HTTP ERROR: {error_msg}")
            self.logger.log_result(
                action="search",
                success=False,
                error=error_msg,
            )
            return PerplexityResult(
                content="",
                sources=[],
                citations=[],
                success=False,
                error=error_msg,
            )
        except Exception as e:
            logger.error(f"[PERPLEXITY] EXCEPTION: {str(e)}")
            self.logger.log_result(
                action="search",
                success=False,
                error=str(e),
            )
            return PerplexityResult(
                content="",
                sources=[],
                citations=[],
                success=False,
                error=str(e),
            )

    async def search_events(
        self,
        query: str,
        category: str,
        location: str,
        date_from: str,
        date_to: str,
        hidden_gems: bool = True,
    ) -> PerplexityResult:
        """
        Specialized event search with category and date filters.
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
                "category": category,
                "location": location,
                "date_from": date_from,
                "hidden_gems": hidden_gems,
            },
        )

        # Build detailed query - maximize event count
        date_to_str = f" to {date_to}" if date_to and date_to != date_from else ""
        event_query = f"""Find at least 15-20 upcoming {category} events in {location} from {date_from}{date_to_str}.

{"Focus on unique local events, hidden gems, and lesser-known happenings in addition to popular ones." if hidden_gems else "Include both popular and local events."}

For EACH event, include:
- **Event name/title**
- **Specific date** (REQUIRED - skip events without dates)
- **Time** if available
- **Venue name and location**
- **Brief description** (1 sentence)
- **Source URL or ticket link**

Search ALL of these: Eventbrite, Eventfrog, Ticketcorner, Songkick, local venue websites, community listings, and city event calendars.

List as many events as you can find (aim for 15-20+). Each event MUST have a confirmed date and a source URL."""

        logger.info(f"[PERPLEXITY] ========== SEARCH_EVENTS START ==========")
        logger.info(f"[PERPLEXITY] Category: {category}, Location: {location}")
        logger.info(f"[PERPLEXITY] Date from: {date_from}, Hidden gems: {hidden_gems}")
        logger.info(f"[PERPLEXITY] Event query: {event_query[:200]}...")

        result = await self.search(
            query=event_query,
            location=location,
        )

        logger.info(f"[PERPLEXITY] ========== SEARCH_EVENTS COMPLETE ==========")
        logger.info(f"[PERPLEXITY] Success: {result.success}, Sources: {len(result.sources)}")

        return result

    async def verify_event(self, event_name: str, event_url: str) -> bool:
        """
        Verify an event exists by checking its source URL.
        """
        self.logger.log_call(
            action="verify_event",
            params={"event_name": event_name, "url": event_url},
        )

        try:
            verify_query = f"""Verify this event exists and is still upcoming:
Event: {event_name}
URL: {event_url}

Respond with:
- VERIFIED if the event exists and the URL is valid
- UNVERIFIED if you cannot confirm the event
- EXPIRED if the event has already passed"""

            result = await self.search(query=verify_query)

            is_verified = "VERIFIED" in result.content.upper() and "UNVERIFIED" not in result.content.upper()

            self.logger.log_result(
                action="verify_event",
                success=True,
                result=f"Verified: {is_verified}",
            )

            return is_verified

        except Exception as e:
            self.logger.log_result(
                action="verify_event",
                success=False,
                error=str(e),
            )
            return False

    async def health_check(self) -> bool:
        """Check if Perplexity API is accessible."""
        try:
            result = await self.search("test query", max_results=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
