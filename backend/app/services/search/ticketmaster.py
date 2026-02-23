"""
Ticketmaster Discovery API Integration.
Provides structured event data with venues, dates, and pricing.
"""
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import ToolCallLogger, get_logger

logger = get_logger("ticketmaster")


@dataclass
class TicketmasterEvent:
    """Single event from Ticketmaster."""

    name: str
    url: str
    date: str | None = None
    time: str | None = None
    venue_name: str | None = None
    venue_address: str | None = None
    venue_city: str | None = None
    venue_country: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    price_currency: str | None = None
    image_url: str | None = None
    category: str | None = None
    source: str = "ticketmaster"
    raw_data: dict[str, Any] | None = None


@dataclass
class TicketmasterResult:
    """Complete result from Ticketmaster search."""

    events: list[TicketmasterEvent] = field(default_factory=list)
    total_results: int = 0
    success: bool = True
    error: str | None = None
    raw_response: Any = None


class TicketmasterSearch:
    """Ticketmaster Discovery API client."""

    BASE_URL = "https://app.ticketmaster.com/discovery/v2/events.json"

    def __init__(self):
        self.api_key = settings.ticketmaster_api_key
        self.logger = ToolCallLogger("ticketmaster")
        self.client = httpx.AsyncClient(timeout=30.0)

    # Country name -> Ticketmaster countryCode mapping
    COUNTRY_CODES = {
        "switzerland": "CH", "austria": "AT", "germany": "DE",
        "france": "FR", "italy": "IT", "spain": "ES",
        "united kingdom": "GB", "uk": "GB", "netherlands": "NL",
        "belgium": "BE", "portugal": "PT", "czech republic": "CZ",
        "poland": "PL", "sweden": "SE", "norway": "NO",
        "denmark": "DK", "finland": "FI", "ireland": "IE",
        "usa": "US", "united states": "US", "canada": "CA",
        "australia": "AU", "liechtenstein": "CH",  # TM has no LI, use CH
    }

    def _extract_country_code(self, location: str) -> str | None:
        """Extract Ticketmaster country code from location string."""
        parts = [p.strip().lower() for p in location.split(",")]
        for part in reversed(parts):
            if part in self.COUNTRY_CODES:
                return self.COUNTRY_CODES[part]
        # Default to CH for Swiss cities
        swiss_cities = ["zurich", "zürich", "bern", "basel", "geneva", "genève",
                        "lausanne", "lucerne", "luzern", "vaduz", "winterthur"]
        if parts[0] in swiss_cities:
            return "CH"
        return None

    async def search(
        self,
        keyword: str,
        city: str | None = None,
        country_code: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        size: int = 50,
    ) -> TicketmasterResult:
        """Search Ticketmaster Discovery API."""
        self.logger.log_call(
            action="search",
            params={
                "keyword": keyword[:100],
                "city": city,
                "country_code": country_code,
                "start_date": start_date,
                "size": size,
            },
        )

        params: dict[str, str] = {
            "apikey": self.api_key,
            "keyword": keyword,
            "size": str(size),
            "sort": "date,asc",
        }
        if city:
            params["city"] = city
        if country_code:
            params["countryCode"] = country_code
        if start_date:
            params["startDateTime"] = f"{start_date}T00:00:00Z"
        if end_date:
            params["endDateTime"] = f"{end_date}T23:59:59Z"

        try:
            logger.info(f"[TICKETMASTER] Making request with keyword: {keyword[:100]}, city: {city}")
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

            events = []
            embedded = data.get("_embedded", {})
            for item in embedded.get("events", []):
                # Extract venue info
                venues = item.get("_embedded", {}).get("venues", [])
                venue = venues[0] if venues else {}

                # Extract dates
                dates = item.get("dates", {}).get("start", {})

                # Extract price ranges
                price_ranges = item.get("priceRanges", [])
                price_range = price_ranges[0] if price_ranges else {}

                # Extract image (highest resolution)
                images = item.get("images", [])
                image_url = None
                if images:
                    sorted_images = sorted(
                        images, key=lambda x: x.get("width", 0), reverse=True
                    )
                    image_url = sorted_images[0].get("url")

                # Extract classification/category
                classifications = item.get("classifications", [])
                cat = (
                    classifications[0].get("segment", {}).get("name", "")
                    if classifications
                    else ""
                )

                event = TicketmasterEvent(
                    name=item.get("name", ""),
                    url=item.get("url", ""),
                    date=dates.get("localDate"),
                    time=dates.get("localTime"),
                    venue_name=venue.get("name"),
                    venue_address=venue.get("address", {}).get("line1"),
                    venue_city=venue.get("city", {}).get("name"),
                    venue_country=venue.get("country", {}).get("name"),
                    price_min=price_range.get("min"),
                    price_max=price_range.get("max"),
                    price_currency=price_range.get("currency"),
                    image_url=image_url,
                    category=cat,
                    raw_data=item,
                )
                events.append(event)
                logger.info(
                    f"[TICKETMASTER]   Event: {event.name[:50]}... "
                    f"date: {event.date}, venue: {event.venue_name}"
                )
                if event.url:
                    self.logger.log_source(
                        source_api="ticketmaster",
                        source_url=event.url,
                        data_type="ticketmaster_event",
                    )

            self.logger.log_result(
                action="search",
                success=True,
                result=f"Found {len(events)} events",
            )

            return TicketmasterResult(
                events=events,
                total_results=len(events),
                success=True,
                raw_response=data,
            )

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            logger.error(f"[TICKETMASTER] HTTP error: {error_msg}")
            self.logger.log_result(action="search", success=False, error=error_msg)
            return TicketmasterResult(success=False, error=error_msg)

        except Exception as e:
            logger.error(f"[TICKETMASTER] Error: {e}")
            self.logger.log_result(action="search", success=False, error=str(e))
            return TicketmasterResult(success=False, error=str(e))

    async def search_events(
        self,
        query: str,
        location: str,
        date_from: str | None = None,
        date_to: str | None = None,
        category: str | None = None,
    ) -> TicketmasterResult:
        """Specialized event search with broad coverage."""
        if category and hasattr(category, "value"):
            category = category.value

        city = location.split(",")[0].strip() if location else None
        country_code = self._extract_country_code(location)

        # First search: city + category keyword
        keyword = category if category and category != "all" else ""
        logger.info(f"[TICKETMASTER] search_events keyword='{keyword}', city={city}, country={country_code}")

        # Search 1: City-level with category
        result = await self.search(
            keyword=keyword,
            city=city,
            country_code=country_code,
            start_date=date_from,
            end_date=date_to,
            size=50,
        )

        # Search 2: If city search returned few results, broaden to country-level
        if len(result.events) < 15 and country_code:
            logger.info(f"[TICKETMASTER] City search returned only {len(result.events)}, broadening to country={country_code}")
            broader = await self.search(
                keyword=keyword,
                city=None,
                country_code=country_code,
                start_date=date_from,
                end_date=date_to,
                size=50,
            )
            if broader.success:
                # Merge, dedup by URL
                seen_urls = {e.url for e in result.events}
                for event in broader.events:
                    if event.url not in seen_urls:
                        result.events.append(event)
                        seen_urls.add(event.url)
                result.total_results = len(result.events)
                logger.info(f"[TICKETMASTER] After broadening: {len(result.events)} total events")

        return result

    async def health_check(self) -> bool:
        """Check if Ticketmaster API is accessible."""
        try:
            result = await self.search("test", size=1)
            return result.success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
