# Changelog

All notable changes to Watchpoint are documented here.
Format: [Conventional Commits](https://www.conventionalcommits.org/).

---

## [0.6.0] — The edge agent measures instead of guessing (2026-08-11)

The collectors delivered reliably as of 0.5.0, but the edge agent's numbers were
invented: `simulateCPU()` returned `15 + rand()*10`, memory and disk were
hardcoded constants, and network counters were literally `0 // placeholder`.
`DEPLOY.md` carried a warning not to show any of it to anyone as a measurement.

### Added

- **Real Linux telemetry.** CPU from `/proc/stat`, memory from `/proc/meminfo`,
  disk via `statfs`, network from `/proc/net/dev`, temperature from
  `/sys/class/thermal`. Stdlib only — `go.mod` still has zero dependencies.
- **`cpu_temp_c` and `gpu_temp_c` are now emitted.** No collector produced a
  temperature before, which meant the thermal-throttling rule — one of the seven,
  and the whole of demo scenario 2 — could not fire on real fleet data at all.
  Zones are matched by their `type` label, so Jetson's `CPU-therm`/`GPU-therm`
  and x86's `coretemp`/`acpitz` both resolve.
- **Network as rates**, `net_rx_bytes_per_sec` / `net_tx_bytes_per_sec`, rather
  than the raw since-boot counters an operator cannot reason about.
- **First Go tests in the repo**, covering the `/proc` formats against fixtures.
  CI now runs `go test`, a `gofmt` check, and cross-compiles all three shipping
  targets plus `darwin/arm64`.

### Fixed

- **Memory was the wrong quantity, not merely simulated.** `MemoryUsedBytes` was
  `runtime.MemStats.Sys` — the agent's own Go heap. It reported 6 MB used on a
  16 GB host and anyone reading it as system memory was being actively misled.
- **Disk percentage now matches `df`.** It is computed as `used / (used +
  available)`, not `used / total`. Filesystems reserve blocks that free space
  reports but no ordinary write can claim; on the volume this was verified
  against, 215 GiB of a 252 GiB device was unavailable, so `used/total` read 5%
  where `df` said 36% — and would still have read under 6% at the moment the
  last writable byte vanished, hiding a disk-full incident completely.
- **CI had never run once.** The workflow triggered only on push to `main` or on
  a pull request, but lived on a working branch with no PR open, so no trigger
  condition ever matched. Working branches are now included in the push trigger.

### Changed

- **`Collect()` is now a stateful `Sampler`.** CPU percentage and network rates
  are deltas between consecutive readings of counters that are cumulative since
  boot; a single sample cannot produce either.
- **Unmeasured values are omitted, never zeroed.** The first tick publishes no
  CPU or network figure, and hardware without thermal sensors publishes no
  temperature. The RCA rules cannot distinguish `0` from "unknown", and would
  read a missing sensor as a cold, idle machine.
- **Non-Linux platforms collect nothing** and say so once, instead of filling the
  gap with simulated values. A developer running the agent on macOS was
  previously shipping invented readings indistinguishable from a real robot's.

### Known gaps

- **Temperature is unvalidated on hardware.** The sandbox exposes no thermal
  zones, so the `/sys/class/thermal` walk is covered by fixtures only. Confirm on
  a Jetson before relying on `cpu_temp_c` in the field.
- **`inference_latency_ms` still has no producer**, so the thermal rule yields
  evidence but not a probable cause on real data. Tracked as the new P2 in
  `.ai/next_steps.md`.

---

## [0.5.0] — The collectors actually deliver data (2026-08-07)

The previous release put device tokens on ingest and knowingly left the
collectors unable to authenticate. Wiring the header through turned up that
**none of the three had ever successfully ingested** — the token was the newest
of several independent faults, not the only one.

### Fixed

- **`Collector.flush()` never transmitted anything.** It wrote msgpack to disk
  and returned; `send_model_run` and `send_inferences` had zero callers. It now
  uploads after the local write — disk first, because a backend that is
  unreachable during an incident is exactly when the capture matters. Upload
  failure is logged and swallowed: this runs inside the inference process, and
  taking down a robot's perception stack to report a telemetry error is worse
  than losing the telemetry.
- **ros2-collector posted the wrong envelope.** `send_logs` sent
  `{"events": [...]}` to `/ingest/logs`, which declares `logs` — a 422 on every
  cycle.
- **ros2-collector silently lost every topic label.** It sent `labels` and
  `metadata` where the schemas declare `labels_json` and `metadata_json`.
  Pydantic ignored the unknown keys, so ingest returned 200 and stored
  `topic_rate_hz` points with no record of *which topic* degraded. This is the
  one worth reading twice: it failed with a success status.
- **Inference timestamps used `time.monotonic_ns()`** — an arbitrary epoch that
  cannot be correlated with anything. Model state could never line up with
  system telemetry on the incident timeline, which is the product's core claim.
  Now `time.time_ns()`.
- **Auto-generated capture IDs were sent as `incident_id`**, a foreign key, so
  any capture not tied to a known incident failed with an FK violation. The
  local capture directory name and the incident reference are now separate.
- **An unknown `incident_id` returned 500.** Now 404, so a client can tell a bad
  reference from a server fault.
- Seeded `topic_rate_hz` metrics had no `labels_json` either, so the demo showed
  anonymous topic rates while its incident titles named specific topics.

### Changed

- **Device identity is derived from the token.** `device_id` is now optional on
  every ingest schema and filled from the authenticated device. Agents sent
  identifiers the API could never accept — the Go agent its hostname, the model
  collector the literal `"unknown-device"` — because they have no reliable way
  to know their own UUID. An agent now needs a backend URL and a token, nothing
  else. A payload that *does* name a device is still checked, so cross-device
  protection is unchanged.
- **Ingest schemas reject unknown fields** (`extra: forbid`). The `labels` bug
  was invisible precisely because extras were ignored; a field-name mistake is
  now a 422 at integration time instead of missing data found weeks later.
- edge-agent takes `-token` / `WP_DEVICE_TOKEN` and exits with a clear message
  without one. `demoProjectID` and agent self-registration are gone — that
  hardcoded constant put every real device in the demo project.
- ros2-collector takes `--token` / `WP_DEVICE_TOKEN` in place of the required
  `--device-id`, and sends explicit ISO-8601 UTC timestamps.

### Added

- `agents/ros2-collector/tests/` — the package had no tests. Asserts the wire
  format directly, which is the only way to catch a silent-drop bug without a
  live backend.
- model-collector flush/send tests; API tests for token attribution, foreign
  `device_id`, unknown fields, and the unknown-incident 404.
- CI job for ros2-collector; `make test-ros2-collector` / `lint-ros2-collector`.
- Collector tests are now linted alongside their source.
- Tests: 119 → 130.

### Verified live

Against a real Postgres and a running API, not mocks — the payload-shape bugs
above are invisible to mocked tests. All three collectors ingest successfully;
metrics land attributed to the token's device rather than a hostname;
`topic_rate_hz` rows carry `labels_json->>'topic'`; inference timestamps are
wall-clock. Negative paths confirmed: no token 401, revoked token 401, foreign
`device_id` 403, unknown field 422, unknown incident 404.

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
