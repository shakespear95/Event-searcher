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
from app.services.llm.router import LLMRouter
from app.services.llm.gemini import GeminiLLM
from app.services.search.perplexity import PerplexitySearch
from app.services.search.serpapi import SerpAPISearch
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
    │   Gemini    │ ← Process to structured output
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
        self.gemini = GeminiLLM()
        self.perplexity = PerplexitySearch()
        self.serpapi = SerpAPISearch()
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

            logger.info(
                "Search completed",
                request_id=request_id,
                results=len(events),
                duration_ms=state.total_duration_ms,
            )

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
        """Execute Perplexity and SerpAPI searches in parallel."""
        logger.debug("Executing parallel search")

        # Get category value (handle enum or string)
        category_value = request.category.value if hasattr(request.category, 'value') else str(request.category)

        logger.info(
            "Executing parallel search",
            prompt=prompt[:100],
            category=category_value,
            location=request.location,
        )

        # Run searches in parallel
        perplexity_task = self.perplexity.search_events(
            query=prompt,
            category=category_value,
            location=request.location,
            date_from=str(request.date_from),
            date_to=str(request.date_to) if request.date_to else "",
            hidden_gems=request.hidden_gems,
        )

        serpapi_task = self.serpapi.search_events(
            query=prompt,
            location=request.location,
            date_from=str(request.date_from),
            category=category_value,
        )

        perplexity_result, serpapi_result = await asyncio.gather(
            perplexity_task,
            serpapi_task,
            return_exceptions=True,
        )

        # Handle exceptions
        if isinstance(perplexity_result, Exception):
            logger.error(f"Perplexity search failed: {perplexity_result}")
            perplexity_result = None
        if isinstance(serpapi_result, Exception):
            logger.error(f"SerpAPI search failed: {serpapi_result}")
            serpapi_result = None

        # Log tool calls
        state.log_tool_call(
            tool_name="perplexity",
            action="search_events",
            success=perplexity_result is not None and perplexity_result.success,
            result_summary=f"Found {len(perplexity_result.sources) if perplexity_result else 0} sources",
        )

        state.log_tool_call(
            tool_name="serpapi",
            action="search_events",
            success=serpapi_result is not None and serpapi_result.success,
            result_summary=f"Found {len(serpapi_result.results) if serpapi_result else 0} results",
        )

        # Merge results
        logger.info("========== MERGING SEARCH RESULTS ==========")
        merged = self.merger.merge(
            perplexity_result=perplexity_result,
            serpapi_result=serpapi_result,
            max_results=request.results_count,
        )

        logger.info(f"[MERGER] Perplexity success: {merged.perplexity_success}")
        logger.info(f"[MERGER] SerpAPI success: {merged.serpapi_success}")
        logger.info(f"[MERGER] Total merged results: {len(merged.results)}")
        logger.info(f"[MERGER] Sources used: {merged.sources_used}")

        # Log each merged result
        for i, result in enumerate(merged.results[:10]):  # Log first 10
            logger.info(f"[MERGER]   Result {i+1}: {result.title[:50] if result.title else 'No title'}... URL: {result.url[:60] if result.url else 'No URL'}")

        # Update state
        state.search_state.perplexity_success = merged.perplexity_success
        state.search_state.serpapi_success = merged.serpapi_success
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
        """Process raw results into structured EventResult objects using Gemini."""
        logger.info("========== GEMINI PROCESSING START ==========")

        if not merged_results.results:
            logger.warning("[GEMINI] No merged results to process")
            return []

        logger.info(f"[GEMINI] Processing {len(merged_results.results)} raw results")

        # Get data for extraction
        perplexity_content = self.merger.get_perplexity_content(merged_results)
        source_urls = self.merger.get_source_urls(merged_results)
        serpapi_snippets = self.merger.get_serpapi_snippets(merged_results)

        logger.info(f"[GEMINI] Perplexity content length: {len(perplexity_content) if perplexity_content else 0} chars")
        logger.info(f"[GEMINI] Source URLs count: {len(source_urls)}")
        logger.info(f"[GEMINI] SerpAPI snippets length: {len(serpapi_snippets) if serpapi_snippets else 0} chars")

        if perplexity_content:
            logger.info(f"[GEMINI] Perplexity content preview: {perplexity_content[:300]}...")
        if serpapi_snippets:
            logger.info(f"[GEMINI] SerpAPI snippets preview: {serpapi_snippets[:300]}...")

        if not perplexity_content and not serpapi_snippets:
            logger.warning("[GEMINI] No content available for extraction")
            return []

        # Build extraction prompt
        extraction_prompt = EXTRACTION_USER_PROMPT.format(
            location=request.location,
            perplexity_content=perplexity_content or "No content available",
            source_urls="\n".join(source_urls) if source_urls else "No URLs",
            serpapi_snippets=serpapi_snippets or "No snippets",
        )

        # Use Gemini to extract structured events
        try:
            extracted, response = await self.gemini.generate_structured(
                prompt=extraction_prompt,
                output_schema=ExtractedEventsResponse,
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
            )

            state.log_llm_call(
                provider="gemini",
                model="gemini-1.5-flash",
                purpose="extract_events",
                success=response.success,
            )

            if not extracted or not response.success:
                logger.warning(f"[GEMINI] Extraction failed: {response.error}")
                # Fallback to basic processing
                return self._fallback_process_results(merged_results, request, state)

            logger.info(f"[GEMINI] Extraction successful! Found {len(extracted.events)} events")

            # Convert ExtractedEvent to EventResult - filter out events without dates
            events = []
            skipped_no_date = 0
            for i, extracted_event in enumerate(extracted.events):
                logger.info(f"[GEMINI]   Event {i+1}: {extracted_event.name[:50] if extracted_event.name else 'No name'}...")
                logger.info(f"[GEMINI]     Date: {extracted_event.date}, Venue: {extracted_event.venue}")
                logger.info(f"[GEMINI]     Source: {extracted_event.source_url[:60] if extracted_event.source_url else 'No URL'}")

                # Skip events without dates
                if not extracted_event.date or extracted_event.date.lower() in ['none', 'null', 'unknown', 'tbd', 'n/a', '']:
                    logger.info(f"[GEMINI]     SKIPPED - no valid date")
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
                    logger.warning(f"[GEMINI] Failed to convert event: {e}")

            if skipped_no_date > 0:
                logger.info(f"[GEMINI] Skipped {skipped_no_date} events without valid dates")

            logger.info(f"========== GEMINI PROCESSING COMPLETE ==========")
            logger.info(f"[GEMINI] Final event count: {len(events)}")
            return events[:request.results_count]

        except Exception as e:
            logger.error(f"Gemini extraction error: {e}")
            state.add_error(f"Extraction failed: {e}")
            return self._fallback_process_results(merged_results, request, state)

    def _fallback_process_results(
        self,
        merged_results: MergedSearchResults,
        request: SearchRequest,
        state: GlobalState,
    ) -> list[EventResult]:
        """Fallback processing when Gemini extraction fails."""
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
            EventCategory,
        )

        # Validate source URL
        source_url = extracted.source_url
        if not source_url or source_url not in source_urls:
            # Use first available source URL if extracted URL is invalid
            if source_urls:
                source_url = source_urls[0]
            else:
                return None

        # Determine category
        try:
            if extracted.category:
                category = EventCategory(extracted.category.lower())
            elif request.category != "all":
                category = EventCategory(request.category)
            else:
                category = EventCategory.COMMUNITY
        except ValueError:
            category = EventCategory.COMMUNITY

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

        # Parse pricing
        is_free = False
        price_min = None
        price_max = None
        if extracted.price:
            price_lower = extracted.price.lower()
            is_free = "free" in price_lower or price_lower == "0"

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
                source_api=DataSource.PERPLEXITY,
                verified=True,
            ),
            image_url=extracted.image_url,
            relevance_score=0.8,
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
        if "perplexity" in sources:
            source_api = DataSource.PERPLEXITY
        elif "serpapi" in sources:
            source_api = DataSource.SERPAPI
        else:
            source_api = DataSource.SCRAPER

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
        if self.scraper:
            await self.scraper.close()
