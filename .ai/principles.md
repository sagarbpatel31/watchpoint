# Engineering Principles

Rules for this codebase derived from its architecture and the decisions already made.

---

## 1. Incident case file > dashboard

The core product is the **incident case file**: full investigative record with timeline, correlated telemetry, root cause, and replay bundle. Not charts. Not status boards.

Every new feature must answer: *does this help an engineer understand what failed and why?*

## 2. Rules first, LLM last

Deterministic rules run before any LLM call. The LLM only synthesizes structured rule output into human prose — it does not reason, infer from raw data, or replace logic.

LLM features are always opt-in via `ANTHROPIC_API_KEY`. The system must be fully functional without it.

## 3. Graceful degradation at every external boundary

| Dependency | Fallback |
|-----------|---------|
| `ANTHROPIC_API_KEY` missing | Return rules-based text summary |
| DB unreachable | FastAPI lifespan fails with clear error |
| Agent not running | Incidents still creatable manually |
| Supabase paused | App shows connection error, no data corruption |

## 4. Token budget discipline (for all LLM calls)

- Always set `max_tokens` — never unbounded
- Cap structured inputs (e.g., `evidence_signals[:4]`)
- Use Haiku unless the task requires multi-step reasoning
- Prompt ends with output constraint: `"Terse. No preamble."`
- Every new LLM call needs a non-LLM fallback path
- Log `message.usage` in dev before shipping

## 5. Never add passlib

passlib is incompatible with bcrypt>=4.x on Python 3.11. Use `import bcrypt` directly. See `app/security.py` for the pattern.

## 6. Never use `asChild` on shadcn Button

This project uses shadcn/ui v5 (base-ui). `asChild` prop does not exist. Use `buttonVariants()` spread onto Link. See `decisions.md #5`.

## 7. Ingest payload format is always wrapped

Agents send `{metrics: [...]}` not `[...]`. All ingest route schemas expect a wrapper object. Never change this without updating all three agents.

## 8. Don't build outside the wedge

**In scope:** incident capture, telemetry correlation, root cause analysis, replay bundles, edge agent data collection.

**Out of scope:** fleet orchestration, teleoperation, OTA updates, digital twin, simulation, general DevOps tooling, real-time video.

## 9. JSONB for evolving structures

Use JSONB (`analysis_json`, `metadata_json`, `labels_json`) for fields whose schema is still stabilizing. Normalize into proper columns only when the shape is proven stable.

## 10. Migrations before any schema change on live data

`alembic/` now has migration files (`0001_initial`, `0002_ai_layer`, `0003_device_api_tokens`). Before production schema changes, use Alembic revisions and upgrades as the source of truth. `create_all` may remain acceptable for dev bootstrap, but it should not be the production migration strategy.

## 11. Monorepo service boundaries via HTTP only

Agents in `agents/` communicate with the API via HTTP — never direct DB access. Apps in `apps/` never import from each other. `packages/` can be imported by any `apps/` service.

## 12. Secrets only via environment variables

`JWT_SECRET_KEY` and `ANTHROPIC_API_KEY` come from env vars only. Never hardcode. The defaults in `config.py` are clearly labelled placeholders for local dev only.
