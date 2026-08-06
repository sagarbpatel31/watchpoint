# Changelog

All notable changes to Watchpoint are documented here.
Format: [Conventional Commits](https://www.conventionalcommits.org/).

---

## [0.4.0] — API authentication and migration-first deploys (2026-08-06)

### Security

- **The API was almost entirely unauthenticated.** `GET /auth/me` was the only
  route that consumed a JWT. `GET /incidents`, `GET /devices`,
  `POST /devices/register`, `POST /devices/deployments`, `GET /projects/{id}`,
  `GET /bundles/{id}`, every `/ingest/*` route, and `POST /seed/demo` all served
  anonymous callers. Login issued valid tokens that nothing checked.
  - All human-facing routes now require a JWT via router-level
    `Depends(require_current_user)`.
  - `health`, `auth/register`, and `auth/login` stay public by design.
- **Device tokens for embedded agents** (`X-Device-Token`). Agents are headless
  and long-lived, so they authenticate with a scoped credential rather than a
  JWT. Stored as SHA-256 — deliberately not bcrypt, which is right for
  low-entropy passwords but would put ~100ms on the ingest hot path for a
  credential that is already 32 random bytes.
  - A token may only write for the device it was issued to. A payload naming a
    different device is rejected with 403 — otherwise one robot's credential
    could corrupt another's baselines, which is exactly what AI-001 and AI-003
    measure against.
  - Decisions carry no `device_id`, so they are scoped through the inference
    they reference.
  - New: `POST /devices/{id}/tokens`, `GET /devices/{id}/tokens`,
    `POST /devices/tokens/{id}/revoke` (soft revoke, preserves the audit trail).
- **`POST /seed/demo` is gated** on `ENABLE_DEMO_SEED`, default off, and returns
  404 rather than 403 so a production deployment does not advertise it.

### Fixed

- **Seeding is idempotent.** It used fixed primary keys with no upsert, so a
  second call errored on duplicate keys against live data. It now deletes the
  previous demo rows first, scoped strictly to the fixed demo IDs.
- **Model/migration drift in `0001_initial`** (`0004_align_unique_indexes`).
  `users.email` and `workspaces.slug` were created as a plain index plus a
  separate unique constraint, while the models declare a single unique index.
  Uniqueness was always enforced, so this was never a data-integrity bug — but
  it left `alembic check` permanently red, which hides real drift. Now clean.

### Changed

- **Migration-first.** `alembic upgrade head` runs before uvicorn binds
  (Dockerfile and docker-compose); `Base.metadata.create_all()` is gone from the
  app lifespan. The two existing migrations had never actually been applied to
  anything — `create_all` was doing the work.
- `make lint-api` now covers `tests/` as well as `app/`.

### Added

- `.github/workflows/ci.yml` — the repo had no CI at all. Five parallel jobs:
  api, migrations, model-collector, web, edge-agent. The migrations job runs
  against a real Postgres and asserts `alembic check` is clean plus a full
  downgrade/upgrade round-trip, enforcing the repo's own "Alembic before schema
  changes" rule.
- `apps/api/tests/conftest.py` — shared `mock_db`, `auth_client`,
  `device_client`, `anon_client` fixtures (the suite previously had no conftest).
- `test_auth_enforcement.py` — asserts every protected route 401s, and fails
  when a route is added without being classified, so a new router cannot ship
  unprotected by omission.
- `test_device_tokens.py`, `test_seed_gating.py`.
- API tests: 35 → 82.

### Known breakage

Collectors do not send `X-Device-Token` yet, so agent ingest returns 401 until
they are wired (`model_collector/sender.py`, `edge-agent/internal/sender/http.go`,
`ros2_collector/sender.py`, plus a configurable `project_id` for the Go agent).
The demo path is unaffected — it goes through the seed endpoint, not the
collectors — so the hosted demo and dashboard work fully. This is the next
change.

---

## [0.3.0] — Go-to-market foundation (2026-08-05)

### Changed
- **LICENSE is now Apache 2.0** (was the TraceMind Source-Available License).
  The previous license permitted "reference, evaluation, and educational
  purposes only" and forbade commercial use without written permission, which
  made the free self-hosted tier impossible and left design partners unable to
  legally run Watchpoint on a production fleet. It also still carried the old
  project name and a repository URL that no longer resolves. Rationale and the
  open-core boundary are documented in `docs/gtm/licensing.md`.
- **Landing page repositioned** (`apps/web/src/app/page.tsx`) from generic
  incident monitoring to the AI-layer wedge — what the model saw, predicted,
  decided, and whether the input was out of distribution.
  - Removed unsubstantiated metrics ("10K+ incidents captured", "73% MTTR
    reduction", "5+ supported platforms") — no evidence exists for any of them.
  - Removed the non-existent `watchpoint.ai/install.sh` install command in
    favour of the real clone-and-compose quickstart.
  - Every roadmap capability is now labelled as roadmap; only AI-001/002/003 are
    marked shipped.
- **Makefile is portable.** Tool paths resolved from `PATH` with macOS fallbacks
  and per-invocation overrides (`make test UV=...`), so `make test` / `make lint`
  run on Linux and in CI instead of only on one laptop.

### Added
- `apps/web/src/app/pricing/page.tsx` — Community / Team / Enterprise tiers,
  design-partner offer, honest "hosted cloud is not built yet" section.
- `docs/gtm/positioning.md` — canonical positioning, ICP, competitive analysis,
  objection handling, and the claim-discipline rules the site copy follows.
- `docs/gtm/licensing.md` — the Apache 2.0 decision and open-core boundary.
- `docs/gtm/yc-application.md` — YC application draft; founder-specific answers
  are marked `[SAGAR]` rather than invented.
- `docs/gtm/design-partners.md` — qualification criteria, outreach templates,
  discovery script, onboarding plan, and design-partner agreement terms.
- `docs/gtm/blog/01-eight-silent-ai-failures.md` — launch post covering
  AI-001…AI-008.
- Makefile targets `typecheck-web`, `build-web`, `check`, and `tools`.

### Fixed
- Landing page and pricing page lost the space after an inline `<span>`
  ("shippedrun today", "roadmapare specified"); now explicit `{" "}`.

### Known gaps (unchanged by this release)
- Ingest endpoints remain unauthenticated — partners must not run a
  network-exposed instance until device tokens ship.
- Rules AI-004…AI-008, the replay sandbox, and the Grad-CAM endpoint are
  specified but not merged.

---

## [0.2.0] — Week 2+3 YC Sprint (2026-05-04)

### Added
- **AI layer seed data** — `POST /seed/demo` now seeds 3 ModelRuns + 65 inference frames + 3 OODSignals
  - Incident 01 (CPU contention): 30 frames, confidence 0.93→0.41 (46.9% drop), 2 OOD signals
  - Incident 02 (thermal throttle): 25 frames, confidence 0.91→0.49 (36.9% drop), 1 OOD signal
  - Incident 03 (version regression): 10 frames, confidence stable 0.87→0.83, no OOD (AI rules intentionally silent)
- **AI-001** — Perception confidence collapse rule: fires when p50 confidence drops >30% first→second half
- **AI-002** — OOD input detected rule: fires on any `OODSignal.is_ood=True` linked to incident
- **AI-003** — Inference latency spike rule: fires when p99 latency in second half >2× first half
- **AI query endpoints**: `GET /api/v1/incidents/{id}/inferences`, `GET /api/v1/inferences/{id}`, `GET /api/v1/inferences/{id}/attention`
- **InferenceTimeline component**: dual-axis Recharts chart (confidence left, latency_ms right); per-frame table with links to detail page
- **Inference detail page** (`/inferences/[id]`): capture metadata, output stats, attention status
- **Inferences tab** on incident detail page (Brain icon, frame count badge)
- **AI rule badges** in analysis probable-causes panel: violet `AI-xxx` pill on AI-layer findings
- **Confidence bar** in probable-causes: color-coded red/yellow/green with percentage
- **Dashboard "AI Anomalies" stat**: counts incidents with AI-layer rule findings (replaces "Active Incidents")
- **Dashboard AI anomaly badge**: violet "AI anomaly" tag on incident table rows
- **Loading skeletons**: pulse skeleton layouts on incident detail + dashboard panels (replaces plain text)
- **InferenceTimeline empty state**: Brain icon + model-collector CTA (replaces plain text)
- `apps/web/src/types/ai_layer.ts` — `Inference`, `ModelRun`, `Decision`, `OODSignal`, `AttentionResponse`, `ReplayJob` TS types
- `AnalysisResult.probable_causes` gains optional `rule_id` field
- 13 new API tests (test_ai_query.py, test_ai_rules.py extended); all 35 passing

### Changed
- `apps/api/app/services/analysis.py` — `_AI_RULES` list now includes AI-001, AI-002, AI-003
- `_mock_db` in `test_analysis_rules.py` supplies 5 `db.execute` side effects (3 AI rule calls)

---

## [Unreleased] — Week 1 (2026-05-01)

### Added
- `agents/model-collector/` — new Python package for AI inference capture
  - `RingBuffer`: thread-safe fixed-size deque, O(1) append + snapshot
  - `CollectorConfig`: all tunables, reads from environment variables
  - `writer.py`: flush frames to `{flush_path}/{incident_id}/run_{ts}.msgpack` (msgpack + numpy serialization)
  - `Collector`: central coordinator — ring buffer, flush interface
  - `adapters/pytorch_adapter.py`: `register_forward_hook` based capture; records layer name, input/output shapes, mean/std, top-1 confidence, input hash, timestamp_ns
  - `sender.py`: HTTP flush to `/ingest/model-runs` + `/ingest/inferences`
  - `scripts/demo_hook.py`: ResNet-18 hook demo — 5 forward passes, flush to disk
  - 16 tests, all passing
- `apps/api/alembic/` — Alembic migration infrastructure initialized
  - `alembic.ini`, `env.py` (async engine), `script.py.mako`
  - `0001_initial.py`: DDL for all 10 existing tables
  - `0002_ai_layer.py`: DDL for `model_runs`, `inferences`, `decisions`, `ood_signals`
- `apps/api/app/models/ai_layer.py` — `ModelRun`, `Inference`, `Decision`, `OODSignal` SQLAlchemy models
- `apps/api/app/routers/ai_ingest.py` — unauthenticated AI layer ingest endpoints:
  - `POST /api/v1/ingest/model-runs`
  - `POST /api/v1/ingest/inferences` (batch)
  - `POST /api/v1/ingest/decisions` (batch)
- `apps/api/app/schemas/ai_layer.py` — Pydantic v2 schemas for all AI layer endpoints
- `Makefile` — root-level `make dev`, `make test`, `make lint`, `make seed`, `make clean`
- `CHANGELOG.md` — this file

### Changed
- **Renamed TraceMind → Watchpoint** across all source, configs, docs, and `.ai/` context files (35 files)
- `CLAUDE.md` — replaced with full engineering spec; added Session rules section
- `apps/api/pyproject.toml` — package name `watchpoint-api`
- `apps/api/app/main.py` — API title + bundle path prefix
- `apps/api/app/services/replay_bundle.py` — ZIP prefix `watchpoint-replay-`
- `apps/api/app/config.py` — default DB URL + JWT secret key prefix
- `apps/api/app/routers/seed.py` — demo email `demo@watchpoint.ai`, workspace slug `watchpoint-demo`
- `agents/edge-agent/go.mod` — module path `github.com/watchpoint/edge-agent`
- `deploy/docker-compose/docker-compose.yml` — Postgres user/db `watchpoint`
- `apps/web/src/lib/auth.ts` — localStorage keys `watchpoint_token` / `watchpoint_user`
- `apps/web/src/app/layout.tsx` — page title updated
- Git remote updated to `https://github.com/sagarbpatel31/watchpoint.git`

---

## [0.1.0] — MVP (2026-04-25)

### Added
- FastAPI backend: JWT auth, devices, incidents, ingest, 7-rule RCA engine, Claude Haiku LLM summary, replay ZIP bundles
- Next.js 16 frontend: dashboard, login, incident detail, device detail
- Go edge agent: system metrics collector (CPU/disk/net stubs), cross-compile Linux/ARM
- Python ROS2 collector: topic rates, node health, simulation mode
- Docker Compose local dev stack
- 3 demo scenarios: CPU contention, thermal throttling, version regression
- `.ai/` context layer: 9 engineering reference files
