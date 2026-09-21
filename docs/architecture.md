# Architecture — DealPilot AI

*[Version française : architecture.fr.md](architecture.fr.md)*

## Overview

16 FastAPI microservices + a Streamlit frontend, orchestrated by an `orchestrator` service that
runs a LangGraph graph (10 sequential steps for acquisition), and proxies calls for the
developer/citizen module (feasibility, conversational design, AI rendering, summary, export).

```
                          ┌─────────────┐
                          │  frontend   │  Streamlit (3 roles: investor/developer/citizen)
                          └──────┬──────┘
                                 │ HTTP
                          ┌──────▼──────┐
                          │ orchestrator│  LangGraph StateGraph + REST proxy
                          └──────┬──────┘
        ┌──────────┬─────────────┼─────────────┬──────────┬───────────┐
        ▼          ▼             ▼             ▼          ▼           ▼
   intake   document-intel   vision       market   location-intel  financial-engine
        │          │             │             │          │           │
        ▼          ▼             ▼             ▼          ▼           ▼
      risk  →   offer  →  due-diligence      land-feasibility   design-agent
                                                    │                 │
                                          interior-render      exterior-render
                                          (SDXL, 360° facade)  (Blender/Cycles, kept
                                                                in the repo but off the
                                                                main path — see below)
                                                    │
                                             summary   report
```

Each service only knows its own responsibility; only the orchestrator sees the full state of a
deal (`DealState`).

## Why microservices (not a monolith)

A decision made from the project's start: isolating each business capability (document extraction,
vision, market, finance, risk, offer, due diligence) makes it possible to:
- Replace an LLM provider without touching the rest (already happened twice: deprecated Groq and
  Gemini models migrated mid-sprint, an isolated change in `document-intel`/`vision`/etc.).
- Isolate failures: a service going down must not take down the whole pipeline (see
  `docs/eval_results.md`, `case_09` — found broken, then fixed).
- Separate test responsibilities: each service has its own independent `pytest` suite.

Cost accepted in exchange: more operational complexity (17 containers to run, a ~350-line
`docker-compose.yml`), internal network latency, and — until recently — minimal shared state (see
below).

## Shared contracts (`shared/dealpilot_shared`)

Every service depends on a single shared Python package containing the Pydantic models for
inter-service contracts (`PropertyRecord`, `DealState`, `RiskRegister`, `LandFeasibility`, etc.).

**A pitfall discovered and documented**: modifying this package isn't enough — each service bundles
its own copy, built at Docker build time. Forgetting to rebuild a service after a shared contract
change leaves it running with a stale schema, silently (Pydantic ignores fields it doesn't know
about instead of raising an error). Hit in practice when adding the `address` field to
`LandConstraints`: the orchestrator ignored the field until it was explicitly rebuilt. See
`RUNBOOK.md` for the full rebuild procedure.

### Provenance and traceability

Every numeric value in the deal (`FieldWithCandidates`) carries the list of its candidates with
their `Provenance` (source type, reference, confidence, note). If two sources give different
values, neither is silently chosen: the field is marked `contested=true` and both stay visible with
their origin. This is the system's central traceability mechanism, explicitly tested by adversarial
cases `case_03` and `case_08` (`docs/eval_results.md`).

## Persistence

**Deal state**: `AsyncSqliteSaver` (LangGraph checkpointer), a SQLite file in a Docker volume
(`orchestrator_db`). Replaces an in-memory `MemorySaver` that lost every deal in progress on the
slightest orchestrator container restart.

**No shared business database**: each service remains stateless beyond its own call; the system's
only durable state is the LangGraph graph's. This is an assumed simplification for this sprint — a
real multi-user product would want a shared Postgres database with a history queryable
independently of the execution graph (see `docs/iteration_plan.md`).

## Reliability

- **Retry with backoff** (`shared/dealpilot_shared/http_retry.py`) on every call to third-party APIs
  (Groq, Gemini, DVF, BAN, Apicarto): up to 2 additional attempts before giving up.
- **Systematic graceful degradation**: every node in the orchestrator graph catches failures from
  its downstream service and turns them into a visible error fact (`*_error`) rather than letting
  the exception propagate. See `docs/eval_results.md` for the discovery and fix of the one point
  that was initially missing it (`market`).
- **Cross-service GPU lock** (`shared/dealpilot_shared/gpu_lock.py`): a single GPU available, shared
  between `interior-render` (SDXL) and `exterior-render` (Blender/Cycles) — two separate containers
  a plain local `threading.Lock` cannot coordinate. A file lock (`flock`) on a Docker volume mounted
  into both services acts as a cross-process mutex. Added after a real contention test showed a ~2x
  mutual slowdown without it (VRAM within 300MB of the card's limit); `interior-render` also keeps
  its own `threading.Lock` for concurrent requests within the same process.
- **Structured logging with a correlation ID** (`shared/dealpilot_shared/logging_utils.py`): every
  deal (`deal_id`) is propagated as an HTTP header (`X-Correlation-ID`) across every inter-service
  call, making it possible to trace a deal's entire path through the combined logs of the 17
  services.

## External data sources

| Source | Usage | Why this one |
|---|---|---|
| Groq (`openai/gpt-oss-120b`) | Document extraction, summary, design agent, location analysis | Fast, low-cost LLM for structured extraction |
| Google Gemini (`gemini-3.6-flash`) | Visual analysis | Groq had no vision-capable model at the time of the sprint |
| DVF (`files.data.gouv.fr/geo-dvf`) | Market comparables | Real transaction data, official open data — no listing scraping (explicit non-goal) |
| BAN (`api-adresse.data.gouv.fr`) | Address geocoding | Official national address database, free |
| Geoportail de l'Urbanisme / Apicarto (`apicarto.ign.fr`) | A parcel's real zoning district | Official registry — gives the zone's identity, not the numeric rules (the registry does not expose those nationally in machine-readable form) |
| Overpass API (OpenStreetMap) | Neighborhood points of interest | Open data, free, dense coverage in France |
| Stable Diffusion XL (self-hosted) | Photorealistic interior/garden/360° facade rendering | Free and unlimited once the model is downloaded, unlike paid APIs (Replicate tested then dropped for this reason) |
| Blender/Cycles (self-hosted, `exterior-render`) | Measurable 3D massing model animated by construction phase | An avenue explored for a geometrically exact volume; kept in the repo but removed from the main flow after a visual comparison with the SDXL rendering — see `docs/case_study.md` |

## Technical non-goals (recap)

See `docs/case_study.md` for the full list of product non-goals. Technically, this means:
`listing_url` is never fetched live (stored only as a provenance reference), no valuation is ever
presented as guaranteed, and the real zoning district is never automatically translated into
numeric rules.
