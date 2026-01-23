"""
Schemas for extracting events from raw search results.
Used by Gemini to parse Perplexity responses into structured data.
"""
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ExtractedEvent(BaseModel):
    """Single event extracted from raw search results."""

    name: str = Field(..., description="Event name/title")
    description: str | None = Field(None, description="Brief event description")
    date: str | None = Field(None, description="Event date (e.g., 'January 25, 2026')")
    time: str | None = Field(None, description="Event time (e.g., '19:00' or '7 PM')")
    venue: str | None = Field(None, description="Venue name")
    address: str | None = Field(None, description="Venue address")
    city: str = Field(..., description="City name")
    country: str = Field(..., description="Country name")
    price: str | None = Field(None, description="Price info (e.g., 'Free', '$25', '€15-30')")
    category: str | None = Field(None, description="Event category")
    source_url: str = Field(..., description="URL where this event was found")
    image_url: str | None = Field(None, description="Event image URL if available")


class ExtractedEventsResponse(BaseModel):
    """Response containing multiple extracted events."""

    events: list[ExtractedEvent] = Field(default_factory=list)
    total_found: int = Field(0, description="Total events found in the content")


EXTRACTION_SYSTEM_PROMPT = """You are an event data extraction specialist. Extract events with VERIFIED DATES from search results.

CRITICAL RULES:
1. ONLY extract events that have a SPECIFIC DATE mentioned (day, month, year or at least day and month)
2. SKIP any event without a clear date - do NOT include events with unknown or unspecified dates
3. NEVER make up or guess dates - only use what's explicitly in the content
4. Every event MUST have: name, date, city, country, and source_url
5. Quality over quantity - 5 complete events is better than 15 incomplete ones

For each event with a confirmed date, extract:
- name: The event title/name (REQUIRED)
- description: Brief description (1-2 sentences max)
- date: The specific date mentioned (REQUIRED - e.g., "January 25, 2026", "25.01.2026", "Jan 25")
- time: The time if mentioned (e.g., "19:00", "7 PM")
- venue: The venue/location name (try to find this)
- address: Street address if mentioned
- city: City name (REQUIRED - use the search location if not specified)
- country: Country name (REQUIRED - use Switzerland for Swiss cities like Zurich, Bern, Basel, etc.)
- price: Price information if mentioned
- category: Type of event (concert, party, exhibition, sports, etc.)
- source_url: The URL where this event was found (REQUIRED - use one from SOURCE URLS)
- image_url: Image URL if available

SKIP these types of entries:
- Events without specific dates
- General venue descriptions without event info
- Recurring events without specific upcoming dates
- Event series without individual dates listed

Return a JSON object with:
{
  "events": [...],
  "total_found": <number>
}"""


EXTRACTION_USER_PROMPT = """Extract events WITH SPECIFIC DATES from the following search results for {location}:

--- PERPLEXITY CONTENT ---
{perplexity_content}

--- SOURCE URLS ---
{source_urls}

--- ADDITIONAL CONTEXT FROM SERPAPI ---
{serpapi_snippets}

IMPORTANT: Only extract events that have a clear, specific date mentioned.
Skip any event without a confirmed date - do not guess or make up dates.
Each event MUST have: name, date, city, country, and source_url.
Return valid JSON only."""
