# DealPilot AI — Case Study

*[Version française : case_study.fr.md](case_study.fr.md)*

## Target user

**Persona**: independent real-estate investor / small rental-portfolio manager in France, who
sources multi-unit residential buildings themselves through listing sites, then manually analyzes
each opportunity before making an offer.

**Realistic profile**: a handful of deals studied per month, no dedicated team of analysts, Excel
and manual document reading as the only tools. Financially competent but not a lawyer or architect
— depends on external professionals (notary, surveyor, agency) for specialized points, but first
needs to know *which* ones to engage and *what* to ask them.

Two secondary roles covered by the system, derived from the same underlying need (turning a fuzzy
opportunity into a structured file):
- **Developer**: evaluates new-construction feasibility on a plot of land.
- **Citizen**: an individual who wants to understand what they can build on their own land, with no
  technical background.

## Job-to-be-done

> "When I find a building I'm interested in, I want to turn a listing + scattered documents +
> photos into a defensible offer decision, without spending my whole evening on it and without
> risking missing a problem a document already contained."

## Current manual workflow (before the system)

| Step | Trigger | Input | Judgment required | Current tool | Approval | Output | Typical exception |
|---|---|---|---|---|---|---|---|
| 1. Sourcing | New listing seen | Web listing | Does it match my criteria? | Listing site | None | Decision to dig further or not | Incomplete listing |
| 2. Document collection | Contact agency/seller | PDF, emails | Which documents are essential? | Email | None | Document folder | Missing documents not flagged |
| 3. Document reading | Documents received | PDF/scans | Spot inconsistencies (rents, surfaces) | Manual reading | None | Scattered notes | Contradiction missed for lack of systematic comparison |
| 4. Photo analysis | Photos received | JPEG | Spot visible defects | Naked eye | None | Subjective impression | Overconfidence without structural expertise |
| 5. Market comparables | Need to value the property | Memory, listing sites | Which comparables are relevant? | Manual research | None | Rough price range | Confirmation bias |
| 6. Financial model | Price + rents known | Excel | Which assumptions to stress-test? | Personal Excel sheet | Self-checked | Cap rate, cash flow | Undetected formula error |
| 7. Risks | Analysis complete | Everything above | What really needs checking before buying? | Memory/experience | None | Informal list | Risk forgotten because not prioritized |
| 8. Offer | Risks known | Financial analysis | What price to offer, under what conditions? | Intuition + Excel | None | Verbal or email price | Offer not defensible if negotiation happens |
| 9. Due diligence | Offer accepted | Risk register | What to request, in what order? | Memory | None | Ad hoc checklist | Task tied to a risk forgotten |
| 10. Final decision | Due diligence advanced | Entire file | Buy or not? | Human judgment | None formal | Purchase decision | Decision made without reviewing every point |

**Current estimated time**: several hours per deal (collection + reading + modeling), spread over
several days depending on when documents arrive.

## What the system does (and does not do)

**In scope**: the 10 steps above for residential rental real estate in France, plus a land
feasibility/new-construction module (developer/citizen) with a photorealistic 360° view of the
building, AI interior/garden rendering, PDF/Excel export, plain-language summary, counter-offer
simulator, multi-deal comparison.

**Out of scope (explicit non-goals)**:
- Autonomous purchase decision — the system never decides, it informs a human decision.
- Binding personalized legal or financial advice.
- Structural safety certification (visual analysis flags, never certifies).
- Guaranteed valuation (DVF comparables are indicative, never an expert appraisal).
- Automated negotiation with the seller.
- Binding transactional execution (no signature, no real financial commitment).
- Live scraping of listing portals (ToS risk) — synthetic data and DVF (official open data) used
  instead.
- Automatic extraction of numeric rules from a zoning regulation (the system gives the real zoning
  district, not the numeric thresholds it imposes — see `docs/architecture.md`).

## Success metric

**Time to decision**: manual/ChatGPT-only time (baseline, see `docs/eval_results.md`) vs time with
DealPilot AI, on the same representative synthetic deal.

**Secondary metrics (from the original brief)**:
- Accuracy of deterministic financial calculations vs a reference engine (hand calculation): target
  100%.
- Recall on missing critical documents/risks: target ≥ 90%.
- Zero unsourced claim in critical outputs (price, risks, compliance).
- 100% traceability of critical facts to a source, an assumption, or a calculation (see the
  provenance model in `shared/dealpilot_shared/provenance.py`).

See `docs/eval_results.md` for results measured on the synthetic cases.

## Architecture and major trade-offs

17 FastAPI microservices (including a Streamlit frontend) rather than a monolith — a decision made
from day one to isolate each business capability (document extraction, vision, market, finance,
risk, offer, due diligence): replacing a deprecated LLM provider, or one service going down,
touches only a single piece rather than the whole pipeline. Accepted cost in exchange: more
operational complexity (17 containers, a recurring documented pitfall — every service bundles its
own copy of the shared data contract and must be rebuilt after any schema change).

Notable trade-offs:
- **Deterministic financial engine** (never delegated to the LLM) — calculation accuracy owes
  nothing to the randomness of text generation.
- **Systematic provenance**: every numeric value carries its candidates and their sources; two
  contradictory sources are never silently resolved (`contested=true`), both stay visible with
  their origin.
- **Persistence**: `AsyncSqliteSaver` (LangGraph) rather than in-memory state — restarting the
  orchestrator container no longer loses deals in progress.
- **Visuals — a pivot made mid-sprint**: an early version generated a measurable 3D massing model
  (Blender/Cycles, animated by construction phase). Compared side-by-side with the photorealistic
  SDXL rendering already used for interiors, the 3D model was judged visually insufficient for real
  use; it was replaced in the main flow by an AI-generated 360° view (8 angles, shared seed for
  visual consistency). The Blender code stays in the repository but is no longer on the main path —
  a concrete example of a trade-off between perceived quality and geometric accuracy, resolved in
  favor of perceived quality for this sales/presentation use case.
- **GPU reliability**: a single GPU shared between two image-generation capabilities (SDXL and the
  Blender pipeline that stays in the repo) — locked with a cross-process file lock after a real
  contention test showed a ~2x mutual slowdown without it.

Full detail: `docs/architecture.md`.

## Work delegated to AI and human judgment retained

This project was built with Claude Code as a development assistant. Delegated to AI: code
generation once technical choices were settled, documentation writing, adversarial test-case
design, bug diagnosis. Kept on the human side: the choice of microservices architecture, the choice
of market (French residential rental), the full 10-step scope from day one, the final trade-off
between technical depth and documentation, and the decision to pivot from the 3D model to the 360°
view after a comparative visual evaluation. Every AI claim was verified before being accepted
(concrete examples, including a case where an AI hypothesis about the cause of a test failure
turned out to be wrong after manual reproduction).

Full detail, including what was rejected or corrected: `docs/ai_collaboration_note.md`.

## Failures found, changes, results, and limitations

**Real bug found and fixed**: the `market` service outage test revealed a complete pipeline crash
(HTTP 500) instead of graceful degradation — fixed, then the same safety net was extended
preemptively to 6 other points in the system that had the same untested weakness, before a real
incident could reveal it.

**Framing bug found and fixed** (360° view): the first photorealistic generations of the building
framed in tight on 1-2 windows instead of showing the whole building. Root cause: the prompt
exceeded SDXL's text model (CLIP) 77-token limit, and the wide-framing instructions were precisely
the part getting truncated. Fixed by reordering the prompt so critical instructions land before the
cutoff — verified visually before/after.

**Known limitation, not fixed**: no rule detects a declared rent that is abnormally high or low
relative to the market (`risk/app/rules.py`) — an unrealistic rent produces flattering financial
indicators with no warning. Documented and deferred to the iteration plan rather than hidden.

**Assumed structural limitation**: no real timed user trial was conducted (no access to a real
investor during the sprint) — the reported time savings remain a qualitative estimate, explicitly
flagged as such rather than presented as proof.

Full measured results (29/29 checks, 1 documented limitation): `docs/eval_results.md`.

## Next two-week iteration plan

Priorities, in order: (1) rent-vs-market plausibility rule — the only known, unfixed functional
gap; (2) real timed user trial with 2-3 investors to replace the qualitative estimate with a real
measurement; (3) shared database queryable independently of the execution graph; (4) unit test
coverage for the 6 services that still lack it (`intake`, `document-intel`, `vision`, `market`,
`design-agent`, `exterior-render`); (5) GPU reliability plan for concurrent multi-user usage.

Full detail with adoption/quality metrics to track: `docs/iteration_plan.md`.
