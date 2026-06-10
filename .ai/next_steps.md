# Next Steps

Last updated: 2026-06-10.

Priority order is fixed. Deployment remains first, but the Alembic item is no longer "initialize migrations" because that work already exists in the repo.

---

## 🔴 Priority 1 — End-to-end production deploy

Nothing is more important than proving the real hosted stack works.

### Step A: Provision Supabase (user action)
1. Create Supabase project `watchpoint`
2. Copy the Postgres URI from Settings → Database → Connection string
3. Provide that URI for Render `DATABASE_URL`

### Step B: Deploy API to Render (user action)
1. Import `sagarbpatel31/watchpoint` as a Render Blueprint
2. Confirm `apps/api/render.yaml` is used
3. Set `DATABASE_URL`
4. Optionally set `ANTHROPIC_API_KEY`
5. Wait for deploy and record the exact Render URL

### Step C: Wire Vercel to the real API (after Render URL exists)
1. Set `NEXT_PUBLIC_API_URL` in Vercel to the Render URL
2. Redeploy the frontend
3. Confirm `CORS_ORIGINS` in `apps/api/render.yaml` matches the actual Vercel domain
4. Verify frontend requests are hitting the hosted API

### Step D: Seed and smoke test production
1. `POST /api/v1/seed/demo`
2. `GET /api/v1/health`
3. Login to the hosted frontend with `demo@watchpoint.ai / demo123`
4. Open dashboard, incident detail, and inference detail pages

### P1 exit criteria
- Render API URL is live and responds successfully
- Vercel frontend points to that API URL
- Production seed succeeds
- Basic user flow works end-to-end

---

## 🟠 Priority 2 — Switch production workflow to migration-first

Alembic is already present:
- `apps/api/alembic/versions/0001_initial.py`
- `apps/api/alembic/versions/0002_ai_layer.py`
- `apps/api/alembic/versions/0003_device_api_tokens.py`

Remaining work:
- Document and use `alembic upgrade head` for production bootstrapping
- Decide whether to keep or remove `Base.metadata.create_all()` in `apps/api/app/main.py`
- Ensure future schema changes land as migrations first, not model-only changes

Do this immediately after the first confirmed production deploy.

---

## ✅ Priority 3 — Secure all ingest endpoints

Implemented:
- Device API tokens are issued on registration and stored hashed in `devices.api_token_hash`
- Classic telemetry ingest now requires `X-Device-Token`
- AI-layer ingest now requires `X-Device-Token`
- `POST /devices/heartbeat/{id}` now requires `X-Device-Token`
- Go edge-agent stores the returned token after registration
- Model-collector accepts `WP_DEVICE_TOKEN`

Remaining verification:
- Confirm the deploy path preserves the new device token flow end-to-end in Render/Vercel

---

## 🟡 Priority 4 — Replace edge-agent stubs with real telemetry

Files:
- `agents/edge-agent/internal/collector/system.go`
- `agents/edge-agent/internal/sender/http.go`

Required changes:
- Replace simulated CPU/disk/network with real collection
- Validate behavior on Linux/Jetson target environment

Do not deploy the current Go agent to real hardware expecting trustworthy RCA inputs.

---

## 🟡 Priority 5 — Harden frontend auth storage

File:
- `apps/web/src/lib/auth.ts`

Current state:
- JWT stored in `localStorage`

Recommended fix:
- Move to `httpOnly`, `Secure`, `SameSite=Strict` cookies
- Add a server-side relay or middleware pattern in Next.js as needed

This matters, but it is still behind P1-P4.

---

## Supporting cleanup

These are not the top production blockers, but they should be fixed soon:

- Populate `ros2_snapshot.json` instead of shipping a placeholder in replay bundles
- Confirm the production frontend domain and CORS origin match the Render deploy URL
