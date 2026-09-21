# Iteration Plan — Next 2 Weeks

*[Version française : iteration_plan.fr.md](iteration_plan.fr.md)*

This plan starts from the current state (functional system, 17 microservices, 11 synthetic cases
evaluated, see `docs/eval_results.md`) and prioritizes what has the most impact before exposure to
real users.

## Priority 1 — Close the known gap

**Rent-vs-market plausibility rule** (`case_06_adversarial_abnormal_rent`, documented in
`docs/eval_results.md`). Today, `services/risk/app/rules.py` never compares the declared rent to a
market reference: an unrealistic rent (too high or too low) passes with no warning, even though the
`market` service already computes a median price per m².

- Add a rule comparing `market_rent_per_m2` (to be created, computed from DVF or a complementary
  rental data source) to the declared rent, with a deviation threshold (e.g. ±25%) triggering a
  medium-severity risk.
- Write the corresponding adversarial test case first, in its "must now fail if not fixed" form, to
  avoid a false victory.
- Estimated effort: 2-3 days (the hardest part is finding a reliable market-rent source in French
  open data — DVF only covers sales, not rentals).

## Priority 2 — Real timed user trial

The evaluation report explicitly flags it: the baseline-vs-system comparison today is only a
qualitative estimate (see `docs/eval_results.md`, "Baseline vs system" section), for lack of access
to a real investor during the sprint.

- Recruit 2-3 real real-estate investors (professional networks, specialized forums).
- Have them analyze the same real (anonymized) deal once manually (timed), once with DealPilot AI.
- Measure: actual time, number of risks identified in each case, stated confidence in the final
  decision.
- Estimated effort: 1 week (recruiting + sessions + synthesis).

## Priority 3 — Shared, independently queryable database

Today, the only durable state is the LangGraph checkpointer (`docs/architecture.md`, Persistence
section) — correct for resuming after a restart, but impossible to query independently ("show me
every deal with an unresolved high-severity risk").

- Introduce a shared Postgres database, one table per service (no schema coupling), fed in parallel
  with the LangGraph graph rather than replacing it.
- First concrete use case: a multi-deal dashboard for the investor (beyond the point-in-time
  comparison already shipped).
- Estimated effort: 3-4 days.

## Priority 4 — Strengthen continuous evaluation

- Extend `eval/run_eval.py` to run in CI (GitHub Actions) on every change touching `services/` or
  `shared/`, not just on demand.
- Add synthetic cases targeting the developer/citizen module (today, the 11 cases only cover the
  investor flow): agricultural zone refusing any permit, land in an unopened AU zone, land with no
  utility hookups.
- Estimated effort: 2 days.

## Priority 5 — GPU reliability in production

The cross-service GPU lock (`flock`, `docs/architecture.md`) correctly serializes two services on
one GPU, but still assumes a single physical GPU. For several concurrent users in a real
environment:
- Add a visible queue on the frontend (position in queue, estimated wait time) instead of a silent
  block.
- Evaluate a second GPU or a managed provider (Replicate/Modal) to absorb peaks, keeping the
  self-hosted mode as the default option (already dropped once for cost, see
  `docs/architecture.md`, but viable for occasional scale-out).
- Estimated effort: 2-3 days.

## Priority 6 — Missing unit test coverage

Found during the global system audit: `intake`, `document-intel`, `vision`, `market`,
`design-agent`, and `exterior-render` have no unit tests at all (6 services out of 17). Some of
these services (`document-intel`, `design-agent`) also instantiated their Groq client at module
load time, making it impossible to test even pure logic without a real API key — already fixed for
4 services via lazy client loading, to be generalized.

- Write tests for each service's pure logic (parsing, validation, request construction) without
  depending on real network calls — follow the pattern already in place in
  `location-intel/tests/test_osm.py` (tests `_build_query`/`aggregate_categories`, not the HTTP
  call itself).
- `exterior-render` (bpy/Blender) remains hard to unit-test conventionally — consider automated
  smoke tests rather than classic pytest.
- Estimated effort: 2-3 days.

## What is deliberately not in this plan

- Automated purchase decisions, binding legal advice, structural certification, automated
  negotiation: remain product non-goals (`docs/case_study.md`), not temporary technical
  limitations.
- Direct scraping of listing portals: ToS risk not re-evaluated, DVF stays the source of truth.

## Metrics to track over these two weeks

- **Adoption**: number of real deals submitted by testing investors (target: ≥ 5 deals each over
  the period).
- **Quality**: share of checks passing in `eval/run_eval.py` (maintain 100% outside documented
  limitations) after each change.
- **User trust**: stated rating (1-5) on "I would trust this file to support a real offer",
  collected after each Priority 2 user trial.
