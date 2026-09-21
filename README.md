# DealPilot AI

*[Version française : README.fr.md](README.fr.md)*

Intelligent system for real-estate acquisition, development, and construction — France.

Turns a real-estate opportunity (listing + documents + photos) into a structured, traceable
analysis file: document intelligence, visual analysis, market comparables, deterministic financial
underwriting, risk register, offer strategy, and due diligence. Also includes a promoter/citizen
module (land feasibility, AI-generated 360° photorealistic building view, conversational AI design,
photorealistic interior/garden rendering).

**What the system does NOT do**: it never decides to buy on your behalf, never gives binding legal
or financial advice, and never certifies structural condition. See `docs/case_study.md` for the
full list of non-goals.

## Quickstart (no technical knowledge required)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- A [Groq](https://console.groq.com/keys) API key (free) and a
  [Google Gemini](https://aistudio.google.com/apikey) API key (free).
- For 3D interior/garden rendering (optional): an NVIDIA GPU with at least 8GB VRAM. Without a GPU,
  every other part of the application works normally.

### Setup (3 steps)

1. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY` and `GEMINI_API_KEY`.
2. Open a terminal in the project folder and run:
   ```
   docker compose up -d
   ```
   (first run: several minutes, while images download)
3. Open [http://localhost:8501](http://localhost:8501) in your browser.

That's it. Pick a role at the top of the page (Investor / Developer / Citizen) and fill in the form
on the left.

### Stopping the application

```
docker compose down
```

Deals already analyzed stay saved (SQLite database persisted in a Docker volume) and are
accessible again on the next startup.

## The three roles

- **🏢 Investor**: submits an existing rental property (listing, documents, photos), gets a
  complete 10-step analysis, can simulate a counter-offer, compare multiple deals, generate a
  plain-language summary, and export the deal file as PDF or Excel.
- **🏗️ Developer**: evaluates construction feasibility on a plot of land (with the real zoning
  district if an address is given), designs a building via a conversational agent, generates a
  photorealistic 360° view of the building plus interior/garden renders.
- **🏠 Citizen**: same module as Developer, for an individual who wants to understand what they can
  build on their own land.

## Note on language

The **application itself runs in French** — this matches the target user persona described in
`docs/case_study.md` (an independent French rental-property investor). Everything a non-developer
needs to run and evaluate the system — this README, the case study, the architecture doc, the AI
collaboration note, and the iteration plan — is available in English. The live system's generated
content (risk register entries, AI summaries, document extraction) stays in French, since that is
the language the target user actually works in.

## Further reading

- `docs/architecture.md` — how the system is built and why.
- `docs/case_study.md` — target user, current manual workflow, non-goals, success metric.
- `docs/eval_results.md` — evaluation test results, including failure scenarios (system output is
  in French; see the English summary at the top of the file).
- `docs/ai_collaboration_note.md` — how this project was built with AI assistance.
- `docs/iteration_plan.md` — what's planned next.
- `docs/demo_script.md` — script for the 5-minute demo video.
- `RUNBOOK.md` — for operators: environment variables, known failure modes, how to debug.

## Third-party component license

Stable Diffusion 1.5/XL model under the CreativeML OpenRAIL-M / Stability AI Community License —
prototype/research use; check the model license before any commercial use.
