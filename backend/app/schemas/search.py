"""
Search request and response schemas.
Defines all search parameters (from RULES.md Search Parameters Reference).
"""
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .event import (
    EventCategory,
    EventResult,
    IndoorOutdoor,
    PriceRange,
    TimeOfDay,
)


class SearchRequest(BaseModel):
    """
    Search request schema with all parameters.
    Based on RULES.md Search Parameters Reference.
    """

    # Core parameters
    query: str = Field(..., min_length=1, max_length=500, description="Free text search")
    category: EventCategory | Literal["all"] = Field(
        default="all", description="Event category filter"
    )
    results_count: int = Field(
        default=50, ge=1, le=50, description="Number of results (max 50)"
    )

    # Location parameters
    location: str = Field(..., min_length=1, description="City, address, or coordinates")
    radius_km: int = Field(
        default=25,
        description="Search radius in kilometers",
    )
    include_online: bool = Field(default=False, description="Include online events")

    # Time parameters
    date_from: date = Field(default_factory=date.today, description="Start date")
    date_to: date | None = Field(default=None, description="End date")
    time_of_day: TimeOfDay = Field(default=TimeOfDay.ANY, description="Time of day filter")
    day_type: Literal["weekday", "weekend", "any"] = Field(
        default="any", description="Day type filter"
    )

    # Filter parameters
    price_range: PriceRange = Field(default=PriceRange.ANY, description="Price range")
    indoor_outdoor: IndoorOutdoor = Field(
        default=IndoorOutdoor.BOTH, description="Indoor/outdoor filter"
    )
    age_restriction: Literal["all_ages", "18+", "21+", "family", "any"] = Field(
        default="any", description="Age restriction filter"
    )
    accessibility: bool = Field(default=False, description="Wheelchair accessible only")
    language: str | None = Field(default=None, description="Event language filter")

    # Quality parameters
    verified_only: bool = Field(
        default=True, description="Only show events with verified source URL"
    )
    hidden_gems: bool = Field(
        default=True, description="Prioritize lesser-known events"
    )
    weather_safe: bool = Field(
        default=True, description="Block outdoor events with bad weather"
    )

    # Sort parameters
    sort_by: Literal["date", "distance", "relevance", "price"] = Field(
        default="relevance", description="Sort field"
    )
    sort_order: Literal["asc", "desc"] = Field(default="asc", description="Sort order")

    @field_validator("date_to")
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure date_to is after date_from."""
        if v is not None and "date_from" in info.data:
            if v < info.data["date_from"]:
                raise ValueError("date_to must be after date_from")
        return v

    @field_validator("radius_km")
    @classmethod
    def validate_radius(cls, v):
        """Validate radius is in allowed values."""
        allowed = [5, 10, 25, 50, 100, 200]
        if v not in allowed:
            # Round to nearest allowed value
            return min(allowed, key=lambda x: abs(x - v))
        return v


class SearchMetadata(BaseModel):
    """Metadata about the search execution."""

    query_id: str = Field(..., description="Unique query identifier")
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    execution_time_ms: float = Field(..., ge=0)
    total_results: int = Field(..., ge=0)
    sources_used: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    weather_checked: bool = False


class SearchResponse(BaseModel):
    """
    Search response schema.
    Contains results and metadata for traceability.
    """

    # Request echo (for debugging)
    request: SearchRequest

    # Results
    events: list[EventResult] = Field(default_factory=list)

    # Metadata
    metadata: SearchMetadata

    # Pagination (for future use)
    has_more: bool = False
    next_cursor: str | None = None

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "request": {
                    "query": "hiking",
                    "category": "nature",
                    "location": "Vaduz, Liechtenstein",
                    "radius_km": 50,
                    "results_count": 20,
                },
                "events": [],
                "metadata": {
                    "query_id": "qry_abc123",
                    "executed_at": "2026-01-22T10:00:00Z",
                    "execution_time_ms": 1250.5,
                    "total_results": 15,
                    "sources_used": ["perplexity", "serpapi"],
                    "cache_hit": False,
                    "weather_checked": True,
                },
                "has_more": False,
            }
        }
