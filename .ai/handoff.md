# Handoff

Single source of truth for resuming work after any context break.
Last updated: 2026-06-10.

---

## Project

- **Name:** Watchpoint — incident intelligence for ROS2 and edge AI robots
- **Repo:** https://github.com/sagarbpatel31/watchpoint (public)
- **Frontend:** https://watchpoint.vercel.app (live, not yet wired to prod API)

---

## Priority order (do not change this)

| # | Task | Status |
|---|------|--------|
| **P1** | Deploy frontend + backend + database end-to-end | ❌ Blocked on user signups |
| **P2** | Switch production workflow to migration-first | ⚠️ Partial — Alembic files exist, runtime still uses `create_all` |
| **P3** | Secure ingest endpoints | ✅ Implemented in source; deploy verification still needed |
| **P4** | Replace simulated edge agent metrics with real collectors | ⚠️ Partial — project ID configurable, metrics still simulated |
| **P5** | Switch JWT from localStorage to httpOnly cookie | ❌ Not started |

**Do not start P3–P5 before P1 is complete.** P2 should happen immediately after first production deploy — before the next schema change.

---

## P1 deploy — exact steps

User provides two URLs, Claude does the rest.

**User actions:**
1. Sign up Supabase → New project (US East) → Settings → DB → URI → paste here
2. Sign up Render → New → Blueprint → connect `sagarbpatel31/watchpoint` → set `DATABASE_URL` → copy deploy URL → paste here

**Claude actions (after URLs provided):**
```bash
# Wire Vercel
cd apps/web
vercel env add NEXT_PUBLIC_API_URL production  # value: Render deploy URL
vercel --prod

# Seed
curl -X POST https://watchpoint-api.onrender.com/api/v1/seed/demo

# Verify
curl https://watchpoint-api.onrender.com/api/v1/health
# → open https://watchpoint.vercel.app → demo@watchpoint.ai / demo123
```

---

## Current branch state

| Branch | Status |
|--------|--------|
| `main` | Active checkout during this audit |
| Repo status | MVP + AI layer + model-collector + device-token auth + Alembic migrations present in source |

---

## What works right now (locally)

```bash
cd deploy/docker-compose
/Applications/Docker.app/Contents/Resources/bin/docker compose up -d
curl -X POST http://localhost:8000/api/v1/seed/demo
open http://localhost:3000   # demo@watchpoint.ai / demo123
open http://localhost:8000/docs
```

---

## Critical rules (non-negotiable)

| Rule | Detail |
|------|--------|
| No passlib | Use `import bcrypt` directly — incompatible with bcrypt 4.x / Python 3.11 |
| No `asChild` on Button | shadcn v5 doesn't have it — use `buttonVariants()` spread on Link |
| Ingest format: wrapped | `{metrics:[...]}` not `[...]` |
| LLM fallback required | System must function without `ANTHROPIC_API_KEY` |
| URL normalization | `config.py` handles cloud URIs automatically — never manually edit |
| Alembic before schema changes | Migrations now exist; future schema changes should land as Alembic revisions, not model-only edits |

---

## Env vars for production

| Var | Source | Destination |
|-----|--------|-------------|
| `DATABASE_URL` | Supabase → Settings → DB → URI | Render env vars |
| `JWT_SECRET_KEY` | Auto-generated | render.yaml: `generateValue: true` |
| `ANTHROPIC_API_KEY` | console.anthropic.com (optional) | Render env vars |
| `NEXT_PUBLIC_API_URL` | Render deploy URL | Vercel env vars |

---

## Key file map

```
apps/api/app/main.py                    FastAPI app, lifespan, router mounts
apps/api/app/config.py                  All settings + URL normalization
apps/api/app/security.py               JWT + bcrypt auth
apps/api/app/services/analysis.py      7 rules engine + Haiku LLM summary
apps/api/app/services/replay_bundle.py ZIP bundle generation
apps/api/app/device_tokens.py         Device token hashing + auth helpers
apps/api/app/routers/ingest.py         Authenticated telemetry ingest
apps/api/app/routers/ai_ingest.py      Authenticated AI-layer ingest/query endpoints
apps/api/alembic/versions/             0001_initial + 0002_ai_layer + 0003_device_api_tokens
apps/web/src/lib/api-client.ts         Typed HTTP client with JWT injection
apps/web/src/lib/auth.ts               Token storage in localStorage (P5 target)
apps/web/src/types/index.ts            All TypeScript interfaces
agents/edge-agent/internal/collector/system.go  Simulated metrics (P4 target)
agents/edge-agent/internal/sender/http.go       Token-aware sender + configurable project ID
agents/model-collector/                Python model instrumentation package + tests
```

---

## Tool paths (macOS arm64)

```bash
docker:   /Applications/Docker.app/Contents/Resources/bin/docker
uv:       /Users/sagarpatel/.local/bin/uv
graphify: /Users/sagarpatel/.local/bin/uv tool run --from graphifyy graphify
bun:      /Users/sagarpatel/.bun/bin/bun
```
