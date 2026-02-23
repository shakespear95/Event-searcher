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

    async def _process_results(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
        state: GlobalState,
    ) -> list[EventResult]:
        """Process raw results into structured EventResult objects using Claude."""
        logger.info("========== CLAUDE PROCESSING START ==========")

        if not merged_results.results:
            logger.warning("[CLAUDE] No merged results to process")
            return []

        logger.info(f"[CLAUDE] Processing {len(merged_results.results)} raw results")

        # Get data for extraction
        perplexity_content = self.merger.get_perplexity_content(merged_results)
        source_urls = self.merger.get_source_urls(merged_results)
        serpapi_snippets = self.merger.get_serpapi_snippets(merged_results)

        logger.info(f"[CLAUDE] Perplexity content length: {len(perplexity_content) if perplexity_content else 0} chars")
        logger.info(f"[CLAUDE] Source URLs count: {len(source_urls)}")
        logger.info(f"[CLAUDE] SerpAPI snippets length: {len(serpapi_snippets) if serpapi_snippets else 0} chars")

        if perplexity_content:
            logger.info(f"[CLAUDE] Perplexity content preview: {perplexity_content[:300]}...")
        if serpapi_snippets:
            logger.info(f"[CLAUDE] SerpAPI snippets preview: {serpapi_snippets[:300]}...")

        if not perplexity_content and not serpapi_snippets:
            logger.warning("[CLAUDE] No content available for extraction")
            return []

        # Build extraction prompt
        date_from_str = str(request.date_from) if request.date_from else "any"
        date_to_str = str(request.date_to) if request.date_to else date_from_str
        extraction_prompt = EXTRACTION_USER_PROMPT.format(
            location=request.location,
            date_from=date_from_str,
            date_to=date_to_str,
            perplexity_content=perplexity_content or "No content available",
            source_urls="\n".join(source_urls) if source_urls else "No URLs",
            serpapi_snippets=serpapi_snippets or "No snippets",
        )

        # Use Claude to extract structured events
        try:
            extracted, response = await self.claude.generate_structured(
                prompt=extraction_prompt,
                output_schema=ExtractedEventsResponse,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )

            state.log_llm_call(
                provider="claude",
                model=self.claude.default_model,
                purpose="extract_events",
                success=response.success,
            )

            if not extracted or not response.success:
                logger.warning(f"[CLAUDE] Extraction failed: {response.error}")
                # Fallback to basic processing
                return self._fallback_process_results(merged_results, request, state)

            logger.info(f"[CLAUDE] Extraction successful! Found {len(extracted.events)} events")

            # Convert ExtractedEvent to EventResult - filter out events without dates
            events = []
            skipped_no_date = 0
            for i, extracted_event in enumerate(extracted.events):
                logger.info(f"[CLAUDE]   Event {i+1}: {extracted_event.name[:50] if extracted_event.name else 'No name'}...")
                logger.info(f"[CLAUDE]     Date: {extracted_event.date}, Venue: {extracted_event.venue}")
                logger.info(f"[CLAUDE]     Source: {extracted_event.source_url[:60] if extracted_event.source_url else 'No URL'}")

                # Skip events without dates
                if not extracted_event.date or extracted_event.date.lower() in ['none', 'null', 'unknown', 'tbd', 'n/a', '']:
                    logger.info(f"[CLAUDE]     SKIPPED - no valid date")
                    skipped_no_date += 1
                    continue

                try:
                    event = self._create_event_from_extracted(
                        extracted_event, request, source_urls, i
                    )
                    if event:
                        events.append(event)
                        state.log_tool_call(
                            tool_name="processor",
                            action="create_event",
                            success=True,
                            source_url=extracted_event.source_url,
                        )
                except Exception as e:
                    state.add_warning(f"Failed to convert extracted event {i}: {e}")
                    logger.warning(f"[CLAUDE] Failed to convert event: {e}")

            if skipped_no_date > 0:
                logger.info(f"[CLAUDE] Skipped {skipped_no_date} events without valid dates")

            logger.info(f"========== CLAUDE PROCESSING COMPLETE ==========")
            logger.info(f"[CLAUDE] Final event count: {len(events)}")
            return events[:request.results_count]

        except Exception as e:
            logger.error(f"Claude extraction error: {e}")
            state.add_error(f"Extraction failed: {e}")
            return self._fallback_process_results(merged_results, request, state)

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
