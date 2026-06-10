# Failure Patterns

Confirmed bugs hit during this build, plus known risks not yet triggered. Read before debugging anything.

---

## FIXED — bugs already resolved

### F1. passlib + bcrypt 4.x incompatibility

**Symptom:** `ValueError: password cannot be longer than 72 bytes` on any login, even 4-char passwords.
**Root cause:** passlib's internal bcrypt API call broke with bcrypt>=4.x. Passlib unmaintained.
**Fix:** Removed passlib. Direct `import bcrypt` + `bcrypt.hashpw()` / `bcrypt.checkpw()`.
**Files:** `apps/api/app/security.py`, `apps/api/pyproject.toml`

---

### F2. shadcn v5 `asChild` TypeScript build failure

**Symptom:** `Property 'asChild' does not exist on type 'ButtonHTMLAttributes<HTMLButtonElement>'`
**Root cause:** shadcn/ui v5 (base-ui) removed Radix `asChild` prop from Button.
**Fix:**
```tsx
// WRONG: <Button asChild><Link href="/x">text</Link></Button>
// CORRECT:
<Link href="/x" className={cn(buttonVariants({ variant: "default" }))}>text</Link>
```

---

### F3. apps/web committed as git submodule

**Symptom:** `git status` shows `apps/web` as mode `160000`. Files inside not stageable.
**Root cause:** `create-next-app` created its own `.git/` inside `apps/web/`.
**Fix:** `rm -rf apps/web/.git && git rm --cached apps/web && git add apps/web/`

---

### F4. Edge agent payload format mismatch → 422

**Symptom:** API returns `422 Unprocessable Entity` when agent POSTs metrics.
**Root cause:** Agent sent flat `[{...}]`. API ingest schema expects `{metrics: [{...}]}`.
**Fix:** Updated `agents/edge-agent/internal/sender/http.go` to wrap payload in object.

---

### F5. Missing DB columns after model change

**Symptom:** `asyncpg.exceptions.UndefinedColumnError: column users.password_hash does not exist`
**Root cause:** `create_all` creates tables but does not add columns to existing tables.
**Fix (dev workaround):**
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) DEFAULT '';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
```
**Permanent fix:** Priority 2 — initialize Alembic migrations.

---

### F6. Seed UniqueViolationError on re-seed

**Symptom:** `POST /seed/demo` returns 500 after first run. UniqueViolationError on device_name or email.
**Fix (dev):**
```sql
TRUNCATE users, workspaces, projects, devices, deployments, incidents,
  event_logs, metric_points, incident_artifacts, annotations CASCADE;
```
Then re-run: `curl -X POST http://localhost:8000/api/v1/seed/demo`

---

### F7. postgres:// URL rejected by SQLAlchemy

**Symptom:** `sqlalchemy.exc.ArgumentError: Could not parse rfc1738 URL from string 'postgres://...'`
**Fix:** Already handled automatically. `config.py:normalize_postgres_url()` rewrites it. Do not manually edit cloud URIs.

---

### F8. Docker not in PATH

**Symptom:** `command not found: docker` even with Docker Desktop running.
**Fix:** `/Applications/Docker.app/Contents/Resources/bin/docker`

---

### F9. Port 3000 conflict (Docker web vs preview server)

**Symptom:** Preview server fails: "Port 3000 is required but is in use."
**Fix:** `docker stop watchpoint-web-1` — or change Docker Compose web port to `3001:3000`.

---

### F10. uv not in PATH

**Symptom:** `command not found: uv`
**Fix:** `/Users/sagarpatel/.local/bin/uv`

---

## KNOWN RISKS — not yet triggered, likely in near future

### R1. 🔴 Schema change on live Supabase DB (HIGH)

**Risk:** Any new column added to a SQLAlchemy model will not appear in the Supabase DB — `create_all` skips existing tables. First request touching that column returns 500.
**Trigger:** After Priority 1 deploy, any feature requiring a new column.
**Mitigation:** Priority 2 — initialize Alembic and generate initial migration immediately after first successful deploy. Do not land any model change before this.

---

### R2. 🟠 Render cold start causes first-load failure

**Risk:** Render free tier spins down after 15 min idle. First request takes ~60s. If frontend has a short API timeout, the page appears broken.
**Trigger:** Any user visiting `watchpoint.vercel.app` after a period of inactivity.
**Mitigation:** Frontend should show a loading state for ≥90s on first load, not a generic error. Or: add a UptimeRobot/cron ping to prevent spin-down.

---

### R3. 🟠 Telemetry injection via unauthenticated ingest

**Status:** mitigated in source
**Fix:** `/ingest/metrics`, `/ingest/logs`, `/ingest/events`, `/ingest/model-runs`, `/ingest/inferences`, `/ingest/decisions`, and `/devices/heartbeat/{id}` now require `X-Device-Token`. Device tokens are issued on registration and stored hashed on the device row.
**Residual risk:** Deployment still needs to confirm the new header is enforced in production and that seeded/demo flows receive a valid token.

---

### R4. 🟠 Simulated metrics trigger false analysis results on real hardware

**Risk:** Edge agent sends fake CPU/disk/network values. Rules engine may trigger `Resource contention` (cpu > 85%) or other rules on fabricated data.
**Trigger:** Deploying the Go agent to a real Jetson device.
**Mitigation:** Priority 4 — replace stubs with real `/proc` reads before any hardware deployment.

---

### R5. 🟡 Supabase DB pause breaks first load

**Risk:** Supabase free tier pauses DB after 1 week of inactivity. Resume takes ~30s. FastAPI lifespan `create_all` call may timeout or throw during pause/resume window.
**Mitigation:** Health check retry logic in frontend. Or: add a simple DB ping in the health route to verify connectivity.
