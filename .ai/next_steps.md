# Next Steps

Last updated: 2026-08-06.

**The priority order below was revised.** It previously put the production
deploy first and security third. That was wrong for a specific, verifiable
reason: `GET /auth/me` was the only authenticated route in the whole API, so
deploying first would have published a fully open database. P2 and P3 are now
done; P1 is unblocked and safe to run.

## 🔴 Priority 1 (new) — Wire device tokens through the collectors

Ingest now requires `X-Device-Token`. None of the collectors send it, so agent
ingest returns 401 until this lands. **A design partner cannot send data before
this is done.**

- `agents/model-collector/model_collector/sender.py` — thread an optional token through `send_model_run` / `send_inferences`
- `agents/ros2-collector/ros2_collector/sender.py` — same
- `agents/edge-agent/internal/sender/http.go` — add the header, and make `project_id` configurable instead of the hardcoded `demoProjectID`

The demo path (seeded data) is unaffected, so the hosted demo and dashboard keep
working meanwhile.

## 🔴 Priority 2 — End-to-end production deploy

Unchanged and still blocked on account provisioning (Supabase + Render). Now
safe to run: the API authenticates, the container migrates before it binds, and
`ENABLE_DEMO_SEED` defaults off. Steps are in `DEPLOY.md` (Step 4b covers token
provisioning).

## ✅ Done — was P2 (migration-first)

`alembic upgrade head` runs before uvicorn in both the Dockerfile and
docker-compose; `create_all` is gone from the app lifespan. CI enforces
`alembic check` against a real Postgres on every PR.

## ✅ Done — was P3 (secure ingest), widened to the whole API

JWT on all human routes, device tokens on all agent routes, seed gated behind
`ENABLE_DEMO_SEED`, and a regression test that fails when a new route is added
without an auth decision.

---

## 🟡 Priority 3 — Replace edge-agent stubs with real telemetry

Files:
- `agents/edge-agent/internal/collector/system.go`
- `agents/edge-agent/internal/sender/http.go`

Required changes:
- Replace simulated CPU/disk/network with real collection
- Make `project_id` configurable instead of hard-coded
- Validate behavior on Linux/Jetson target environment

Do not deploy the current Go agent to real hardware expecting trustworthy RCA inputs.

---

## 🟡 Priority 4 — Harden frontend auth storage

File:
- `apps/web/src/lib/auth.ts`

Current state:
- JWT stored in `localStorage`

Recommended fix:
- Move to `httpOnly`, `Secure`, `SameSite=Strict` cookies
- Add a server-side relay or middleware pattern in Next.js as needed

This matters, but it is still behind the priorities above.

---

## Supporting cleanup

These are not the top production blockers, but they should be fixed soon:

- Recreate stale checked-in `.venv` environments whose shebangs still reference the old pre-rename repo path
- Populate `ros2_snapshot.json` instead of shipping a placeholder in replay bundles
- Scope queries by workspace. Auth is now enforced, but any authenticated user
  still sees every workspace's data. Not reachable by an outsider on a
  single-tenant self-hosted install; required before any hosted offering.
