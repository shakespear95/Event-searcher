"""
Search API endpoints.
Main entry point for event discovery.
"""
from fastapi import APIRouter, HTTPException

from app.agent.orchestrator import AgentOrchestrator
from app.core.logging import get_logger
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter()
logger = get_logger("api.search")

# Global orchestrator instance
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the agent orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@router.post("/search", response_model=SearchResponse)
async def search_events(request: SearchRequest):
    """
    Search for events based on query and filters.

    This endpoint:
    1. Creates a GlobalState for the request
    2. Uses Claude to generate optimized search prompts
    3. Queries Perplexity and SerpAPI in parallel
    4. Optionally scrapes for additional details
    5. Processes results with Gemini/OpenAI
    6. Checks weather for outdoor events
    7. Returns verified, traceable results
    """
    logger.info(
        "Search request received",
        query=request.query,
        category=request.category,
        location=request.location,
    )

    try:
        orchestrator = get_orchestrator()
        response = await orchestrator.search(request)
        return response

    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/categories")
async def get_categories():
    """Get all available event categories."""
    from app.schemas.event import EventCategory

    return {
        "categories": [
            {"value": cat.value, "label": cat.value.replace("_", " ").title()}
            for cat in EventCategory
        ]
    }


@router.get("/search/filters")
async def get_filter_options():
    """Get all available filter options."""
    from app.schemas.event import PriceRange, TimeOfDay, IndoorOutdoor

    return {
        "price_ranges": [{"value": p.value, "label": p.value.title()} for p in PriceRange],
        "time_of_day": [{"value": t.value, "label": t.value.title()} for t in TimeOfDay],
        "indoor_outdoor": [
            {"value": i.value, "label": i.value.title()} for i in IndoorOutdoor
        ],
        "radius_options": [5, 10, 25, 50, 100, 200],
        "age_restrictions": ["all_ages", "18+", "21+", "family"],
        "sort_options": ["date", "distance", "relevance", "price"],
    }
