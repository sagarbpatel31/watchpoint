# Next Steps

Last updated: 2026-08-06.

**The priority order below was revised.** It previously put the production
deploy first and security third. That was wrong for a specific, verifiable
reason: `GET /auth/me` was the only authenticated route in the whole API, so
deploying first would have published a fully open database. P2 and P3 are now
done; P1 is unblocked and safe to run.

## ✅ Done — was P1 (wire device tokens through the collectors)

All three collectors authenticate and deliver, verified against a live API.
Scope turned out to be larger than "add a header": none of them had ever
ingested successfully. `Collector.flush()` never called its sender at all, the
ros2 collector posted the wrong envelope and silently dropped every topic label,
and inference timestamps used a monotonic clock that could not be correlated
with anything. See CHANGELOG 0.5.0.

Device identity now comes from the token, so an agent needs only a backend URL
and a credential.

## 🔴 Priority 1 — End-to-end production deploy

Still blocked on account provisioning (Supabase + Render). Now
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

## 🟡 Priority 2 — Replace edge-agent stubs with real telemetry

File:
- `agents/edge-agent/internal/collector/system.go`

Required changes:
- Replace `simulateCPU()` and the hardcoded 16GB/500GB with real `/proc` reads
- Network counters are still `0 // placeholder`
- Validate behaviour on a Linux/Jetson target

The agent now authenticates and delivers correctly — but the numbers it delivers
are invented. Do not put it on real hardware and expect trustworthy RCA inputs,
and do not show a design partner these values as if they were measurements.

(`project_id` is no longer relevant here: the device is resolved from the token,
and the hardcoded `demoProjectID` has been removed.)

---

## 🟡 Priority 3 — Harden frontend auth storage

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
