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

## ✅ Done — was P2 (real edge-agent telemetry)

The agent reads `/proc/stat`, `/proc/meminfo`, `/proc/net/dev`, `statfs` and
`/sys/class/thermal` on Linux, and reports nothing at all on other platforms.
Verified against `top`, `df` and `/proc` on a live host, and end to end into
Postgres through the real ingest path.

One item could not be validated here: **temperature has no hardware to test
against** — this VM exposes no thermal zones. The parsers are covered by
fixtures (`proc_test.go`), but the `/sys/class/thermal` walk itself wants
confirming on a Jetson before anyone relies on `cpu_temp_c` in the field.

---

## 🟡 Priority 2 — the model-collector never measures inference latency

Files:
- `agents/model-collector/model_collector/adapters/pytorch_adapter.py`
- `agents/model-collector/model_collector/sender.py` (`_INFERENCE_FIELDS`)
- `apps/api/app/rca/ai_rules/rule_ai003.py`
- `apps/api/app/services/analysis.py` (thermal rule, line ~121)

**Correcting an earlier entry here, which claimed the latency data "is already
there" on `Inference.latency_ms` and only needed re-exposing. It is not there.**
The column exists, `sender.py` lists `latency_ms` in its projection whitelist,
and the adapter docstring advertises "wall latency" — but nothing ever writes
the field. The frame built in `pytorch_adapter._build_frame` carries
`inference_id`, `layer_name`, `timestamp_ns`, input/output shapes, output
statistics and `confidence`, and no latency at all. The only timing in the file
is `elapsed_us`, which measures the hook's *own* overhead for a warning check
and is never captured.

Two rules depend on it and neither can fire on real data:

- **AI-003** filters `inferences` on `latency_ms is not None`, which is never
  true outside the seed.
- The **system thermal rule** requires `inference_latency_ms > 100` on top of a
  temperature above 75 before it will name "Thermal throttling". Confirmed by
  running the analyzer: temperature alone yields evidence but no probable cause;
  supplying both makes it fire at 0.80.

So a real overheating robot produces a temperature reading and no diagnosis.

Fix: time the forward pass in the adapter and set `latency_ms` on the frame.
That is a few lines and it makes AI-003 genuinely live. Emitting it *also* as an
`inference_latency_ms` MetricPoint is what closes the thermal rule — worth doing
in the same change, since the two consumers read from different places.

This is the same read-path/write-path split that hid the broken collectors: the
schema, the whitelist, the rule and the docstring all describe a field that no
code produces.

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
