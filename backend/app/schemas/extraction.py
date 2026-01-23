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


EXTRACTION_SYSTEM_PROMPT = """You are an event data extraction specialist. Extract ALL events from search results.

CRITICAL RULES:
1. Extract EVERY distinct event mentioned - aim for 10-20 events if the content contains them
2. NEVER make up or guess event details - only use what's in the content
3. If a field is not clearly stated, use null
4. Every event MUST have a source_url - use any URL from the source URLs provided
5. Be thorough - look for event names, dates, venues throughout ALL the content
6. Include the city and country for each event

For each event, extract:
- name: The event title/name
- description: Brief description (1-2 sentences max)
- date: The date in any format mentioned
- time: The time if mentioned
- venue: The venue/location name
- address: Street address if mentioned
- city: City name (REQUIRED - use the search location if not specified)
- country: Country name (REQUIRED - use Switzerland if in Swiss cities)
- price: Price information if mentioned
- category: Type of event (concert, party, exhibition, sports, etc.)
- source_url: The URL where this event info came from (REQUIRED - use one from SOURCE URLS)
- image_url: Image URL if available

IMPORTANT: Extract as many events as you can find. Look for:
- Specific event names and titles
- Performances, concerts, shows
- Exhibitions, openings
- Festivals, fairs, markets
- Sports events, matches
- Workshops, classes

Return a JSON object with:
{
  "events": [...],
  "total_found": <number>
}"""


EXTRACTION_USER_PROMPT = """Extract all events from the following search results for {location}:

--- PERPLEXITY CONTENT ---
{perplexity_content}

--- SOURCE URLS ---
{source_urls}

--- ADDITIONAL CONTEXT FROM SERPAPI ---
{serpapi_snippets}

Extract every distinct event you can find. Each event must have at minimum: name, city, country, and source_url.
Return valid JSON only."""
