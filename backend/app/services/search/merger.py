"""
Search Result Merger.
Combines and deduplicates results from Perplexity and SerpAPI.
"""
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.core.logging import get_logger

from .perplexity import PerplexityResult
from .serpapi import SerpAPIResult, SerpAPIResultItem

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
    """

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
        max_results: int = 20,
    ) -> MergedSearchResults:
        """
        Merge results from Perplexity and SerpAPI.

        Priority:
        1. Results found in both sources (higher confidence)
        2. Perplexity results (synthesized with context)
        3. SerpAPI results (raw Google results)
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

        # Parse events from Perplexity content to enrich results
        parsed_events: list[dict[str, str]] = []
        if perplexity_result and perplexity_result.success and perplexity_result.content:
            parsed_events = self._parse_events_from_content(perplexity_result.content)
            logger.info(f"[MERGER] Parsed {len(parsed_events)} events from Perplexity content")
            for i, pe in enumerate(parsed_events):
                logger.info(f"[MERGER]   Parsed event {i+1}: {pe.get('name', 'unnamed')[:60]}")

        # Process Perplexity sources first
        if perplexity_result and perplexity_result.success:
            for idx, source_url in enumerate(perplexity_result.sources):
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

            merged.total_raw_results += len(perplexity_result.sources)

        # Process SerpAPI results
        if serpapi_result and serpapi_result.success:
            for item in serpapi_result.results:
                if not item.link:
                    continue

                # Check if this URL was already found by Perplexity
                norm_url = self._normalize_url(item.link)
                existing = next(
                    (r for r in results if self._normalize_url(r.url) == norm_url),
                    None,
                )

                if existing:
                    # Enrich existing result
                    existing.title = item.title
                    existing.snippet = item.snippet
                    existing.sources.append("serpapi")
                    existing.serpapi_data = {
                        "position": item.position,
                        "displayed_link": item.displayed_link,
                        "date": item.date,
                    }
                    existing.confidence_score = 0.9  # Found in both sources
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

            merged.total_raw_results += len(serpapi_result.results)

            # Also include Google Events results
            for event in serpapi_result.events:
                event_url = event.get("link", "")
                event_title = event.get("title", "")

                if event_url and not self._is_duplicate(event_url, event_title):
                    result = MergedResult(
                        title=event_title,
                        url=event_url,
                        snippet=event.get("description", ""),
                        sources=["serpapi_events"],
                        serpapi_data=event,
                        confidence_score=0.8,  # Google Events are high quality
                    )
                    results.append(result)
                    self._mark_seen(event_url, event_title)

        # Sort by confidence score
        results.sort(key=lambda x: x.confidence_score, reverse=True)

        # Limit results
        merged.results = results[:max_results]
        merged.total_after_dedup = len(merged.results)

        logger.info(
            "Merged search results",
            raw_total=merged.total_raw_results,
            after_dedup=merged.total_after_dedup,
            sources=merged.sources_used,
        )

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
        """Get concatenated SerpAPI snippets for context."""
        snippets = []
        for r in merged.results:
            if r.snippet:
                snippets.append(f"- {r.title}: {r.snippet}" if r.title else f"- {r.snippet}")
        return "\n".join(snippets) if snippets else ""
