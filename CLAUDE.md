# CLAUDE.md - Event Searcher / Secret Nature / Whats Up App

## Project Overview
Event discovery app that finds verified, real events using multiple search APIs + LLM extraction. Focuses on hidden gems, verified sources, and weather-aware recommendations.

## Architecture
- **Frontend**: Next.js 14 + React 18 + Tailwind CSS (deployed on **Vercel**)
- **Backend**: Python FastAPI + Uvicorn (deployed on **Render**)
- **Database/Auth**: Supabase (PostgreSQL + Auth with Google OAuth)
- **LLMs**: Claude (primary), Gemini (extraction fallback), OpenAI (fallback)

## Live URLs
- **Frontend**: `https://event-searcher-95.vercel.app` (+ preview deployments)
- **Backend**: `https://event-searcher-0wnu.onrender.com`
- **Supabase**: `https://clxbjqeqpreryvpnaspp.supabase.co`

## Key File Paths

### Backend (`backend/`)
- `app/main.py` - FastAPI app entry, CORS config, middleware
- `app/core/config.py` - Pydantic Settings (all env vars)
- `app/core/auth.py` - Supabase JWT auth
- `app/core/supabase.py` - Supabase client
- `app/api/endpoints/search.py` - Search endpoint
- `app/api/endpoints/users.py` - User profile, favorites, history
- `app/api/endpoints/health.py` - Health check
- `app/agent/orchestrator.py` - Search orchestration pipeline
- `app/schemas/` - Pydantic models (`event.py`, `search.py`, `state.py`, `extraction.py`, `user.py`)
- `app/services/search/` - Search providers: `perplexity.py`, `serpapi.py`, `serper.py`, `firecrawl.py`, `exa.py`, `ticketmaster.py`, `merger.py`
- `app/services/llm/` - LLM clients: `claude.py`, `gemini.py`, `openai.py`, `router.py`, `base.py`
- `app/services/scraper/` - Stealth scraper with Playwright

### Frontend (`frontend/`)
- `app/page.tsx` - Home/search page
- `app/results/page.tsx` - Search results
- `app/profile/page.tsx` - User profile
- `app/settings/page.tsx` - Settings
- `app/layout.tsx` - Root layout
- `lib/api.ts` - Backend API client (all fetch calls)
- `lib/supabase.ts` - Supabase client
- `components/` - EventCard, EventDetailModal, MapView, UI components

## API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/api/v1/search` | Optional | Search events |
| GET | `/api/v1/search/categories` | No | List categories |
| GET | `/api/v1/search/filters` | No | Filter options |
| GET | `/api/v1/users/me` | Yes | Get profile |
| PATCH | `/api/v1/users/me` | Yes | Update profile |
| GET | `/api/v1/users/me/search-history` | Yes | Search history |
| DELETE | `/api/v1/users/me/search-history` | Yes | Clear history |
| GET | `/api/v1/users/me/favorites` | Yes | List favorites |
| POST | `/api/v1/users/me/favorites` | Yes | Add favorite |
| DELETE | `/api/v1/users/me/favorites/{id}` | Yes | Remove favorite |

## CORS Configuration
- Static origins in `ALLOWED_ORIGINS` env var (comma-separated)
- Regex `https://event-searcher[a-z0-9-]*\.vercel\.app` catches all Vercel preview deploys
- On Render: `ALLOWED_ORIGINS` env var **overrides** the default in `config.py` - make sure it includes all production Vercel domains
- Credentials enabled (needed for auth tokens)

## Common Commands
```bash
# Backend local dev
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend local dev
cd frontend && npm install --legacy-peer-deps && npm run dev

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "concerts", "location": "Vienna, Austria", "category": "music"}'
```

## Implementation Status (as of 2026-02-23)

### Completed
- FastAPI backend with full search pipeline (6 providers: Perplexity, SerpAPI, Serper, Firecrawl, Exa, Ticketmaster)
- LLM integration with Claude (primary) + Gemini/OpenAI fallbacks
- Search result merging and deduplication
- Stealth scraper with Playwright
- Pydantic schemas for all data models
- Next.js frontend with search UI, results, event cards, map view
- Supabase auth (Google OAuth) with user profiles
- Favorites and search history (Supabase-backed)
- Deployed: Vercel (frontend) + Render (backend) + Supabase (DB/auth)
- CORS configured with regex for all Vercel preview deployments

### Known Issues
- Render free tier cold starts (~30s after 15min inactivity)
- CORS: if `ALLOWED_ORIGINS` is set on Render, it overrides config.py defaults - regex is the reliable fallback

### Not Yet Implemented
- Weather API integration (placeholder exists)
- Redis caching layer
- Full test suite

## Rules
See `RULES.md` for full project rules. Key ones:
- No mock data (rule C6) - real APIs only
- Every event must have a verified source URL (rule PR1)
- No wildcard CORS - explicit allowlist + regex (rule AR4)
- Pydantic schemas for all API responses (rule A4)
