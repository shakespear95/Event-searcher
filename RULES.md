# Project Rules - Source of Truth
> **Last Updated:** 2026-01-22
> **Status:** Backend Core Complete - Ready for Frontend

---

## Documentation Rules

| # | Rule | Reason |
|---|------|--------|
| D1 | No markdown files after every procedure | Avoid documentation sprawl |
| D2 | This file (`RULES.md`) is the single source of truth | Centralized reference |
| D3 | Update this file after every implementation | Keep rules current |

---

## Code Integrity Rules

| # | Rule | Reason |
|---|------|--------|
| C1 | Before creating a variable, **search the codebase first** | Prevent dead code and duplication |
| C2 | Never create a new function if one already exists | Reuse over reinvention |
| C3 | Delete unused code immediately - no commenting out | Keep codebase clean |
| C4 | Every variable must have a single owner/origin | Traceability |
| C5 | No hardcoded values - use config/env files | Maintainability |
| C6 | No mock data or fake API responses - use real APIs only | Mocks hide real behavior and create false confidence |

---

## Agent & API Rules

| # | Rule | Reason |
|---|------|--------|
| A1 | Never generate data not provided by a tool output | Prevent hallucinations |
| A2 | If an API fails, return "Data Unavailable" - never guess | Data integrity |
| A3 | Every response must trace back to its source API | Accountability |
| A4 | Use Pydantic schemas for all API responses | Enforce structure |
| A5 | Log every tool call before proceeding to next step | Debugging & transparency |

---

## Architecture Rules

| # | Rule | Reason |
|---|------|--------|
| AR1 | Backend (Python) and Frontend (Next.js) in separate concerns | Clean separation |
| AR2 | All state changes go through the Global State Object | Single source of state |
| AR3 | Reject any write to undefined schema keys | Prevent state pollution |
| AR4 | No wildcard CORS - explicit domain allowlist only | Security |
| AR5 | Environment-specific configs (dev/staging/prod) | Safe deployments |

---

## Development Workflow Rules

| # | Rule | Reason |
|---|------|--------|
| W1 | Test locally before any deployment | Catch issues early |
| W2 | One feature/fix per commit | Clear git history |
| W3 | No secrets in code - use environment variables | Security |
| W4 | Run existing tests before adding new code | Don't break what works |

---

## Communication Rules (Planning Phase)

| # | Rule | Reason |
|---|------|--------|
| P1 | Clarify requirements before implementation | Avoid rework |
| P2 | Flag assumptions explicitly | Transparency |
| P3 | Update this document when rules change | Living document |

---

## Product Rules (Learned from Competitors)

> Competitors analyzed: Eventbrite, Meetup, AllEvents

| # | Rule | Reason | Competitor Gap |
|---|------|--------|----------------|
| PR1 | Every event MUST have a verified source URL | Competitors show unverified/scraped data | AllEvents shows outdated events |
| PR2 | Weather check before recommending outdoor events | No competitor does this | Users get bad recommendations |
| PR3 | No sponsored/paid event boosting | Eventbrite buries organic events | Pay-to-play kills discovery |
| PR4 | Prioritize hidden gems over popular events | All competitors favor popular/promoted | Secret spots get buried |
| PR5 | Show data source for every piece of information | No competitor provides traceability | Users can't verify info |
| PR6 | Deep local focus beats broad global coverage | AllEvents is broad but shallow | Generic recommendations |
| PR7 | Reject event if verification fails - never show unverified | Competitors show "maybe" events | Builds user trust |

---

## Competitive Differentiators

| What We Do | What Competitors Do |
|------------|---------------------|
| Verified events only (source URL required) | User-submitted or scraped data |
| Weather-aware recommendations | No weather integration |
| Zero hallucination (strict schema) | AI can suggest fake events |
| Organic discovery (no pay-to-play) | Sponsored listings dominate |
| Full traceability (user sees sources) | Black box recommendations |
| Secret/hidden gems focus | Popular events prioritized |
| Liechtenstein/region deep knowledge | Generic global coverage |

---

## Scraper Rules

| # | Rule | Reason |
|---|------|--------|
| S1 | Always check robots.txt before scraping | Respect site preferences |
| S2 | Max 1 request per 2-5 seconds per domain | Don't overload servers |
| S3 | Only scrape public event data | No private/login-required data |
| S4 | Cache scraped results aggressively | Reduce repeat scraping |
| S5 | Stop if site explicitly blocks | Respect their decision |
| S6 | Prefer official APIs when available | Scrape only when no API exists |
| S7 | Use residential proxies for production | Datacenter IPs get blocked |
| S8 | Rotate user agents per request | Avoid fingerprinting |
| S9 | Randomize delays (human-like behavior) | Avoid pattern detection |
| S10 | Log all scraper activity | Debugging and compliance |

---

## Search Parameters Reference

### Categories
Music, Movies, Sports, Nature, Food & Drinks, Arts & Culture, Nightlife, Theater, Comedy, Workshops, Family, Networking, Wellness, Markets, Festivals, Tech & Gaming, Community, Religious

### Core Parameters
- `query` (string) - Free text search
- `category` (enum) - Event category
- `results_count` (int) - Max 20 per search
- `location` (string) - City/address/coordinates
- `radius_km` (int) - 5, 10, 25, 50, 100, 200

### Time Parameters
- `date_from` / `date_to` (date)
- `time_of_day` (morning/afternoon/evening/night/any)
- `day_type` (weekday/weekend/any)

### Filters
- `price_range` (free/budget/mid/premium/any)
- `indoor_outdoor` (indoor/outdoor/both)
- `verified_only` (bool) - Default: true
- `hidden_gems` (bool) - Default: true
- `weather_safe` (bool) - Default: true

---

## Implementation Status

### ✅ Completed (2026-01-22)

| Component | Status | Details |
|-----------|--------|---------|
| **FastAPI Backend** | ✅ Working | `backend/app/main.py` - Running on port 8000 |
| **Pydantic Schemas** | ✅ Complete | `event.py`, `search.py`, `state.py`, `extraction.py` |
| **LLM Integration** | ✅ Working | Claude (prompts), Gemini (extraction), Router with fallbacks |
| **Perplexity Search** | ✅ Working | Deep search with source URLs |
| **SerpAPI Search** | ✅ Working | Google Events integration |
| **Search Merger** | ✅ Working | Deduplication by URL |
| **Stealth Scraper** | ✅ Working | Playwright with anti-detection |
| **Gemini Extraction** | ✅ Working | Extracts real events from Perplexity content |
| **Structured Logging** | ✅ Working | Tool call tracing (Rule A5) |

### 🔄 In Progress

| Component | Status | Next Steps |
|-----------|--------|------------|
| Weather API | ⏳ Placeholder | Integrate real weather API |
| Redis Caching | ⏳ Not started | Add caching layer |
| Supabase | ⏳ Not started | Database integration |

### 📋 Next Session Tasks

1. **Frontend (Next.js)** - Build UI for search interface
2. **Weather Integration** - Real weather API for outdoor events
3. **Caching** - Redis for API response caching
4. **Database** - Supabase for user preferences / history

### API Endpoints

| Endpoint | Method | Status |
|----------|--------|--------|
| `/health` | GET | ✅ Working |
| `/api/v1/search` | POST | ✅ Working |

### Test Command

```bash
# Start server
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "concerts", "location": "Vienna, Austria", "category": "music"}'
```

---

## Change Log

| Date | Change | Section |
|------|--------|---------|
| 2026-01-22 | Initial rules created | All |
| 2026-01-22 | Added C6: No mock data rule | Code Integrity |
| 2026-01-22 | Added Product Rules & Competitive Differentiators (from Eventbrite, Meetup, AllEvents analysis) | Product Rules |
| 2026-01-22 | Added Scraper Rules (S1-S10) and Search Parameters Reference | Scraper Rules |
| 2026-01-22 | Backend core complete - search pipeline working end-to-end | Implementation Status |

