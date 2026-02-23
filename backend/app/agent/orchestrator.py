"""
Agent Orchestrator.
Main workflow controller that coordinates all services.

Flow:
1. Claude creates optimized search prompts
2. Perplexity + SerpAPI search in parallel
3. Merge and deduplicate results
4. Scrape for additional details (optional)
5. Gemini processes results into structured events
6. Weather check for outdoor events
7. Return verified, traceable results
"""
import asyncio
import uuid
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.schemas.event import EventResult, DataSource, EventSource, WeatherStatus
from app.schemas.search import SearchRequest, SearchResponse, SearchMetadata
from app.schemas.state import StateManager, AgentPhase, GlobalState
from app.schemas.extraction import (
    ExtractedEventsResponse,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
)
from app.core.config import settings
from app.services.llm.router import LLMRouter
from app.services.llm.claude import ClaudeLLM
from app.services.search.perplexity import PerplexitySearch
from app.services.search.serpapi import SerpAPISearch
from app.services.search.serper import SerperSearch
from app.services.search.firecrawl import FirecrawlSearch
from app.services.search.exa import ExaSearch
from app.services.search.ticketmaster import TicketmasterSearch
from app.services.search.merger import SearchMerger, MergedSearchResults

# Optional scraper import (requires playwright which may not be installed)
try:
    from app.services.scraper.engine import ScraperEngine
    SCRAPER_AVAILABLE = True
except ImportError:
    ScraperEngine = None
    SCRAPER_AVAILABLE = False

logger = get_logger("agent.orchestrator")


class AgentOrchestrator:
    """
    Main agent orchestrator implementing the search workflow.

    Architecture:
    ┌─────────────┐
    │   Claude    │ ← Prompt Engineering
    └──────┬──────┘
           ↓
    ┌──────┴──────┐
    │  Parallel   │
    │   Search    │
    ├─────┬───────┤
    │Perp.│SerpAPI│ ← Deep Search
    └─────┴───────┘
           ↓
    ┌─────────────┐
    │   Merger    │ ← Deduplicate
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │  Scraper    │ ← Optional detail enrichment
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │   Claude    │ ← Process to structured output
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │  Weather    │ ← Check for outdoor events
    └──────┬──────┘
           ↓
    ┌─────────────┐
    │   Output    │ ← Verified events with sources
    └─────────────┘
    """

    def __init__(self):
        self.llm_router = LLMRouter()
        self.claude = ClaudeLLM()
        self.perplexity = PerplexitySearch()
        self.serpapi = SerpAPISearch()
        self.serper = SerperSearch() if settings.serper_api_key else None
        self.firecrawl = FirecrawlSearch() if settings.firecrawl_api_key else None
        self.exa = ExaSearch() if settings.exa_api_key else None
        self.ticketmaster = TicketmasterSearch() if settings.ticketmaster_api_key else None
        self.merger = SearchMerger()
        self.scraper: ScraperEngine | None = None

    async def _init_scraper(self) -> None:
        """Initialize scraper lazily."""
        if not SCRAPER_AVAILABLE:
            logger.debug("Scraper not available (playwright not installed)")
            return
        if not self.scraper:
            self.scraper = ScraperEngine()
            await self.scraper.start()

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute the full search workflow.
        """
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        state_manager = StateManager(request_id=request_id)
        state = state_manager.get_state()

        logger.info(
            "Starting search workflow",
            request_id=request_id,
            query=request.query,
            category=request.category,
            location=request.location,
        )

        try:
            # Store request in state
            state_manager.update(search_request=request)

            # Phase 1: Prompt Engineering (Claude)
            state.set_phase(AgentPhase.PROMPT_ENGINEERING)
            search_prompt = await self._create_search_prompt(request, state)

            # Phase 2: Parallel Search (Perplexity + SerpAPI)
            state.set_phase(AgentPhase.SEARCHING)
            merged_results = await self._execute_parallel_search(
                search_prompt, request, state
            )

            # Phase 3: Optional Scraping for details
            if merged_results.total_after_dedup > 0:
                state.set_phase(AgentPhase.SCRAPING)
                await self._enrich_with_scraping(merged_results, state)

            # Phase 4: Process with Gemini
            state.set_phase(AgentPhase.PROCESSING)
            events = await self._process_results(merged_results, request, state)

            # Phase 5: Weather check for outdoor events
            if request.weather_safe and request.indoor_outdoor != "indoor":
                state.set_phase(AgentPhase.WEATHER_CHECK)
                events = await self._check_weather(events, request, state)

            # Phase 6: Finalize
            state.set_phase(AgentPhase.FINALIZING)
            state_manager.update(final_events=events)
            state.finalize()

            # Build response
            metadata = SearchMetadata(
                query_id=request_id,
                executed_at=datetime.utcnow(),
                execution_time_ms=state.total_duration_ms or 0,
                total_results=len(events),
                sources_used=merged_results.sources_used,
                cache_hit=False,
                weather_checked=state.weather_state.checked,
            )

            # === PIPELINE SUMMARY ===
            logger.info("=" * 60)
            logger.info("SEARCH PIPELINE SUMMARY")
            logger.info("=" * 60)
            logger.info(f"  Request ID:         {request_id}")
            logger.info(f"  Query:              {request.query}")
            logger.info(f"  Location:           {request.location}")
            logger.info(f"  Category:           {request.category}")
            logger.info(f"  Date range:         {request.date_from} -> {request.date_to}")
            logger.info(f"  Requested count:    {request.results_count}")
            logger.info(f"  ---")
            logger.info(f"  Sources used:       {merged_results.sources_used}")
            logger.info(f"  Raw results:        {merged_results.total_raw_results}")
            logger.info(f"  After dedup:        {merged_results.total_after_dedup}")
            logger.info(f"  After processing:   {len(events)}")
            logger.info(f"  Final returned:     {len(events)}")
            logger.info(f"  Duration:           {state.total_duration_ms}ms")
            if merged_results.total_raw_results > 0 and len(events) < merged_results.total_raw_results:
                drop_pct = round((1 - len(events) / merged_results.total_raw_results) * 100, 1)
                logger.info(f"  DROP RATE:          {drop_pct}% of raw results lost in pipeline")
            logger.info("=" * 60)

            return SearchResponse(
                request=request,
                events=events,
                metadata=metadata,
                has_more=False,
            )

        except Exception as e:
            state.add_error(str(e))
            state.set_phase(AgentPhase.ERROR)
            logger.error(
                "Search workflow failed",
                request_id=request_id,
                error=str(e),
            )
            raise

    async def _create_search_prompt(
        self, request: SearchRequest, state: GlobalState
    ) -> str:
        """Use Claude to create optimized search prompt."""
        logger.debug("Creating search prompt with Claude")

        date_range = f"{request.date_from}"
        if request.date_to:
            date_range += f" to {request.date_to}"

        # Get category value (handle enum or string)
        category_value = request.category.value if hasattr(request.category, 'value') else str(request.category)

        prompt = await self.llm_router.generate_prompt(
            query=request.query,
            category=category_value,
            location=request.location,
            date_range=date_range,
            additional_context=f"Radius: {request.radius_km}km, Hidden gems: {request.hidden_gems}",
        )

        state.log_tool_call(
            tool_name="claude",
            action="create_search_prompt",
            params={"query": request.query},
            success=True,
            result_summary=f"Generated prompt: {prompt[:100]}...",
        )

        state_manager = StateManager(request_id=state.request_id)
        state_manager.update(search_prompt_perplexity=prompt)

        return prompt

    async def _execute_parallel_search(
        self, prompt: str, request: SearchRequest, state: GlobalState
    ):
        """Execute all search providers in parallel."""
        logger.debug("Executing parallel search across all providers")

        # Get category value (handle enum or string)
        category_value = request.category.value if hasattr(request.category, 'value') else str(request.category)

        logger.info(
            "Executing parallel search",
            prompt=prompt[:100],
            category=category_value,
            location=request.location,
        )

        date_from_str = str(request.date_from)
        date_to_str = str(request.date_to) if request.date_to else ""

        # Build tasks dict -- only include providers that are available
        tasks: dict[str, Any] = {}

        tasks["perplexity"] = self.perplexity.search_events(
            query=prompt,
            category=category_value,
            location=request.location,
            date_from=date_from_str,
            date_to=date_to_str,
            hidden_gems=request.hidden_gems,
        )

        tasks["serpapi"] = self.serpapi.search_events(
            query=prompt,
            location=request.location,
            date_from=date_from_str,
            category=category_value,
        )

        if self.serper:
            tasks["serper"] = self.serper.search_events(
                query=prompt,
                location=request.location,
                date_from=date_from_str,
                category=category_value,
            )

        if self.firecrawl:
            tasks["firecrawl"] = self.firecrawl.search_events(
                query=prompt,
                location=request.location,
                date_from=date_from_str,
                category=category_value,
            )

        if self.exa:
            tasks["exa"] = self.exa.search_events(
                query=prompt,
                location=request.location,
                date_from=date_from_str,
                category=category_value,
            )

        if self.ticketmaster:
            tasks["ticketmaster"] = self.ticketmaster.search_events(
                query=prompt,
                location=request.location,
                date_from=date_from_str,
                date_to=date_to_str if date_to_str else None,
                category=category_value,
            )

        # Run ALL available searches in parallel
        task_names = list(tasks.keys())
        task_coros = list(tasks.values())

        logger.info(f"Running {len(task_names)} search providers in parallel: {task_names}")
        raw_results = await asyncio.gather(*task_coros, return_exceptions=True)

        # Map back to named results, handling exceptions
        providers: dict[str, Any] = {}
        for name, result in zip(task_names, raw_results):
            if isinstance(result, Exception):
                logger.error(f"{name} search failed: {result}")
                providers[name] = None
            else:
                providers[name] = result

        # === DIAGNOSTIC: Per-provider result counts ===
        logger.info("=" * 60)
        logger.info("PROVIDER RESULTS SUMMARY")
        logger.info("=" * 60)

        for name, result in providers.items():
            if result is None:
                logger.info(f"  [{name.upper()}] FAILED (returned None / exception)")
                continue

            success = hasattr(result, 'success') and result.success

            if name == "perplexity":
                src_count = len(result.sources) if hasattr(result, 'sources') else 0
                content_len = len(result.content) if hasattr(result, 'content') and result.content else 0
                logger.info(f"  [PERPLEXITY] success={success} | sources={src_count} | content_length={content_len} chars")
            elif name == "serpapi":
                organic = len(result.results) if hasattr(result, 'results') else 0
                events = len(result.events) if hasattr(result, 'events') else 0
                logger.info(f"  [SERPAPI] success={success} | organic_results={organic} | google_events={events}")
            elif name == "serper":
                count = len(result.results) if hasattr(result, 'results') else 0
                logger.info(f"  [SERPER] success={success} | results={count}")
            elif name == "firecrawl":
                count = len(result.results) if hasattr(result, 'results') else 0
                logger.info(f"  [FIRECRAWL] success={success} | results={count}")
            elif name == "exa":
                count = len(result.results) if hasattr(result, 'results') else 0
                logger.info(f"  [EXA] success={success} | results={count}")
            elif name == "ticketmaster":
                count = len(result.events) if hasattr(result, 'events') else 0
                logger.info(f"  [TICKETMASTER] success={success} | events={count}")
            else:
                logger.info(f"  [{name.upper()}] success={success}")

        logger.info("=" * 60)

        # Log tool calls for all providers
        for name, result in providers.items():
            success = result is not None and hasattr(result, 'success') and result.success
            state.log_tool_call(
                tool_name=name,
                action="search_events",
                success=success,
                result_summary=f"Success: {success}",
            )

        # Merge all results
        logger.info("========== MERGING SEARCH RESULTS ==========")
        merged = self.merger.merge(
            perplexity_result=providers.get("perplexity"),
            serpapi_result=providers.get("serpapi"),
            serper_result=providers.get("serper"),
            firecrawl_result=providers.get("firecrawl"),
            exa_result=providers.get("exa"),
            ticketmaster_result=providers.get("ticketmaster"),
            max_results=request.results_count,
        )

        logger.info(f"[MERGER] Sources used: {merged.sources_used}")
        logger.info(f"[MERGER] Total merged results: {len(merged.results)}")
        logger.info(f"[MERGER] Raw total: {merged.total_raw_results}, After dedup: {merged.total_after_dedup}")

        # Log first 10 merged results
        for i, result in enumerate(merged.results[:10]):
            logger.info(f"[MERGER]   Result {i+1}: {result.title[:50] if result.title else 'No title'}... URL: {result.url[:60] if result.url else 'No URL'}")

        # Update state
        state.search_state.perplexity_success = merged.perplexity_success
        state.search_state.serpapi_success = merged.serpapi_success
        state.search_state.serper_success = merged.serper_success
        state.search_state.firecrawl_success = merged.firecrawl_success
        state.search_state.exa_success = merged.exa_success
        state.search_state.ticketmaster_success = merged.ticketmaster_success
        state.search_state.merged_results = self.merger.to_raw_list(merged)

        return merged

    async def _enrich_with_scraping(
        self, merged_results: MergedSearchResults, state: GlobalState
    ) -> None:
        """Optionally scrape URLs for additional event details."""
        if not SCRAPER_AVAILABLE:
            logger.debug("Scraping skipped (playwright not installed)")
            return

        # Only scrape URLs that need enrichment (missing title or details)
        urls_to_scrape = [
            r.url
            for r in merged_results.results
            if not r.title or not r.serpapi_data
        ][:5]  # Limit scraping to 5 URLs to avoid rate limits

        if not urls_to_scrape:
            logger.debug("No URLs need scraping")
            return

        try:
            await self._init_scraper()
            scraped_pages = await self.scraper.scrape_multiple(urls_to_scrape)

            # Enrich results with scraped data
            for page in scraped_pages:
                if page.success:
                    event_data = await self.scraper.extract_event_data(page)
                    if event_data:
                        # Find and update matching result
                        for result in merged_results.results:
                            if result.url == page.url:
                                result.title = result.title or event_data.get("name", "")
                                result.snippet = result.snippet or event_data.get("description", "")
                                break

            state.log_tool_call(
                tool_name="scraper",
                action="enrich_results",
                success=True,
                result_summary=f"Scraped {len(urls_to_scrape)} URLs",
            )

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            state.log_tool_call(
                tool_name="scraper",
                action="enrich_results",
                success=False,
                error=str(e),
            )

    def _convert_structured_events(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
    ) -> list[EventResult]:
        """Directly convert structured events (Ticketmaster, Google Events) to EventResult.
        These have full data and don't need Claude extraction."""
        from app.schemas.event import EventLocation, EventTiming, EventPricing

        direct_events: list[EventResult] = []

        for result in merged_results.results:
            # Only process results that have structured serpapi_data with a date
            if not result.serpapi_data or not isinstance(result.serpapi_data, dict):
                continue

            data = result.serpapi_data
            has_date = data.get("date") or data.get("localDate")
            is_structured = "ticketmaster" in result.sources or "serpapi_events" in result.sources

            if not (is_structured and has_date):
                continue

            # Parse date
            date_str = data.get("date") or data.get("localDate", "")
            time_str = data.get("time") or data.get("localTime", "")
            try:
                from dateutil import parser as dateparser
                parsed_dt = dateparser.parse(date_str, fuzzy=True)
                if time_str:
                    try:
                        parsed_time = dateparser.parse(time_str, fuzzy=True)
                        parsed_dt = datetime.combine(parsed_dt.date(), parsed_time.time())
                    except Exception:
                        pass
            except Exception:
                parsed_dt = datetime.combine(request.date_from, datetime.min.time())

            # Date range filter
            event_date = parsed_dt.date() if isinstance(parsed_dt, datetime) else parsed_dt
            if request.date_from and event_date < request.date_from:
                continue
            if request.date_to and event_date > request.date_to:
                continue

            # Category
            category = self._map_category(data.get("category"), request.category)

            # Pricing
            is_free = False
            price_min = data.get("price_min")
            price_max = data.get("price_max")
            price_info = None
            if price_min is not None:
                price_info = f"${price_min}"
                if price_max and price_max != price_min:
                    price_info += f" - ${price_max}"

            # Source API
            source_api = self._detect_source_api(result.url)

            event = EventResult(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_name=result.title or data.get("title", f"Event"),
                description=data.get("description") or result.snippet or None,
                category=category,
                location=EventLocation(
                    venue_name=data.get("venue_name"),
                    address=data.get("venue_address"),
                    city=data.get("venue_city") or request.location.split(",")[0].strip(),
                    country=data.get("venue_country") or (request.location.split(",")[-1].strip() if "," in request.location else "Unknown"),
                ),
                timing=EventTiming(start_datetime=parsed_dt),
                pricing=EventPricing(
                    is_free=is_free,
                    price_min=price_min,
                    price_max=price_max,
                    price_info=price_info,
                ),
                source=EventSource(
                    source_url=result.url,
                    source_api=source_api,
                    verified=True,
                ),
                image_url=data.get("image_url"),
                relevance_score=result.confidence_score,
                is_hidden_gem=request.hidden_gems,
            )
            direct_events.append(event)
            logger.info(f"[DIRECT] Converted: {event.event_name[:50]}... date={date_str} source={result.sources}")

        logger.info(f"[DIRECT] Total structured events converted directly: {len(direct_events)}")
        return direct_events

    def _convert_all_merged_results(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
    ) -> list[EventResult]:
        """Convert ALL merged results directly to EventResult objects.
        Uses whatever data is available — title, snippet, serpapi_data.
        No filtering — every result becomes an event."""
        from app.schemas.event import EventLocation, EventTiming, EventPricing

        events: list[EventResult] = []
        city = request.location.split(",")[0].strip()
        country = request.location.split(",")[-1].strip() if "," in request.location else "Unknown"

        for i, result in enumerate(merged_results.results):
            data = result.serpapi_data if isinstance(result.serpapi_data, dict) else {}

            # --- Parse date ---
            date_str = data.get("date") or data.get("localDate") or ""
            time_str = data.get("time") or data.get("localTime") or ""
            parsed_dt = None

            # Try from structured data first
            if date_str:
                try:
                    from dateutil import parser as dateparser
                    parsed_dt = dateparser.parse(date_str, fuzzy=True)
                    if time_str:
                        try:
                            parsed_time = dateparser.parse(time_str, fuzzy=True)
                            parsed_dt = datetime.combine(parsed_dt.date(), parsed_time.time())
                        except Exception:
                            pass
                except Exception:
                    pass

            # Try parsing date from snippet
            if not parsed_dt and result.snippet:
                try:
                    from dateutil import parser as dateparser
                    # Look for date patterns in snippet
                    import re
                    date_patterns = re.findall(
                        r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{4}\b',
                        result.snippet,
                        re.IGNORECASE,
                    )
                    if date_patterns:
                        parsed_dt = dateparser.parse(date_patterns[0], fuzzy=True)
                except Exception:
                    pass

            # Try parsing date from title
            if not parsed_dt and result.title:
                try:
                    from dateutil import parser as dateparser
                    import re
                    date_patterns = re.findall(
                        r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{4}\b',
                        result.title,
                        re.IGNORECASE,
                    )
                    if date_patterns:
                        parsed_dt = dateparser.parse(date_patterns[0], fuzzy=True)
                except Exception:
                    pass

            # Default to request date if nothing found
            if not parsed_dt:
                parsed_dt = datetime.combine(request.date_from, datetime.min.time())

            # --- Parse venue ---
            venue_name = data.get("venue_name") or None
            # Try to extract venue from snippet if not in structured data
            if not venue_name and result.snippet:
                import re
                venue_match = re.search(r'Venue:\s*([^|,\n]+)', result.snippet)
                if venue_match:
                    venue_name = venue_match.group(1).strip()

            # --- Category ---
            category = self._map_category(data.get("category"), request.category)

            # --- Pricing ---
            is_free = False
            price_min = data.get("price_min")
            price_max = data.get("price_max")
            price_info = None
            if price_min is not None:
                price_info = f"${price_min}"
                if price_max and price_max != price_min:
                    price_info += f" - ${price_max}"
            elif result.snippet:
                import re
                price_match = re.search(r'Price:\s*([^|,\n]+)', result.snippet)
                if price_match:
                    price_info = price_match.group(1).strip()
                    is_free = "free" in price_info.lower()

            # --- Source ---
            source_api = self._detect_source_api(result.url)

            # --- Event name ---
            event_name = result.title or data.get("title") or f"Event in {city}"

            event = EventResult(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_name=event_name,
                description=data.get("description") or result.snippet or None,
                category=category,
                location=EventLocation(
                    venue_name=venue_name,
                    address=data.get("venue_address"),
                    city=data.get("venue_city") or city,
                    country=data.get("venue_country") or country,
                ),
                timing=EventTiming(start_datetime=parsed_dt),
                pricing=EventPricing(
                    is_free=is_free,
                    price_min=price_min,
                    price_max=price_max,
                    price_info=price_info,
                ),
                source=EventSource(
                    source_url=result.url,
                    source_api=source_api,
                    verified=True,
                ),
                image_url=data.get("image_url"),
                relevance_score=result.confidence_score,
                is_hidden_gem=request.hidden_gems,
            )
            events.append(event)

        logger.info(f"[DIRECT] Converted ALL {len(events)} merged results to events")
        return events

    async def _process_results(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
        state: GlobalState,
    ) -> list[EventResult]:
        """Process merged results:
        1. Convert all to basic EventResult (no drop)
        2. Use Perplexity to deep-research and enrich with date/venue/price
        3. Return up to 30 enriched results"""
        from app.schemas.event import EventLocation, EventTiming, EventPricing

        logger.info("========== PROCESSING START ==========")

        if not merged_results.results:
            logger.warning("No merged results to process")
            return []

        # Cap at 30 results for enrichment
        max_to_process = min(30, request.results_count, len(merged_results.results))
        results_to_process = merged_results.results[:max_to_process]
        logger.info(f"[PROCESSING] Processing top {len(results_to_process)} merged results")

        # Step 1: Convert all to basic EventResult
        all_events = self._convert_all_merged_results(
            MergedSearchResults(
                results=results_to_process,
                sources_used=merged_results.sources_used,
                total_raw_results=merged_results.total_raw_results,
                total_after_dedup=len(results_to_process),
            ),
            request,
        )

        # Step 2: Identify events needing enrichment (missing date or venue)
        events_needing_enrichment = []
        events_complete = []
        for event in all_events:
            has_real_date = True
            # Check if date is just the default (request.date_from)
            if event.timing.start_datetime:
                event_date = event.timing.start_datetime
                if isinstance(event_date, datetime):
                    event_date = event_date.date()
                if event_date == request.date_from and event_date == event.timing.start_datetime.date() if isinstance(event.timing.start_datetime, datetime) else True:
                    # Could be default — check if we actually parsed a date
                    has_real_date = bool(event.location.venue_name)  # proxy: if no venue either, likely no data

            if not has_real_date or not event.location.venue_name:
                events_needing_enrichment.append(event)
            else:
                events_complete.append(event)

        logger.info(f"[PROCESSING] Complete events: {len(events_complete)}, Need enrichment: {len(events_needing_enrichment)}")

        # Step 3: Use Perplexity to deep-research events missing data
        if events_needing_enrichment:
            date_range = f"{request.date_from} to {request.date_to}" if request.date_to else str(request.date_from)

            # Batch enrichment — 15 per Perplexity call max
            batch_size = 15
            for batch_start in range(0, len(events_needing_enrichment), batch_size):
                batch = events_needing_enrichment[batch_start:batch_start + batch_size]
                batch_data = [
                    {
                        "url": e.source.source_url,
                        "title": e.event_name,
                        "snippet": e.description or "",
                    }
                    for e in batch
                ]

                logger.info(f"[PERPLEXITY ENRICH] Sending batch of {len(batch)} events for deep research")
                try:
                    enriched_list = await self.perplexity.enrich_events(
                        events_data=batch_data,
                        location=request.location,
                        date_range=date_range,
                    )

                    # Match enriched data back to events by URL
                    url_to_enriched = {}
                    for enriched in enriched_list:
                        src_url = enriched.get("source_url", "")
                        if src_url:
                            url_to_enriched[src_url] = enriched

                    enriched_count = 0
                    for event in batch:
                        enriched = url_to_enriched.get(event.source.source_url)
                        if not enriched:
                            # Try partial URL match
                            for url_key, enr_data in url_to_enriched.items():
                                if url_key in event.source.source_url or event.source.source_url in url_key:
                                    enriched = enr_data
                                    break

                        if enriched:
                            enriched_count += 1
                            # Update event name
                            if enriched.get("name") and event.event_name.startswith("Event in "):
                                event.event_name = enriched["name"]

                            # Update date
                            if enriched.get("date"):
                                try:
                                    from dateutil import parser as dateparser
                                    parsed = dateparser.parse(enriched["date"], fuzzy=True)
                                    if enriched.get("time"):
                                        try:
                                            parsed_time = dateparser.parse(enriched["time"], fuzzy=True)
                                            parsed = datetime.combine(parsed.date(), parsed_time.time())
                                        except Exception:
                                            pass
                                    event.timing = EventTiming(start_datetime=parsed)
                                except Exception:
                                    pass

                            # Update venue
                            if enriched.get("venue"):
                                event.location.venue_name = enriched["venue"]
                            if enriched.get("address"):
                                event.location.address = enriched["address"]

                            # Update price
                            if enriched.get("price"):
                                price_str = enriched["price"]
                                event.pricing.price_info = price_str
                                event.pricing.is_free = "free" in price_str.lower()

                            # Update description
                            if enriched.get("description") and not event.description:
                                event.description = enriched["description"]

                            logger.info(f"[ENRICH] Updated: {event.event_name[:40]}... date={enriched.get('date', '?')} venue={enriched.get('venue', '?')}")

                    logger.info(f"[PERPLEXITY ENRICH] Batch result: {enriched_count}/{len(batch)} events enriched")

                    state.log_tool_call(
                        tool_name="perplexity",
                        action="enrich_events",
                        success=True,
                        result_summary=f"Enriched {enriched_count}/{len(batch)} events",
                    )

                except Exception as e:
                    logger.error(f"[PERPLEXITY ENRICH] Batch failed (non-fatal): {e}")
                    state.log_tool_call(
                        tool_name="perplexity",
                        action="enrich_events",
                        success=False,
                        error=str(e),
                    )

        # Combine complete + enriched events
        final_events = events_complete + events_needing_enrichment

        logger.info(f"========== PROCESSING COMPLETE ==========")
        logger.info(f"[PROCESSING] Final event count: {len(final_events)}")
        return final_events[:request.results_count]

    def _parse_events_from_perplexity(self, content: str) -> list[dict[str, str]]:
        """Extract structured event data from Perplexity markdown content."""
        import re
        events = []
        current: dict[str, str] = {}

        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Match "**Event name/title**: ..." or "- **Event name/title**: ..."
            name_match = re.match(r'^-?\s*\*\*(?:Event\s+)?name(?:/title)?\*\*:\s*(.+)', line, re.IGNORECASE)
            if name_match:
                if current.get("name"):
                    events.append(current)
                current = {"name": name_match.group(1).strip()}
                continue

            date_match = re.match(r'^-?\s*\*\*(?:Specific\s+)?date\*\*:\s*(.+)', line, re.IGNORECASE)
            if date_match and current:
                current["date"] = date_match.group(1).strip()
                continue

            time_match = re.match(r'^-?\s*\*\*Time\*\*:\s*(.+)', line, re.IGNORECASE)
            if time_match and current:
                current["time"] = time_match.group(1).strip()
                continue

            venue_match = re.match(r'^-?\s*\*\*Venue(?:\s+name)?(?:\s+and\s+location)?\*\*:\s*(.+)', line, re.IGNORECASE)
            if venue_match and current:
                current["venue"] = venue_match.group(1).strip()
                continue

            desc_match = re.match(r'^-?\s*\*\*(?:Brief\s+)?description\*\*:\s*(.+)', line, re.IGNORECASE)
            if desc_match and current:
                current["description"] = desc_match.group(1).strip()
                continue

            source_match = re.match(r'^-?\s*\*\*Source(?:\s+URL)?(?:\s+or\s+ticket\s+link)?\*\*:\s*(.+)', line, re.IGNORECASE)
            if source_match and current:
                current["source_url"] = source_match.group(1).strip()
                continue

        if current.get("name"):
            events.append(current)

        return events

    def _fallback_process_results(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
        state: GlobalState,
    ) -> list[EventResult]:
        """Fallback processing when Gemini extraction fails."""
        # First, try to parse structured events from Perplexity content
        perplexity_content = self.merger.get_perplexity_content(merged_results)
        parsed_events = self._parse_events_from_perplexity(perplexity_content) if perplexity_content else []

        if parsed_events:
            logger.info(f"[FALLBACK] Parsed {len(parsed_events)} events from Perplexity content")
            events = []
            for i, parsed in enumerate(parsed_events):
                try:
                    event = self._create_event_from_parsed(parsed, request, i)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Fallback parsed event {i} failed: {e}")
            if events:
                return events[:request.results_count]

        # Fall back to raw results
        raw_list = self.merger.to_raw_list(merged_results)
        events = []

        for i, raw in enumerate(raw_list):
            try:
                if not raw.get("url"):
                    continue
                event = self._create_event_from_raw(raw, request, i)
                if event:
                    events.append(event)
            except Exception as e:
                logger.warning(f"Fallback processing failed for result {i}: {e}")

        return events[:request.results_count]

    def _map_category(self, raw_category: str | None, request_category: str) -> "EventCategory":
        """Map an extracted category string to the EventCategory enum."""
        from app.schemas.event import EventCategory

        if not raw_category:
            if request_category and request_category != "all":
                try:
                    return EventCategory(request_category)
                except ValueError:
                    pass
            return EventCategory.COMMUNITY

        cat = raw_category.lower().strip()

        # Direct enum match
        try:
            return EventCategory(cat)
        except ValueError:
            pass

        # Keyword-based mapping
        keyword_map = {
            EventCategory.MUSIC: ["music", "concert", "jazz", "rock", "pop", "classical", "opera", "dj", "band", "orchestra", "piano", "live music", "hip-hop", "electronic"],
            EventCategory.THEATER: ["theater", "theatre", "play", "drama", "musical", "ballet", "dance", "performance", "show"],
            EventCategory.ARTS_CULTURE: ["art", "exhibition", "gallery", "museum", "culture", "painting", "sculpture", "photography"],
            EventCategory.SPORTS: ["sport", "football", "soccer", "basketball", "tennis", "hockey", "match", "game", "race", "marathon", "fitness"],
            EventCategory.FOOD_DRINKS: ["food", "drink", "wine", "beer", "tasting", "culinary", "cooking", "restaurant", "dining", "brunch"],
            EventCategory.NIGHTLIFE: ["nightlife", "club", "party", "rave", "bar", "lounge", "nightclub"],
            EventCategory.COMEDY: ["comedy", "standup", "stand-up", "improv", "humor"],
            EventCategory.WORKSHOPS: ["workshop", "class", "seminar", "course", "lecture", "talk", "training", "tutorial"],
            EventCategory.FAMILY: ["family", "kids", "children", "child"],
            EventCategory.FESTIVALS: ["festival", "carnival", "fair", "fête", "fete"],
            EventCategory.MARKETS: ["market", "flea", "bazaar", "craft"],
            EventCategory.NETWORKING: ["networking", "meetup", "conference", "business", "startup"],
            EventCategory.WELLNESS: ["wellness", "yoga", "meditation", "spa", "health", "mindfulness"],
            EventCategory.NATURE: ["nature", "outdoor", "hiking", "garden", "park"],
            EventCategory.TECH_GAMING: ["tech", "gaming", "hackathon", "esports", "code"],
        }

        for enum_val, keywords in keyword_map.items():
            for kw in keywords:
                if kw in cat:
                    return enum_val

        # Fall back to request category
        if request_category and request_category != "all":
            try:
                return EventCategory(request_category)
            except ValueError:
                pass

        return EventCategory.COMMUNITY

    def _detect_source_api(self, source_url: str) -> DataSource:
        """Detect which API a source URL likely came from."""
        if not source_url:
            return DataSource.PERPLEXITY

        url_lower = source_url.lower()
        if "ticketmaster.com" in url_lower or "livenation.com" in url_lower:
            return DataSource.TICKETMASTER
        # Default to perplexity since it's the primary content source
        return DataSource.PERPLEXITY

    def _create_event_from_extracted(
        self,
        extracted,
        request: SearchRequest,
        source_urls: list[str],
        index: int,
    ) -> EventResult | None:
        """Create EventResult from ExtractedEvent."""
        from app.schemas.event import (
            EventLocation,
            EventTiming,
            EventPricing,
        )

        # Validate source URL
        source_url = extracted.source_url
        if not source_url or source_url not in source_urls:
            # Use first available source URL if extracted URL is invalid
            if source_urls:
                source_url = source_urls[0]
            else:
                return None

        # Determine category using keyword mapping
        category = self._map_category(extracted.category, request.category)

        # Parse timing
        start_datetime = datetime.combine(request.date_from, datetime.min.time())
        if extracted.date:
            try:
                # Try to parse the date string
                from dateutil import parser
                parsed_date = parser.parse(extracted.date, fuzzy=True)
                if extracted.time:
                    try:
                        parsed_time = parser.parse(extracted.time, fuzzy=True)
                        start_datetime = datetime.combine(
                            parsed_date.date(), parsed_time.time()
                        )
                    except Exception:
                        start_datetime = parsed_date
                else:
                    start_datetime = parsed_date
            except Exception:
                pass  # Keep default date

        # --- Date range filter: skip events outside the requested range ---
        event_date = start_datetime.date() if isinstance(start_datetime, datetime) else start_datetime
        if request.date_from and event_date < request.date_from:
            logger.info(f"[DATE-FILTER] Skipping '{extracted.name}' - date {event_date} before {request.date_from}")
            return None
        if request.date_to and event_date > request.date_to:
            logger.info(f"[DATE-FILTER] Skipping '{extracted.name}' - date {event_date} after {request.date_to}")
            return None

        # Parse pricing
        is_free = False
        price_min = None
        price_max = None
        if extracted.price:
            price_lower = extracted.price.lower()
            is_free = "free" in price_lower or price_lower == "0"

        # Detect source API from URL
        source_api = self._detect_source_api(source_url)

        return EventResult(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_name=extracted.name,
            description=extracted.description,
            category=category,
            location=EventLocation(
                venue_name=extracted.venue,
                address=extracted.address,
                city=extracted.city,
                country=extracted.country,
            ),
            timing=EventTiming(
                start_datetime=start_datetime,
            ),
            pricing=EventPricing(
                is_free=is_free,
                price_min=price_min,
                price_max=price_max,
                price_info=extracted.price,
            ),
            source=EventSource(
                source_url=source_url,
                source_api=source_api,
                verified=True,
            ),
            image_url=extracted.image_url,
            relevance_score=0.8,
            is_hidden_gem=request.hidden_gems,
        )

    def _create_event_from_parsed(
        self, parsed: dict[str, str], request: SearchRequest, index: int
    ) -> EventResult | None:
        """Create EventResult from Perplexity-parsed event data."""
        from app.schemas.event import (
            EventLocation,
            EventTiming,
            EventPricing,
            EventCategory,
        )

        name = parsed.get("name", "").strip()
        if not name:
            return None

        # Parse date
        event_date = None
        date_str = parsed.get("date", "")
        if date_str:
            import re
            from dateutil import parser as dateparser
            try:
                # Remove qualifiers like "Not specified"
                if date_str.lower() not in ['not specified', 'n/a', 'tbd', 'unknown', 'none']:
                    event_date = dateparser.parse(date_str, fuzzy=True)
            except (ValueError, TypeError):
                pass

        if not event_date:
            event_date = datetime.combine(request.date_from, datetime.min.time()) if request.date_from else datetime.now()

        # Parse venue
        venue = parsed.get("venue", "")
        city = request.location.split(",")[0].strip()

        # Determine category
        try:
            category = (
                EventCategory(request.category)
                if request.category != "all"
                else EventCategory.COMMUNITY
            )
        except ValueError:
            category = EventCategory.COMMUNITY

        source_url = parsed.get("source_url", "")
        # Clean markdown links from source_url
        if source_url.startswith("["):
            import re
            link_match = re.search(r'\((https?://[^\)]+)\)', source_url)
            if link_match:
                source_url = link_match.group(1)

        return EventResult(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_name=name,
            description=parsed.get("description", ""),
            category=category,
            location=EventLocation(
                city=city,
                country=request.location.split(",")[-1].strip() if "," in request.location else "Unknown",
                venue_name=venue if venue else None,
            ),
            timing=EventTiming(
                start_datetime=event_date,
            ),
            pricing=EventPricing(
                is_free=request.price_range == "free",
            ),
            source=EventSource(
                source_url=source_url or f"https://www.google.com/search?q={name.replace(' ', '+')}",
                source_api=DataSource.PERPLEXITY,
                verified=True,
            ),
            relevance_score=0.7,
            is_hidden_gem=request.hidden_gems,
        )

    def _create_event_from_raw(
        self, raw: dict[str, Any], request: SearchRequest, index: int
    ) -> EventResult | None:
        """Create EventResult from raw search result."""
        from app.schemas.event import (
            EventLocation,
            EventTiming,
            EventPricing,
            EventCategory,
        )

        url = raw.get("url", "")
        if not url:
            return None

        # Determine category
        try:
            category = (
                EventCategory(request.category)
                if request.category != "all"
                else EventCategory.COMMUNITY
            )
        except ValueError:
            category = EventCategory.COMMUNITY

        # Determine source
        sources = raw.get("sources", [])
        source_api = DataSource.SCRAPER  # default
        source_str = " ".join(sources)
        for name in ["ticketmaster", "perplexity", "serpapi", "serper", "firecrawl", "exa"]:
            if name in source_str:
                source_api = DataSource(name)
                break

        return EventResult(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_name=raw.get("title") or f"Event {index + 1}",
            description=raw.get("snippet"),
            category=category,
            location=EventLocation(
                city=request.location.split(",")[0].strip(),
                country=request.location.split(",")[-1].strip() if "," in request.location else "Unknown",
            ),
            timing=EventTiming(
                start_datetime=datetime.combine(request.date_from, datetime.min.time()),
            ),
            pricing=EventPricing(
                is_free=request.price_range == "free",
            ),
            source=EventSource(
                source_url=url,
                source_api=source_api,
                verified=True,
            ),
            relevance_score=raw.get("confidence", 0.5),
            is_hidden_gem=request.hidden_gems,
        )

    async def _check_weather(
        self,
        events: list[EventResult],
        request: SearchRequest,
        state: GlobalState,
    ) -> list[EventResult]:
        """Check weather and filter/warn for outdoor events."""
        # TODO: Implement actual weather API check
        # For now, mark all as weather-safe

        state.weather_state.checked = True
        state.weather_state.location = request.location
        state.weather_state.outdoor_safe = True

        logger.debug(f"Weather check completed for {len(events)} events")

        return events

    async def close(self) -> None:
        """Clean up resources."""
        await self.perplexity.close()
        await self.serpapi.close()
        if self.serper:
            await self.serper.close()
        if self.firecrawl:
            await self.firecrawl.close()
        if self.exa:
            await self.exa.close()
        if self.ticketmaster:
            await self.ticketmaster.close()
        if self.scraper:
            await self.scraper.close()
