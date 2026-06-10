# Architecture

## Identity
Watchpoint — AI failure forensics for physical AI.
"When your robot fails in the field, we tell you why — at the AI layer, not just the logs."
Captures system-level telemetry + model-level introspection, generates replayable bundles with AI root-cause analysis.

---

## Repository layout

```
apps/api/                   FastAPI backend (Python 3.11)
apps/web/                   Next.js 16 frontend (TypeScript)
agents/edge-agent/          Go — system metrics collector (CPU/disk/net stubs)
agents/ros2-collector/      Python — ROS2 topic/node monitor (simulation mode)
agents/claude.md            Claude-specific usage rules
agents/codex.md             Codex-specific usage rules
packages/sample-data/       Seed script + JSON fixtures
packages/shared-types/src/  Shared TS types (thin, not fully wired)
deploy/docker-compose/      Local dev stack (postgres + api + web)
.ai/                        AI engineering context — READ BEFORE CODING
docs/                       Empty
```

---

## Data flow

```
Edge devices (Jetson / Linux / simulation)
  agents/edge-agent        Go    → POST /api/v1/ingest/metrics  {metrics:[...]}
  agents/ros2-collector    Python → POST /api/v1/ingest/metrics + /ingest/logs

apps/api (FastAPI + SQLAlchemy 2.0 async + asyncpg + Postgres)
  /ingest/*                → writes MetricPoint / EventLog rows (X-Device-Token required)
  /incidents/{id}/analyze  → 7 rules engine → optional Claude Haiku 2-sentence summary
  /incidents/{id}/replay-bundle → ZIP: metadata + events + metrics + deployment + analysis

apps/web (Next.js 16 + shadcn/ui v5)
  /dashboard               → devices + incidents overview
  /incidents/[id]          → full incident case file
  /login                   → JWT auth (localStorage — XSS risk, MVP acceptable)
```

---

## Backend: apps/api

**Entry:** `apps/api/app/main.py`
- Lifespan: `Base.metadata.create_all()` on startup — **Alembic exists (`0001_initial`, `0002_ai_layer`, `0003_device_api_tokens`), but runtime still relies on `create_all`**
- CORS: comma-split `settings.cors_origins`
- All routes at `/api/v1`

**Full route table:**

| Method | Path | Notes |
|--------|------|-------|
| GET | /health | {status, version} |
| POST | /auth/register | email+password+name → JWT |
| POST | /auth/login | email+password → JWT |
| GET | /auth/me | Bearer required |
| POST | /devices/register | project_id, device_name, hardware_model, os_version, agent_version → returns device token |
| GET | /devices/ | ?project_id= |
| GET | /devices/{id} | |
| POST | /devices/heartbeat/{id} | X-Device-Token required; sets status=online, updates last_seen_at |
| POST | /devices/deployments | version + metadata_json |
| POST | /incidents/ | project_id, device_id, deployment_id?, title, severity, trigger_type |
| GET | /incidents/ | ?project_id, device_id, status, limit=50, offset=0 |
| GET | /incidents/{id} | detail + event/metric counts |
| GET | /incidents/{id}/events | ?limit=500 |
| GET | /incidents/{id}/metrics | ?limit=5000 |
| POST | /incidents/{id}/analyze | runs 7 rules + optional LLM summary |
| POST | /incidents/{id}/replay-bundle | generates ZIP |
| GET | /projects/{id} | |
| GET | /projects/{id}/summary | {total_devices, online_devices, total_incidents} |
| POST | /ingest/logs | {logs:[...]} + X-Device-Token |
| POST | /ingest/metrics | {metrics:[...]} + X-Device-Token |
| POST | /ingest/events | {events:[...]} + X-Device-Token |
| POST | /ingest/model-runs | + X-Device-Token |
| POST | /ingest/inferences | + X-Device-Token |
| POST | /ingest/decisions | + X-Device-Token |
| POST | /seed/demo | creates demo@watchpoint.ai / demo123 + 3 devices + 3 incidents |
| GET | /bundles/{incident_id} | FileResponse — ZIP download from storage/bundles/ |

**Models (all use UUIDMixin + TimestampMixin, timezone-aware datetimes):**

| Model | Table | Key fields |
|-------|-------|-----------|
| User | users | email(unique), name, password_hash, is_active |
| Workspace | workspaces | name, slug(unique), owner_id→users |
| Project | projects | name, slug, workspace_id→workspaces |
| Device | devices | project_id, device_name, api_token_hash(nullable), hardware_model, os_version, agent_version, status(enum), last_seen_at |
| Deployment | deployments | device_id, version, deployed_at, metadata_json(JSONB) |
| Incident | incidents | project_id, device_id, deployment_id(nullable), title, severity(enum), status(enum), trigger_type, root_cause_summary(Text), analysis_json(JSONB), started_at, resolved_at(nullable) |
| IncidentArtifact | incident_artifacts | incident_id, artifact_type(enum), file_path, size_bytes |
| EventLog | event_logs | device_id(idx), incident_id(nullable,idx), timestamp(idx), level(enum), source, message(Text), metadata_json(JSONB) |
| MetricPoint | metric_points | device_id(idx), incident_id(nullable,idx), timestamp(idx), metric_name(idx), value(float), unit, labels_json(JSONB) |
| Annotation | annotations | incident_id, user_id(nullable), content(Text), annotation_type |

**Enums:** Severity(critical/high/medium/low) · IncidentStatus(open/investigating/resolved) · DeviceStatus(online/offline/unknown) · LogLevel(debug/info/warn/error/fatal) · ArtifactType(log_bundle/metrics_bundle/replay_bundle/ros2_snapshot)

**Config (`apps/api/app/config.py`):**

| Setting | Default | Notes |
|---------|---------|-------|
| database_url | postgresql+asyncpg://watchpoint:watchpoint@localhost:5432/watchpoint | auto-normalized |
| cors_origins | http://localhost:3000 | comma-separated |
| storage_path | ./storage | replay bundle root |
| jwt_secret_key | watchpoint-dev-secret-change-in-production | env var in prod |
| jwt_expiration_minutes | 60 | |
| anthropic_api_key | "" | optional — LLM disabled if empty |

`normalize_postgres_url()`: auto-rewrites `postgres://` and `postgresql://` → `postgresql+asyncpg://`, strips `?sslmode=require`. Handles Supabase/Render/Heroku URIs transparently.

**Auth:** python-jose (JWT, HS256). Passwords: `import bcrypt` directly — NOT passlib (incompatible with bcrypt 4.x on Python 3.11).

**Analysis engine (`app/services/analysis.py`):**

| # | Rule | Trigger | Confidence |
|---|------|---------|------------|
| 1 | Resource contention | cpu_percent > 85 AND topic_rate_hz < 5 | 0.85 |
| 2 | Version regression | deployment/version keywords AND regression/abort keywords | 0.82 |
| 3 | Thermal throttling | temp > 75°C AND inference_latency_ms > 100 | 0.80 |
| 4 | Process failure chain | crash/exit events AND watchdog/timeout events | 0.75 |
| 5 | Mission abort | abort/e-stop events | evidence only |
| 6 | Latency degradation | latency > 50ms AND 2× increase, no thermal | evidence only |
| 7 | Error spike | error/fatal logs > 3 | evidence only |

After rules: `generate_llm_summary()` — model=claude-haiku-4-5, max_tokens=80, ~120 input tokens. Fallback to rules text if `ANTHROPIC_API_KEY` empty.

**Replay bundle (`app/services/replay_bundle.py`):**
ZIP at `{storage_path}/bundles/watchpoint-replay-{incident_id}.zip`:
- `metadata.json` · `events.json` · `metrics.json` · `deployment.json` · `analysis_summary.txt`
- `ros2_snapshot.json` — **placeholder, not populated**

---

## Frontend: apps/web

Next.js 16 app router + TypeScript + Tailwind + shadcn/ui v5 (base-ui).

**Critical:** shadcn v5 has **no `asChild` prop** on Button. Pattern: `<Link className={cn(buttonVariants({...}))}>`.

**Pages:** `/` (redirect) · `/login` · `/dashboard` · `/devices/[id]` · `/incidents/[id]`

**Auth:** JWT in `localStorage` (keys: `watchpoint_token`, `watchpoint_user`). `apiFetch()` auto-injects Bearer. 401 → clear + redirect to /login.

**API base:** `NEXT_PUBLIC_API_URL` env var — baked in at build time.

---

## Edge agents

**edge-agent (Go):** CLI: `--api-url`, `--device-id`, `--device-name`, `--project-id`, `--interval`
- Sends: `POST /devices/register` → `POST /ingest/metrics` loop → `POST /devices/heartbeat`
- Health endpoint on `:8081`
- ⚠️ CPU/disk/network: **simulated stubs** — only memory is real
- Uses the `device_token` returned from registration for subsequent API calls

**model-collector (Python):** Hooks PyTorch forward passes and can send `X-Device-Token` via `WP_DEVICE_TOKEN`.

**ros2-collector (Python):** Collects topic_rate_hz, ros2_node_count, ros2_topic_count. `--simulate` flag for non-ROS environments.

---

## Production stack

| Layer | Service | Status | Notes |
|-------|---------|--------|-------|
| Frontend | Vercel | ✅ Live | https://watchpoint.vercel.app — production API wiring still needs confirmation |
| API | Render (free) | ⚠️ Config ready | `apps/api/render.yaml` exists; live deploy not verified in this review |
| Database | Supabase (free) | ⚠️ Planned | production project/URL not verified in this review |

---

## Local dev

```bash
cd deploy/docker-compose
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
# postgres:5432  api:8000  web:3000
curl -X POST http://localhost:8000/api/v1/seed/demo
open http://localhost:3000      # demo@watchpoint.ai / demo123
open http://localhost:8000/docs # Swagger
```

**Tool paths (macOS arm64):**
```
docker:   /Applications/Docker.app/Contents/Resources/bin/docker
uv:       /Users/sagarpatel/.local/bin/uv
graphify: /Users/sagarpatel/.local/bin/uv tool run --from graphifyy graphify
bun:      /Users/sagarpatel/.bun/bin/bun
```
