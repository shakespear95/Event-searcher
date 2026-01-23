"""
Search Result Merger.
Combines and deduplicates results from Perplexity and SerpAPI.
"""
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

        # Process Perplexity sources first
        if perplexity_result and perplexity_result.success:
            for source_url in perplexity_result.sources:
                if not self._is_duplicate(source_url, ""):
                    result = MergedResult(
                        title="",  # Will be enriched from SerpAPI or scraping
                        url=source_url,
                        snippet="",
                        sources=["perplexity"],
                        perplexity_content=perplexity_result.content,
                        confidence_score=0.7,
                    )
                    results.append(result)
                    self._mark_seen(source_url, "")

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
