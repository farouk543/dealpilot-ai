# Demo Script — 5 minutes

*[Version française : demo_script.fr.md](demo_script.fr.md)*

For recording a presentation video. Timings below are indicative. The live system's own UI and
generated content (risk labels, summaries, etc.) are in French — that matches the target user
described in `docs/case_study.md` (a French rental-property investor); narrate over it in English.

## 1. The problem and the baseline (0:00 – 0:45)

> "A real-estate investor who finds a building to buy today spends several hours, spread over
> several days, manually reading PDF documents, comparing rents, researching comparable prices, and
> modeling cash flow in Excel — with no safety net against human error or oversight. [Show
> `docs/case_study.md`, the 10-step manual workflow table, on screen for a few seconds.] DealPilot
> AI turns that into a structured, traceable deal file in minutes, without ever deciding on the
> investor's behalf."

## 2. Live walkthrough on a real case (0:45 – 3:00)

Use the synthetic case `case_01_normal_complete` (or an equivalent deal filled in live):

1. Open [http://localhost:8501](http://localhost:8501), **Investor** role.
2. Fill in the form: listing, price, rent, upload documents (`etat_locatif`,
   `titre_de_propriete`) and a photo.
3. Submit — show the deal progressing through the 10 steps (documents, vision, market, finance,
   risks, offer, due diligence).
4. Once complete, show:
   - The **risk register** with severity and its supporting evidence.
   - The **offer strategy** (target price, max price, conditions).
   - A **contested** field if present (e.g. rent inconsistent between two sources) — highlight that
     the system never silently picks a value, it shows both with their origin.
5. Click **"Plain-language summary"** — show the summary (in French, matching the target user).
6. Simulate a **counter-offer** — show the before/after comparison.
7. Export to **PDF** — briefly open the generated file.

## 3. Non-developer UX (3:00 – 3:30)

> "All of this runs with no command line for the end user — a 3-step Docker install documented in
> `README.md`, then everything happens in the browser. The three roles (investor, developer,
> citizen) each get their own workflow suited to their need, not a generic technical interface."

Optional if time allows: switch briefly to the **Developer/Citizen** role, show land feasibility
with the real zoning district fetched from an address, show the pre-generated **360° view** (8
angles, AI, drag to rotate), then an interior render kept visually consistent with that facade
(same building "identity" via a shared random seed).

## 4. Evaluation and failure handling (3:30 – 4:30)

> "The system was tested against 11 synthetic cases, 9 of them adversarial, matching the failure
> modes identified from the start: contradictory documents, missing documents, abnormal rent,
> ambiguous visual defect, external service outage, unprofitable financing, a prompt-injection
> attempt inside a document. [Show `docs/eval_results.md`, the English summary at the top.] 29
> checks passed, 0 failed, one known limitation documented rather than hidden."

> "One concrete example: the market-service outage test revealed a real bug — the pipeline crashed
> entirely instead of continuing without comparables. Fixed, then the same safety net was added
> preemptively to 6 other points in the system with the same untested weakness. [Show the 'what this
> test pass found and fixed' section.]"

## 5. Results and the main limitation (4:30 – 5:00)

> "This system never replaces the investor's judgment — it never decides to buy, never gives
> binding legal advice, and never certifies structural condition. The most important current
> limitation: no rule yet detects a rent that's abnormally high or low relative to the market —
> documented in `docs/eval_results.md` and planned as the top priority in `docs/iteration_plan.md`.
> A real trial with real investors, timed against their actual manual workflow, is the second
> priority, to replace the qualitative time-savings estimate with a real measurement."

## Recording notes

- Start the containers ahead of time (`docker compose up -d`, wait until everything is `healthy`)
  so demo time isn't lost on a cold start.
- SDXL rendering (a single interior/facade image) takes ~30-60s — if demonstrated, start it, then
  keep talking during generation rather than waiting in silence.
- The **360° view** (8 angles) takes ~5 minutes — too long for a live demo. **Pre-generate it before
  recording** for the same property/style shown in the demo, and just show/manipulate the
  already-ready result (drag to rotate) during the recording.
- Have `docs/eval_results.md` and `docs/case_study.md` already open in tabs so you don't have to
  search for them on camera.
