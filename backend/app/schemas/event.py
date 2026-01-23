"""
Event schemas - Pydantic models for event data.
Enforces structured output (Rule A4).
"""
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class EventCategory(str, Enum):
    """Event categories for search and filtering."""

    MUSIC = "music"
    MOVIES = "movies"
    SPORTS = "sports"
    NATURE = "nature"
    FOOD_DRINKS = "food_drinks"
    ARTS_CULTURE = "arts_culture"
    NIGHTLIFE = "nightlife"
    THEATER = "theater"
    COMEDY = "comedy"
    WORKSHOPS = "workshops"
    FAMILY = "family"
    NETWORKING = "networking"
    WELLNESS = "wellness"
    MARKETS = "markets"
    FESTIVALS = "festivals"
    TECH_GAMING = "tech_gaming"
    COMMUNITY = "community"
    RELIGIOUS = "religious"


class PriceRange(str, Enum):
    """Price range filter options."""

    FREE = "free"
    BUDGET = "budget"  # < $20
    MID = "mid"  # $20-50
    PREMIUM = "premium"  # > $50
    ANY = "any"


class TimeOfDay(str, Enum):
    """Time of day filter options."""

    MORNING = "morning"  # 6am-12pm
    AFTERNOON = "afternoon"  # 12pm-5pm
    EVENING = "evening"  # 5pm-9pm
    NIGHT = "night"  # 9pm-6am
    ANY = "any"


class IndoorOutdoor(str, Enum):
    """Indoor/outdoor filter options."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    BOTH = "both"


class WeatherStatus(str, Enum):
    """Weather suitability for outdoor events."""

    GOOD = "good"  # Safe to recommend
    MODERATE = "moderate"  # Warn user
    BAD = "bad"  # Block outdoor recommendation


class DataSource(str, Enum):
    """Source of event data for traceability (Rule A3)."""

    PERPLEXITY = "perplexity"
    SERPAPI = "serpapi"
    SCRAPER = "scraper"
    MANUAL = "manual"


class EventLocation(BaseModel):
    """Event location details."""

    venue_name: str | None = None
    address: str | None = None
    city: str
    country: str
    coordinates: tuple[float, float] | None = None
    distance_km: float | None = None


class EventTiming(BaseModel):
    """Event timing details."""

    start_datetime: datetime
    end_datetime: datetime | None = None
    duration_hours: float | None = None
    timezone: str = "UTC"
    is_recurring: bool = False
    recurrence_pattern: str | None = None


class EventPricing(BaseModel):
    """Event pricing details."""

    price: float | None = None
    price_currency: str = "EUR"
    is_free: bool = False
    price_range: PriceRange = PriceRange.ANY
    booking_required: bool = False
    booking_url: HttpUrl | None = None


class WeatherInfo(BaseModel):
    """Weather information for outdoor events."""

    weather_score: float = Field(..., ge=0, le=100)
    weather_status: WeatherStatus
    temperature_celsius: float | None = None
    conditions: str | None = None
    precipitation_chance: float | None = Field(None, ge=0, le=100)


class EventSource(BaseModel):
    """
    Event source information for traceability.
    Every event MUST have a verified source URL (Rule PR1).
    """

    source_url: HttpUrl = Field(..., description="REQUIRED: Verified source URL")
    source_api: DataSource
    scraped_at: datetime | None = None
    verified: bool = True


class EventResult(BaseModel):
    """
    Complete event result schema.
    This is the output format for all events (Rule A4).
    """

    # Core identification
    event_id: str = Field(..., description="Unique event identifier")
    event_name: str = Field(..., min_length=1, max_length=500)
    description: str | None = Field(None, max_length=5000)

    # Classification
    category: EventCategory
    subcategory: str | None = None
    tags: list[str] = Field(default_factory=list)

    # Location
    location: EventLocation

    # Timing
    timing: EventTiming

    # Pricing
    pricing: EventPricing

    # Details
    indoor_outdoor: IndoorOutdoor = IndoorOutdoor.BOTH
    age_restriction: Literal["all_ages", "18+", "21+", "family"] = "all_ages"
    language: str | None = None
    accessibility: bool = False

    # Weather (for outdoor events)
    weather: WeatherInfo | None = None

    # Source & Verification (REQUIRED)
    source: EventSource

    # Media
    image_url: HttpUrl | None = None
    images: list[HttpUrl] = Field(default_factory=list)

    # Quality indicators
    is_hidden_gem: bool = False
    relevance_score: float = Field(default=0.0, ge=0, le=1)

    @field_validator("weather")
    @classmethod
    def validate_weather_for_outdoor(cls, v, info):
        """Outdoor events should have weather info when available."""
        # Weather is optional but recommended for outdoor events
        return v

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "event_id": "evt_abc123",
                "event_name": "Secret Sunset Hike",
                "description": "Discover a hidden trail with stunning views",
                "category": "nature",
                "subcategory": "hiking",
                "tags": ["outdoor", "hiking", "sunset", "secret spot"],
                "location": {
                    "venue_name": "Malbun Trailhead",
                    "city": "Vaduz",
                    "country": "Liechtenstein",
                    "coordinates": [47.1410, 9.5209],
                    "distance_km": 12.5,
                },
                "timing": {
                    "start_datetime": "2026-02-01T16:00:00Z",
                    "duration_hours": 3.0,
                    "timezone": "Europe/Zurich",
                },
                "pricing": {"is_free": True, "price_range": "free"},
                "indoor_outdoor": "outdoor",
                "source": {
                    "source_url": "https://example.com/event/123",
                    "source_api": "perplexity",
                    "verified": True,
                },
                "is_hidden_gem": True,
                "relevance_score": 0.95,
            }
        }
