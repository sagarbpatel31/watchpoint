# Current Task

Last updated: 2026-08-05.

## Active branch

`claude/project-startup-planning-ub8jwb`.

---

## 2026-08-05 — GTM foundation track (complete)

Product priorities P1–P5 below are unchanged. This session ran the
go-to-market track in parallel, because P1 is blocked on user-side account
signups rather than on code.

**Landed:**

| Change | Where |
|--------|-------|
| LICENSE relicensed to Apache 2.0 | `LICENSE`, rationale in `docs/gtm/licensing.md` |
| Landing page repositioned on the AI-layer wedge | `apps/web/src/app/page.tsx` |
| Pricing page added | `apps/web/src/app/pricing/page.tsx` |
| Positioning, YC draft, design-partner playbook, launch blog post | `docs/gtm/` |
| Makefile made portable (PATH-first, macOS fallback) | `Makefile` |
| TraceMind → Watchpoint rename completed | README, SECURITY.md, seed fixtures, package.json |

**Why the license changed:** the old TraceMind Source-Available License allowed
evaluation only and forbade commercial use without written permission. That made
the free self-hosted tier impossible and would have put every design partner in
violation the moment they deployed to a fleet. Apache 2.0 for the core, with
commercial features kept outside the tree.

**Open item for Sagar:** relicensing is only clean if you hold copyright on the
whole tree. If anyone else has contributed, get written sign-off before
publicising the change. Tracked in `docs/gtm/licensing.md` §Follow-up.

**Claim discipline is now a repo rule.** `docs/gtm/positioning.md` §10 governs
all customer-facing copy: no metric without evidence, roadmap always labelled as
roadmap. The previous landing page carried invented numbers (10K+ incidents, 73%
MTTR reduction) and a non-existent install URL; both are gone.

---

## Product state (unchanged from the 2026-05-31 audit)

This repo is no longer just the original MVP. The codebase now includes:
- Core incident intelligence backend + frontend
- AI-layer ingest/query endpoints and rules
- A Python `model-collector` package
- Alembic migration files `0001_initial` and `0002_ai_layer`

---

## Current product state

### ✅ Implemented in source

| Feature | Status | Files |
|---------|--------|-------|
| FastAPI backend — auth, devices, incidents, ingest, projects, seed | Implemented | `apps/api/app/routers/` |
| 7 classic incident-analysis rules + optional Haiku summary | Implemented | `apps/api/app/services/analysis.py` |
| Replay bundle ZIP export | Implemented | `apps/api/app/services/replay_bundle.py` |
| Next.js dashboard, login, device, incident, inference views | Implemented | `apps/web/src/app/` |
| AI-layer data model (model runs, inferences, decisions, OOD signals) | Implemented | `apps/api/app/models/ai_layer.py` |
| AI-layer ingest/query endpoints | Implemented | `apps/api/app/routers/ai_ingest.py` |
| AI-layer RCA rules AI-001, AI-002, AI-003 | Implemented | `apps/api/app/rca/ai_rules/` |
| Demo seed data including AI-layer frames | Implemented | `apps/api/app/routers/seed.py` |
| Go edge agent | Implemented, still partly stubbed | `agents/edge-agent/` |
| ROS2 collector | Implemented | `agents/ros2-collector/` |
| Python model-collector package + tests | Implemented | `agents/model-collector/` |
| Alembic setup + migration files | Implemented | `apps/api/alembic/versions/` |
| Render deployment config | Implemented | `apps/api/render.yaml` |

### ✅ Verified during this review

| Check | Result |
|------|--------|
| Frontend lint | Passed via `npm run lint` in `apps/web` |
| API tests exist | Present in `apps/api/tests/` |
| Model-collector tests exist | Present in `agents/model-collector/tests/` |

### ⚠️ Verification gaps found during this review

| Gap | Detail |
|-----|--------|
| Python test envs are stale | Checked-in `.venv` entrypoints still point at the old pre-rename repo path |
| Offline dependency resolution | Fresh `uv` runs cannot refill missing deps without network access |
| Production deploy not proven | No confirmed live Render API URL or wired Vercel production API base in this review |

---

## Production blocker audit

Priority order remains deployment first, then security/hardening.

### 🔴 P1 — End-to-end production deploy

**Status:** Still blocked on platform provisioning / final wiring, not on missing product code.

Blocking items:
- Supabase project + production `DATABASE_URL` not confirmed in repo/docs
- Render API deployment not confirmed live from this review
- Vercel `NEXT_PUBLIC_API_URL` wiring to production API not confirmed
- `apps/api/render.yaml` currently sets `CORS_ORIGINS` for `https://watchpoint-gray.vercel.app`, so the final production frontend domain must be confirmed and aligned
- Production seed + smoke test not confirmed

### 🟠 P2 — Migration discipline

**Status:** Partially complete.

What is true now:
- Alembic is initialized
- Migration files already exist: `0001_initial`, `0002_ai_layer`

What is still incomplete:
- Runtime still uses `Base.metadata.create_all()` on startup in `apps/api/app/main.py`
- Production process is not yet clearly documented as migration-first

### 🟠 P3 — Secure ingest endpoints

**Status:** Not started in code.

Current blocker:
- `/api/v1/ingest/logs`, `/metrics`, `/events` are still unauthenticated in `apps/api/app/routers/ingest.py`
- AI ingest endpoints in `apps/api/app/routers/ai_ingest.py` are also unauthenticated

### 🟡 P4 — Real edge telemetry

**Status:** Not started in code.

Current blocker:
- `agents/edge-agent/internal/collector/system.go` still simulates CPU/disk/network
- `agents/edge-agent/internal/sender/http.go` still hard-codes demo `project_id`

### 🟡 P5 — Web auth hardening

**Status:** Not started in code.

Current blocker:
- JWT remains in `localStorage` in `apps/web/src/lib/auth.ts`

---

## Known code issues still open

| Issue | Location | Impact |
|-------|----------|--------|
| Runtime still does `create_all` | `apps/api/app/main.py` | Easy to drift from migration-first production discipline |
| Ingest endpoints unauthenticated | `apps/api/app/routers/ingest.py`, `apps/api/app/routers/ai_ingest.py` | Telemetry injection risk |
| Edge agent collector stubs | `agents/edge-agent/internal/collector/system.go` | False positives on real hardware |
| Hard-coded demo project ID | `agents/edge-agent/internal/sender/http.go` | Real deployments all map to seed project |
| `ros2_snapshot.json` placeholder | `apps/api/app/services/replay_bundle.py` | Replay bundle incomplete |
| JWT in `localStorage` | `apps/web/src/lib/auth.ts` | XSS-extractable token |
| Checked-in `.venv` shebangs reference the pre-rename repo path | `apps/api/.venv/`, `agents/model-collector/.venv/` | Local test tooling breaks after repo rename; recreate with `uv sync --extra dev` |
