"""
Search Result Merger.
Combines and deduplicates results from all search sources.
"""
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger

from .perplexity import PerplexityResult
from .serpapi import SerpAPIResult, SerpAPIResultItem
from .serper import SerperResult
from .firecrawl import FirecrawlResult
from .exa import ExaResult
from .ticketmaster import TicketmasterResult

logger = get_logger("search.merger")


@dataclass
class MergedResult:
    """A single merged result from multiple sources."""

    title: str
    url: str
    snippet: str
    sources: list[str]  # Which APIs provided this result
    perplexity_content: str | None = None
    serpapi_data: dict[str, Any] | None = None
    confidence_score: float = 0.0
    is_duplicate: bool = False


@dataclass
class MergedSearchResults:
    """Combined results from all search sources."""

    results: list[MergedResult] = field(default_factory=list)
    perplexity_success: bool = False
    serpapi_success: bool = False
    serper_success: bool = False
    firecrawl_success: bool = False
    exa_success: bool = False
    ticketmaster_success: bool = False
    total_raw_results: int = 0
    total_after_dedup: int = 0
    sources_used: list[str] = field(default_factory=list)


class SearchMerger:
    """
    Merges and deduplicates search results from multiple sources.

    Handles:
    - URL normalization for deduplication
    - Source tracking for traceability
    - Confidence scoring based on multiple sources
    - Filtering out listing/index pages that aren't specific events
    """

    # URL patterns that indicate listing/index pages, not specific events
    LISTING_PAGE_PATTERNS = [
        r'/events/?$',
        r'/events/?\?',
        r'/d/[^/]+/events/?',          # eventbrite.com/d/.../events/
        r'/d/[^/]+/free--events/?',     # eventbrite.com/d/.../free--events/
        r'/d/[^/]+/[^/]+/$',           # eventbrite.com/d/.../category/
        r'/whats-on/?$',
        r'/what-to-do/?$',
        r'/things-to-do/?$',
        r'/calendar/?$',
        r'/events/month/',
        r'/events/week/',
        r'/sitesearch/',
        r'/search\?',
        r'/island/[^/]+$',             # islandsevents.com/island/mallorca (index)
    ]

    def _is_listing_page(self, url: str) -> bool:
        """Check if a URL is a listing/index page rather than a specific event."""
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")

        # Very short paths are usually index pages
        if path.count("/") <= 1:
            return True

        # Check against known listing patterns
        for pattern in self.LISTING_PAGE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True

        return False

    def __init__(self):
        self.seen_urls: set[str] = set()
        self.seen_titles: set[str] = set()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison."""
        parsed = urlparse(url)
        # Remove trailing slashes, www prefix, and query params for comparison
        normalized = f"{parsed.scheme}://{parsed.netloc.replace('www.', '')}{parsed.path.rstrip('/')}"
        return normalized.lower()

    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        # Remove common suffixes and normalize
        title = title.lower().strip()
        for suffix in [" - eventbrite", " | meetup", " - tickets", " | events"]:
            title = title.replace(suffix, "")
        return title

    def _is_duplicate(self, url: str, title: str) -> bool:
        """Check if result is a duplicate."""
        norm_url = self._normalize_url(url)

        # Check URL - this is the primary deduplication
        if norm_url in self.seen_urls:
            return True

        # Only check title if it's not empty
        # Empty titles should not trigger deduplication
        if title and title.strip():
            norm_title = self._normalize_title(title)
            if norm_title in self.seen_titles:
                return True

        return False

    def _mark_seen(self, url: str, title: str) -> None:
        """Mark URL and title as seen."""
        self.seen_urls.add(self._normalize_url(url))
        # Only track non-empty titles
        if title and title.strip():
            self.seen_titles.add(self._normalize_title(title))

    def _find_existing(self, results: list[MergedResult], url: str) -> MergedResult | None:
        """Find an existing result by normalized URL."""
        norm_url = self._normalize_url(url)
        return next(
            (r for r in results if self._normalize_url(r.url) == norm_url),
            None,
        )

    def _parse_events_from_content(self, content: str) -> list[dict[str, str]]:
        """Parse structured events from Perplexity markdown content.

        Extracts event name, date, venue, description, and any mentioned URLs
        from the typical Perplexity response format using bold markdown headers.
        """
        events: list[dict[str, str]] = []
        current: dict[str, str] = {}

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match bold event headers like "**Event Name**" at the start of a line
            # or "- **Event Name**" or "1. **Event Name**"
            header_match = re.match(r'^(?:[-*\d.]+\s*)?\*\*([^*]+)\*\*', line)
            if header_match:
                text_after = line[header_match.end():].strip()
                # Check if it's a field label like "**Date**: ..." or "**Event name/title**: ..."
                is_field = text_after.startswith(':') or text_after.startswith('-')
                field_label = header_match.group(1).strip().lower()
                field_labels = ['date', 'time', 'venue', 'location', 'description',
                                'source', 'price', 'event name', 'event name/title',
                                'specific date', 'brief description', 'venue name',
                                'source url', 'venue name and location']

                if is_field and any(field_label.startswith(fl) for fl in field_labels):
                    # This is a field within an event
                    value = text_after.lstrip(':- ').strip()
                    if 'name' in field_label and 'title' in field_label:
                        if current.get("name"):
                            events.append(current)
                        current = {"name": value}
                    elif 'date' in field_label and current:
                        current["date"] = value
                    elif 'time' in field_label and current:
                        current["time"] = value
                    elif 'venue' in field_label or ('location' in field_label and field_label != 'location'):
                        if current:
                            current["venue"] = value
                    elif 'description' in field_label and current:
                        current["description"] = value
                    elif 'source' in field_label and current:
                        current["source_url"] = value
                else:
                    # This is an event title header
                    if current.get("name"):
                        events.append(current)
                    current = {"name": header_match.group(1).strip()}
                    # Check if there's extra info after the bold
                    if text_after.startswith(':') or text_after.startswith('–') or text_after.startswith('-'):
                        current["description"] = text_after.lstrip(':–- ').strip()
                continue

            # Match "- Date: ..." or "  Date: ..." style fields
            field_match = re.match(r'^[-•]\s*\*?\*?(\w[\w\s/]*?)\*?\*?\s*[:]\s*(.+)', line)
            if field_match and current:
                key = field_match.group(1).strip().lower()
                value = field_match.group(2).strip()
                if 'date' in key:
                    current["date"] = value
                elif 'time' in key:
                    current["time"] = value
                elif 'venue' in key or 'location' in key:
                    current["venue"] = value
                elif 'description' in key:
                    current["description"] = value
                elif 'source' in key or 'url' in key or 'ticket' in key:
                    current["source_url"] = value

        if current.get("name"):
            events.append(current)

        return events

    def merge(
        self,
        perplexity_result: PerplexityResult | None,
        serpapi_result: SerpAPIResult | None,
        serper_result: SerperResult | None = None,
        firecrawl_result: FirecrawlResult | None = None,
        exa_result: ExaResult | None = None,
        ticketmaster_result: TicketmasterResult | None = None,
        max_results: int = 50,
    ) -> MergedSearchResults:
        logger.info("=" * 60)
        logger.info("MERGER INPUT DIAGNOSTIC")
        logger.info("=" * 60)
        logger.info(f"  max_results cap: {max_results}")
        logger.info(f"  perplexity: present={perplexity_result is not None}, success={perplexity_result.success if perplexity_result else 'N/A'}, sources={len(perplexity_result.sources) if perplexity_result and perplexity_result.success else 0}")
        logger.info(f"  serpapi:    present={serpapi_result is not None}, success={serpapi_result.success if serpapi_result else 'N/A'}, organic={len(serpapi_result.results) if serpapi_result and serpapi_result.success else 0}, events={len(serpapi_result.events) if serpapi_result and serpapi_result.success else 0}")
        logger.info(f"  serper:     present={serper_result is not None}, success={serper_result.success if serper_result else 'N/A'}, results={len(serper_result.results) if serper_result and serper_result.success else 0}")
        logger.info(f"  firecrawl:  present={firecrawl_result is not None}, success={firecrawl_result.success if firecrawl_result else 'N/A'}, results={len(firecrawl_result.results) if firecrawl_result and firecrawl_result.success else 0}")
        logger.info(f"  exa:        present={exa_result is not None}, success={exa_result.success if exa_result else 'N/A'}, results={len(exa_result.results) if exa_result and exa_result.success else 0}")
        logger.info(f"  ticketmaster: present={ticketmaster_result is not None}, success={ticketmaster_result.success if ticketmaster_result else 'N/A'}, events={len(ticketmaster_result.events) if ticketmaster_result and ticketmaster_result.success else 0}")
        logger.info("=" * 60)
        """
        Merge results from all search sources.

        Priority / confidence scores:
        - Multi-source (found in 2+): base + 0.2 per additional, capped at 1.0
        - Ticketmaster: 0.85 (structured event data)
        - Google Events (SerpAPI): 0.8
        - Perplexity: 0.7
        - Firecrawl: 0.6
        - Exa: 0.55
        - SerpAPI organic: 0.5
        - Serper organic: 0.5
        """
        self.seen_urls.clear()
        self.seen_titles.clear()

        merged = MergedSearchResults()
        results: list[MergedResult] = []

        # Track which sources were used
        if perplexity_result and perplexity_result.success:
            merged.perplexity_success = True
            merged.sources_used.append("perplexity")

        if serpapi_result and serpapi_result.success:
            merged.serpapi_success = True
            merged.sources_used.append("serpapi")

        if serper_result and serper_result.success:
            merged.serper_success = True
            merged.sources_used.append("serper")

        if firecrawl_result and firecrawl_result.success:
            merged.firecrawl_success = True
            merged.sources_used.append("firecrawl")

        if exa_result and exa_result.success:
            merged.exa_success = True
            merged.sources_used.append("exa")

        if ticketmaster_result and ticketmaster_result.success:
            merged.ticketmaster_success = True
            merged.sources_used.append("ticketmaster")

        # Parse events from Perplexity content to enrich results
        parsed_events: list[dict[str, str]] = []
        if perplexity_result and perplexity_result.success and perplexity_result.content:
            parsed_events = self._parse_events_from_content(perplexity_result.content)
            logger.info(f"[MERGER] Parsed {len(parsed_events)} events from Perplexity content")
            for i, pe in enumerate(parsed_events):
                logger.info(f"[MERGER]   Parsed event {i+1}: {pe.get('name', 'unnamed')[:60]}")

        # === Process Perplexity sources first ===
        perplexity_added = 0
        perplexity_duped = 0
        listing_filtered = 0
        if perplexity_result and perplexity_result.success:
            for idx, source_url in enumerate(perplexity_result.sources):
                if self._is_listing_page(source_url):
                    listing_filtered += 1
                    logger.debug(f"[MERGER] Filtered listing page: {source_url}")
                    continue
                if not self._is_duplicate(source_url, ""):
                    # Try to match a parsed event to this source URL
                    title = ""
                    snippet = ""
                    if idx < len(parsed_events):
                        pe = parsed_events[idx]
                        title = pe.get("name", "")
                        parts = []
                        if pe.get("date"):
                            parts.append(pe["date"])
                        if pe.get("venue"):
                            parts.append(pe["venue"])
                        if pe.get("description"):
                            parts.append(pe["description"])
                        snippet = " | ".join(parts)

                    result = MergedResult(
                        title=title,
                        url=source_url,
                        snippet=snippet,
                        sources=["perplexity"],
                        perplexity_content=perplexity_result.content,
                        confidence_score=0.7,
                    )
                    results.append(result)
                    self._mark_seen(source_url, title)
                    perplexity_added += 1
                else:
                    perplexity_duped += 1
                    logger.info(f"[MERGER] DEDUP perplexity source #{idx}: {source_url[:80]}")

            merged.total_raw_results += len(perplexity_result.sources)
            logger.info(f"[MERGER] Perplexity: {perplexity_added} added, {perplexity_duped} deduped (from {len(perplexity_result.sources)} sources)")

        # === Process SerpAPI results ===
        serpapi_added = 0
        serpapi_enriched = 0
        serpapi_duped = 0
        serpapi_events_added = 0
        serpapi_events_duped = 0
        if serpapi_result and serpapi_result.success:
            for item in serpapi_result.results:
                if not item.link:
                    continue

                existing = self._find_existing(results, item.link)
                if existing:
                    existing.title = item.title
                    existing.snippet = item.snippet
                    existing.sources.append("serpapi")
                    existing.serpapi_data = {
                        "position": item.position,
                        "displayed_link": item.displayed_link,
                        "date": item.date,
                    }
                    existing.confidence_score = min(existing.confidence_score + 0.2, 1.0)
                    serpapi_enriched += 1
                elif self._is_listing_page(item.link):
                    listing_filtered += 1
                    continue
                elif not self._is_duplicate(item.link, item.title):
                    result = MergedResult(
                        title=item.title,
                        url=item.link,
                        snippet=item.snippet,
                        sources=["serpapi"],
                        serpapi_data={
                            "position": item.position,
                            "displayed_link": item.displayed_link,
                            "date": item.date,
                        },
                        confidence_score=0.5,
                    )
                    results.append(result)
                    self._mark_seen(item.link, item.title)
                    serpapi_added += 1
                else:
                    serpapi_duped += 1
                    logger.info(f"[MERGER] DEDUP serpapi organic: {item.title[:50]}... -> {item.link[:60]}")

            merged.total_raw_results += len(serpapi_result.results)

            # Also include Google Events results (with structured venue/date data)
            for event in serpapi_result.events:
                event_url = event.get("link", "")
                event_title = event.get("title", "")

                if not event_url or self._is_listing_page(event_url):
                    if event_url:
                        listing_filtered += 1
                    continue
                if not self._is_duplicate(event_url, event_title):
                    # Extract structured data from Google Events
                    date_info = event.get("date", {})
                    date_when = date_info.get("when") if isinstance(date_info, dict) else date_info
                    date_start = date_info.get("start_date") if isinstance(date_info, dict) else None

                    # Google Events venue info is in address field
                    venue_info = event.get("venue", {}) if isinstance(event.get("venue"), dict) else {}
                    event_address = event.get("address", [])
                    address_str = ", ".join(event_address) if isinstance(event_address, list) else str(event_address) if event_address else ""

                    # Build rich snippet
                    snippet_parts = []
                    if date_when:
                        snippet_parts.append(f"Date: {date_when}")
                    if venue_info.get("name"):
                        snippet_parts.append(f"Venue: {venue_info['name']}")
                    if address_str:
                        snippet_parts.append(f"Address: {address_str}")
                    desc = event.get("description", "")
                    if desc:
                        snippet_parts.append(desc)

                    serpapi_event_data = {
                        **event,
                        "date": date_start or date_when,
                        "date_when": date_when,
                        "venue_name": venue_info.get("name") if venue_info else None,
                        "venue_address": address_str or None,
                    }

                    result = MergedResult(
                        title=event_title,
                        url=event_url,
                        snippet=" | ".join(snippet_parts) if snippet_parts else desc,
                        sources=["serpapi_events"],
                        serpapi_data=serpapi_event_data,
                        confidence_score=0.8,  # Google Events are high quality
                    )
                    results.append(result)
                    self._mark_seen(event_url, event_title)
                    serpapi_events_added += 1
                else:
                    serpapi_events_duped += 1
                    if event_url:
                        logger.info(f"[MERGER] DEDUP serpapi event: {event_title[:50]}...")

            logger.info(f"[MERGER] SerpAPI organic: {serpapi_added} added, {serpapi_enriched} enriched existing, {serpapi_duped} deduped (from {len(serpapi_result.results)} results)")
            logger.info(f"[MERGER] SerpAPI events: {serpapi_events_added} added, {serpapi_events_duped} deduped (from {len(serpapi_result.events)} events)")

        # === Process Serper results ===
        serper_added = 0
        serper_enriched = 0
        serper_duped = 0
        if serper_result and serper_result.success:
            for item in serper_result.results:
                if not item.link:
                    continue

                existing = self._find_existing(results, item.link)
                if existing:
                    existing.sources.append("serper")
                    existing.confidence_score = min(existing.confidence_score + 0.2, 1.0)
                    serper_enriched += 1
                elif self._is_listing_page(item.link):
                    listing_filtered += 1
                    continue
                elif not self._is_duplicate(item.link, item.title):
                    result = MergedResult(
                        title=item.title,
                        url=item.link,
                        snippet=item.snippet,
                        sources=["serper"],
                        confidence_score=0.5,
                    )
                    results.append(result)
                    self._mark_seen(item.link, item.title)
                    serper_added += 1
                else:
                    serper_duped += 1
                    logger.info(f"[MERGER] DEDUP serper: {item.title[:50]}... -> {item.link[:60]}")

            merged.total_raw_results += len(serper_result.results)
            logger.info(f"[MERGER] Serper: {serper_added} added, {serper_enriched} enriched, {serper_duped} deduped (from {len(serper_result.results)} results)")

        # === Process Firecrawl results ===
        firecrawl_added = 0
        firecrawl_enriched = 0
        firecrawl_duped = 0
        if firecrawl_result and firecrawl_result.success:
            for item in firecrawl_result.results:
                if not item.url:
                    continue

                existing = self._find_existing(results, item.url)
                if existing:
                    existing.sources.append("firecrawl")
                    existing.confidence_score = min(existing.confidence_score + 0.2, 1.0)
                    # Enrich with Firecrawl's markdown content if richer
                    if item.content and len(item.content) > len(existing.snippet or ""):
                        existing.snippet = item.content[:500]
                    firecrawl_enriched += 1
                elif self._is_listing_page(item.url):
                    listing_filtered += 1
                    continue
                elif not self._is_duplicate(item.url, item.title):
                    result = MergedResult(
                        title=item.title,
                        url=item.url,
                        snippet=item.content[:500] if item.content else "",
                        sources=["firecrawl"],
                        confidence_score=0.6,
                    )
                    results.append(result)
                    self._mark_seen(item.url, item.title)
                    firecrawl_added += 1
                else:
                    firecrawl_duped += 1
                    logger.info(f"[MERGER] DEDUP firecrawl: {item.title[:50]}... -> {item.url[:60]}")

            merged.total_raw_results += len(firecrawl_result.results)
            logger.info(f"[MERGER] Firecrawl: {firecrawl_added} added, {firecrawl_enriched} enriched, {firecrawl_duped} deduped (from {len(firecrawl_result.results)} results)")

        # === Process Exa results ===
        exa_added = 0
        exa_enriched = 0
        exa_duped = 0
        if exa_result and exa_result.success:
            for item in exa_result.results:
                if not item.url:
                    continue

                existing = self._find_existing(results, item.url)
                if existing:
                    existing.sources.append("exa")
                    existing.confidence_score = min(existing.confidence_score + 0.2, 1.0)
                    exa_enriched += 1
                elif self._is_listing_page(item.url):
                    listing_filtered += 1
                    continue
                elif not self._is_duplicate(item.url, item.title):
                    result = MergedResult(
                        title=item.title,
                        url=item.url,
                        snippet=item.text[:500] if item.text else "",
                        sources=["exa"],
                        confidence_score=0.55,
                    )
                    results.append(result)
                    self._mark_seen(item.url, item.title)
                    exa_added += 1
                else:
                    exa_duped += 1
                    logger.info(f"[MERGER] DEDUP exa: {item.title[:50]}... -> {item.url[:60]}")

            merged.total_raw_results += len(exa_result.results)
            logger.info(f"[MERGER] Exa: {exa_added} added, {exa_enriched} enriched, {exa_duped} deduped (from {len(exa_result.results)} results)")

        # === Process Ticketmaster results (highest confidence -- structured event data) ===
        tm_added = 0
        tm_enriched = 0
        tm_duped = 0
        if ticketmaster_result and ticketmaster_result.success:
            for event in ticketmaster_result.events:
                if not event.url:
                    continue

                existing = self._find_existing(results, event.url)
                if existing:
                    existing.sources.append("ticketmaster")
                    existing.confidence_score = max(existing.confidence_score, 0.85)
                    tm_enriched += 1
                elif not self._is_duplicate(event.url, event.name):
                    # Build rich snippet from structured Ticketmaster data
                    snippet_parts = []
                    if event.date:
                        snippet_parts.append(f"Date: {event.date}")
                    if event.time:
                        snippet_parts.append(f"Time: {event.time}")
                    if event.venue_name:
                        snippet_parts.append(f"Venue: {event.venue_name}")
                    if event.price_min is not None:
                        price_str = f"${event.price_min}"
                        if event.price_max and event.price_max != event.price_min:
                            price_str += f" - ${event.price_max}"
                        snippet_parts.append(f"Price: {price_str}")

                    result = MergedResult(
                        title=event.name,
                        url=event.url,
                        snippet=" | ".join(snippet_parts),
                        sources=["ticketmaster"],
                        serpapi_data={
                            "date": event.date,
                            "time": event.time,
                            "venue_name": event.venue_name,
                            "venue_address": event.venue_address,
                            "venue_city": event.venue_city,
                            "venue_country": event.venue_country,
                            "venue_latitude": event.venue_latitude,
                            "venue_longitude": event.venue_longitude,
                            "price_min": event.price_min,
                            "price_max": event.price_max,
                            "price_currency": event.price_currency,
                            "image_url": event.image_url,
                            "category": event.category,
                            "performers": event.performers,
                            "genre": event.genre,
                            "subgenre": event.subgenre,
                            "timezone": event.timezone,
                            "on_sale_status": event.on_sale_status,
                            "please_note": event.please_note,
                            "promoter": event.promoter,
                            "all_images": event.all_images,
                            "accessibility_info": event.accessibility_info,
                        },
                        confidence_score=0.85,
                    )
                    results.append(result)
                    self._mark_seen(event.url, event.name)
                    tm_added += 1
                else:
                    tm_duped += 1
                    logger.info(f"[MERGER] DEDUP ticketmaster: {event.name[:50]}...")

            merged.total_raw_results += len(ticketmaster_result.events)
            logger.info(f"[MERGER] Ticketmaster: {tm_added} added, {tm_enriched} enriched, {tm_duped} deduped (from {len(ticketmaster_result.events)} events)")

        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)

        total_before_cap = len(results)

        # Limit results
        merged.results = results[:max_results]
        merged.total_after_dedup = len(merged.results)

        logger.info("=" * 60)
        logger.info("MERGER OUTPUT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Total raw inputs:     {merged.total_raw_results}")
        logger.info(f"  Listing pages filtered: {listing_filtered}")
        logger.info(f"  After dedup:          {total_before_cap}")
        if total_before_cap > max_results:
            logger.info(f"  After max_results cap ({max_results}): {len(merged.results)}  ** {total_before_cap - max_results} results DROPPED by cap **")
        else:
            logger.info(f"  After max_results cap ({max_results}): {len(merged.results)}")
        logger.info(f"  Sources used:         {merged.sources_used}")
        # Log all final results with their sources
        for i, r in enumerate(merged.results):
            logger.info(f"  [{i+1}] score={r.confidence_score:.2f} sources={r.sources} title={r.title[:50] if r.title else '(no title)'}...")
        logger.info("=" * 60)

        return merged

    def to_raw_list(self, merged: MergedSearchResults) -> list[dict[str, Any]]:
        """Convert merged results to raw list for LLM processing."""
        return [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "sources": r.sources,
                "confidence": r.confidence_score,
                "extra_data": r.serpapi_data,
            }
            for r in merged.results
        ]

    def get_perplexity_content(self, merged: MergedSearchResults) -> str | None:
        """Get the full Perplexity content for extraction."""
        for result in merged.results:
            if result.perplexity_content:
                return result.perplexity_content
        return None

    def get_source_urls(self, merged: MergedSearchResults) -> list[str]:
        """Get all unique source URLs."""
        return [r.url for r in merged.results]

    def get_serpapi_snippets(self, merged: MergedSearchResults) -> str:
        """Get concatenated snippets from all sources for context."""
        snippets = []
        for r in merged.results:
            if r.snippet:
                snippets.append(f"- {r.title}: {r.snippet}" if r.title else f"- {r.snippet}")
        return "\n".join(snippets) if snippets else ""
