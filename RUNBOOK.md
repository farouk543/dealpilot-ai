# RUNBOOK — DealPilot AI

*[Version française : RUNBOOK.fr.md](RUNBOOK.fr.md)*

For the system operator (not the end user — see `README.md` for that).

## Start / stop

```
docker compose up -d          # start everything
docker compose down           # stop everything (persisted data stays in volumes)
docker compose ps             # each service's status
docker compose logs -f <name> # a service's live logs
```

## Environment variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Document extraction, summary, design agent, location analysis |
| `GEMINI_API_KEY` | Yes | Visual analysis (Groq has no vision model) |
| `GROQ_MODEL` | No (default `openai/gpt-oss-120b`) | Groq model — Groq models get deprecated regularly, see below |
| `GEMINI_MODEL` | No (default `gemini-3.6-flash`) | Same for Gemini |
| `SD_MODEL_ID` | No (default `stabilityai/stable-diffusion-xl-base-1.0`) | Interior/garden rendering model |
| `DVF_YEARS` | No (default `2023,2022,2021`) | DVF transaction years to load |

No key is needed for real zoning (Apicarto/IGN), geocoding (BAN), comparables (DVF), or 3D
rendering — all of these sources are free and require no authentication.

## Known failure modes and how to recognize them

### A rebuilt service doesn't pick up a shared contract change

**Symptom**: a field added to `shared/dealpilot_shared/` (e.g. a new Pydantic field) seems ignored
by a service, with no error.

**Cause**: that service hasn't been rebuilt since the change — its copy of the shared package is
stale.

**Fix**:
```
docker compose build <affected-service>
docker compose up -d --force-recreate <affected-service>
```
Verify the new field is actually present:
```
docker run --rm --entrypoint /app/.venv/bin/python dealpilot-ai-<service> \
  -c "from dealpilot_shared import LandConstraints; print(list(LandConstraints.model_fields.keys()))"
```
**General rule**: after any change in `shared/`, rebuild *every* service that uses it (in practice:
all of them), not just the one you're directly editing.

### `docker compose build` fails with `docker-credential-desktop: executable file not found`

**Cause**: Docker Desktop sometimes regenerates `credsStore: "desktop"` in
`~/.docker/config.json`, which references a cloud auth helper not needed for public images.

**Fix**: remove the `"credsStore": "desktop",` line from `~/.docker/config.json`, then re-run the
build.

**Pitfall**: this error can happen silently in the middle of a pipe (`docker compose build X |
tail -N`), which hides the real exit code. Always check `docker compose build`'s actual exit code,
not just the absence of visible output.

### Insufficient WSL2/Docker Desktop memory (Windows)

**Symptom**: builds or GPU generations fail or become extremely slow with no clear error message;
`vmmem` consumes the entire configured limit.

**Fix**:
1. Raise the limit in `%UserProfile%\.wslconfig`:
   ```
   [wsl2]
   memory=11GB
   ```
2. `wsl --shutdown` then restart Docker Desktop.
3. If the problem persists, close RAM-hungry applications on the host (the image-generation
   pipeline temporarily uses several GB while loading the model onto the GPU).

**Case encountered: every container crashes at once (exit code 255)**. Under critical host memory
pressure (observed: under 700MB free out of 16GB), Docker Desktop/WSL2 can abruptly kill every
container at once, unrelated to application code — only one container may survive (the one
recreated right before the incident). Check with `docker compose ps -a` (`STATUS` column, look for
`Exited (255)` on several services at once) then simply `docker compose up -d` to restart
everything — no data loss (every service is stateless, only the SQLite deal history persists).
Check free memory before starting a heavy build or generation:
`wmic OS get FreePhysicalMemory,TotalVisibleMemorySize`.

### Interior/garden rendering abnormally slow (several minutes) or timing out on the frontend

**Symptom encountered**: the frontend shows `500 Server Error ... /land/interior` while the image
still finishes generating server-side (visible in the `interior-render` logs well after the HTTP
timeout expired).

**Root cause found and fixed**: SDXL's default VAE produces artifacts in float16, so `diffusers`
automatically upcasts it to float32 at final decode time. On an 8GB GPU already nearly full from
the rest of the float16 pipeline, that upcast overflows dedicated VRAM; the driver then falls back
to a very slow memory swap instead of crashing — the diffusion loop (30 steps) only took ~25s, but
the final decode pushed total time to ~295s, well past the configured timeouts (120s orchestrator,
150s frontend).

**Fix applied** (`services/interior-render/app/generator.py`): replaced the default VAE with
`madebyollin/sdxl-vae-fp16-fix`, a community VAE retrained to work correctly in float16 without
ever triggering that upcast. Generation time measured after the fix: ~45s end to end (confirmed
through the orchestrator, not just directly).

**Related pitfall**: the very first call after this fix downloads this new VAE (~330MB) from
Hugging Face, which can again take several minutes on a slow network (see below) — a one-time cost
only, cached in the `hf_cache` volume afterward.

### First call to interior/garden rendering is slow

**Normal**: the Stable Diffusion XL model (~7GB) downloads on the first call and is cached in a
Docker volume (`hf_cache`). Subsequent calls are fast (~45s/image, model already loaded in GPU
memory). Check the real state via:
```
curl http://localhost:8022/health
```
`{"status": "ok", "model_loaded": false}` means the process is running but the model isn't loaded
yet — the first generation will take a while.

### Abnormally slow Hugging Face download

**Cause encountered**: Hugging Face's accelerated `hf-xet` protocol can be throttled to near-zero
on some networks. The `interior-render` service explicitly uninstalls it at build time (see its
`Dockerfile`) to force a plain HTTP download, noticeably faster in this specific case.

### A Groq or Gemini model returns a 404 "model does not exist" error

**Cause**: Groq and Gemini models get deprecated regularly. Hit several times during this sprint
(`llama-3.3-70b-versatile`, `gemini-2.0-flash`, `gemini-2.5-flash`).

**Fix**: update `GROQ_MODEL` or `GEMINI_MODEL` in `.env` to an active model (check
`https://console.groq.com/docs/models` or the Gemini documentation), then rebuild the affected
services (`document-intel`, `location-intel`, `design-agent`, `summary` for Groq; `vision` for
Gemini).

### Two interior/garden image generations launched at the same time

**Expected behavior**: the second one waits its turn (a single GPU, explicit locking in
`services/interior-render/app/generator.py`). Verifiable in the logs: `"GPU busy, request for
<room> queued behind the current generation"`. This is not a failure.

## Observability

Every request is logged with a correlation ID (`deal_id` for a deal, otherwise a per-request
generated ID) propagated as the `X-Correlation-ID` header across every service. To trace a deal's
full path through the logs:
```
docker compose logs | grep <deal_id>
```

## Tests

Each service has its own test suite, runnable with no dependency on other services:
```
docker run --rm --entrypoint uv dealpilot-ai-<service> run pytest -q
```
For end-to-end evaluation on synthetic cases (requires the stack running):
```
py eval/run_eval.py
```
Regenerates `docs/eval_results.md` with real results.
