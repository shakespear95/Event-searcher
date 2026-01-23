# Project: Secret Nature / Whats Up App (Python Rebuild)
## Engineering Roadmap & Guardrails

---

### 1. Competitor Analysis & Our Edge

#### What Competitors Do (Eventbrite, Meetup, AllEvents)

| Platform | Strengths | Weaknesses |
|----------|-----------|------------|
| **Eventbrite** | Curated "It Lists", video listings, Spotify integration, 180K+ businesses | Pay-to-play discovery, unverified data, generic algorithm |
| **Meetup** | 60M+ users, group-based, AI recommendations (2026), community focus | Misses hidden gems, no weather, no verification |
| **AllEvents** | 40K+ cities, aggregates sources, social features, real-time details | Scraped data often outdated, broad but shallow |

#### Industry-Wide Gaps We Exploit

| Gap | Our Solution |
|-----|--------------|
| Unverified events | Perplexity source URL required or event rejected |
| No weather awareness | Weather API blocks bad outdoor recommendations |
| Sponsored events dominate | Zero pay-to-play - organic discovery only |
| Popular over hidden | Prioritize secret nature spots and hidden gems |
| Black box AI | Full traceability - user sees every data source |
| Generic global | Deep Liechtenstein/region expertise |

---

### 2. Core Architecture (The "Tom & Dominique" Stack)
* **Backend:** Python (Local development first, deploying to **Railway**)
* **Frontend:** Next.js / PWA (Deployed to **Vercel**)
* **Database:** Supabase (Auth & Multi-tenant data)
* **Agent Logic:** Python-based orchestration (LangGraph or PydanticAI) focusing on **Traceability**

---

### 3. Solving the "Hallucination & Variable Loss" Problem

* **Strict State Schema:** Global State Object with predefined keys. System kills process if agent writes to undefined key.
* **Intermediate Transparency:** Log **every single tool call** to console/database before next step.
* **The "Grounding" Agent:** Perplexity as "Truth Engine." No event exists unless Perplexity provides valid source URL.

---

### 4. Implementation Phases

#### Phase 0: Foundation
| Task | Purpose |
|------|---------|
| Define Global State Schema (Pydantic models) | Single source of state truth |
| Set up project structure & virtual env | Clean development environment |
| Create config management (.env files) | Environment separation |
| Set up logging infrastructure | Traceability from day one |
| Secure API keys for all services | Real API access |

#### Phase 1: Core Tools + FastAPI Shell
| Task | Purpose |
|------|---------|
| FastAPI skeleton with health check | Foundation for all endpoints |
| `search_perplexity.py` - REAL API | Truth engine for events |
| `weather_check.py` - REAL API | Location/date validation + outdoor event blocking |
| `sap_connector.py` - skip until sandbox available | No fake data |
| Response caching layer | Avoid repeat API calls, save costs |
| Tool-level tests with REAL responses (pytest) | Validate actual behavior |

#### Phase 2: Agent Orchestration
| Task | Purpose |
|------|---------|
| LLM router with fallback chain | Resilience |
| Fallback order: Perplexity → Gemini → OpenAI → "Unavailable" | Never guess |
| Parallel execution with circuit breakers | Performance + fault tolerance |
| Structured output enforcement (Pydantic) | No loose JSON |
| 20 integration tests with real data | Validate end-to-end |

#### Phase 3: Security & Integration
| Task | Purpose |
|------|---------|
| CORS allowlist (Vercel domains only) | No wildcard security holes |
| Rate limiting per tenant | Cost control + fair usage |
| Supabase auth integration | Multi-tenant security |
| Railway deployment | Production backend |

#### Phase 4: Frontend Bridge
| Task | Purpose |
|------|---------|
| PWA connection to Railway API | Full stack integration |
| Multi-tenancy data isolation | User privacy |
| End-to-end tests | Production readiness |

---

### 5. Golden Rules for the AI Agent

| Rule | Description | Beats Competitor |
|------|-------------|------------------|
| #1 | Never generate data not provided in tool output | AllEvents shows fake data |
| #2 | If a tool fails, return "Data Unavailable" - never guess | Meetup guesses |
| #3 | Every response must be traceable to source API | None offer this |
| #4 | No mock data - real APIs only | Internal quality |
| #5 | Block outdoor events when weather is bad | No competitor does this |
| #6 | Require verified source URL for every event | Eventbrite doesn't verify |
| #7 | Prioritize hidden gems over sponsored/popular | Eventbrite pay-to-play |

---

### 6. Fallback & Resilience Strategy

```
API Call Flow:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│ Perplexity  │───▶│   Gemini    │───▶│   OpenAI    │───▶│ "Unavailable"   │
│  (Primary)  │fail│ (Fallback 1)│fail│ (Fallback 2)│fail│  (Final State)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────────┘

Circuit Breaker: If API fails 3x in 5 minutes → skip for 10 minutes
```

---

### 7. Caching Strategy

| Query Type | Cache Duration | Reason |
|------------|----------------|--------|
| Event search | 1 hour | Events don't change frequently |
| Weather data | 30 minutes | Weather updates regularly |
| Location data | 24 hours | Static information |

---

> **Reference:** See `RULES.md` for full project rules
