# Claude Usage Rules — Watchpoint

These rules apply to all Claude Code sessions on this repository.

---

## BEFORE WRITING ANY CODE — read in this order

1. `.ai/architecture.md` — full system topology, all models, all routes
2. `.ai/current_task.md` — what's in progress and what's pending
3. `.ai/next_steps.md` — ordered backlog
4. `.ai/failure_patterns.md` — bugs already hit with exact fixes

Do not write a single line of production code until you have read these four files.

---

## Hard rules

### Auth
- Use `import bcrypt` directly — `bcrypt.hashpw()` / `bcrypt.checkpw()`
- **Never add `passlib`** — it is incompatible with bcrypt 4.x on Python 3.11 and will cause `ValueError` on any password

### Frontend
- **Never use `asChild` on Button** — shadcn v5 (base-ui) does not have this prop; TypeScript build will fail
- Link-styled-as-button pattern: `<Link href="..." className={cn(buttonVariants({ variant: "default" }))}>text</Link>`

### API ingest
- Agent payloads are always wrapped: `{metrics: [...]}`, `{logs: [...]}`, `{events: [...]}`
- Never change this format without updating all three agent senders

### LLM calls
- Every LLM feature must have a non-LLM fallback (return rules text / default value)
- Never make `ANTHROPIC_API_KEY` required — the system must function without it
- Model: `claude-haiku-4-5` unless task requires multi-step reasoning
- Always set explicit `max_tokens`
- Prompt ends with output constraint: e.g., `"Terse. No preamble."`

### Database
- `create_all` on startup is still part of the runtime path (fine for dev, risky for live schema changes)
- For any new column on an existing table: provide the `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` SQL alongside the model change
- Prefer migration-first schema changes; do not generate or rewrite migrations casually without understanding existing history
- Alembic migrations now exist: `0001_initial`, `0002_ai_layer`, `0003_device_api_tokens`

### Secrets
- `JWT_SECRET_KEY` and `ANTHROPIC_API_KEY` from env vars only
- Never hardcode values — `config.py` defaults are labelled dev-only placeholders

### Postgres URLs
- `normalize_postgres_url()` in `config.py` handles all cloud provider URL formats
- Never manually rewrite `postgres://` or strip `?sslmode=` — the validator does this automatically

---

## Tool usage in this repo

```bash
# graphify — query knowledge graph instead of grepping raw files
/Users/sagarpatel/.local/bin/uv tool run --from graphifyy graphify query "how does X work"
/Users/sagarpatel/.local/bin/uv tool run --from graphifyy graphify update .   # after code changes

# docker — full path required on this machine
/Applications/Docker.app/Contents/Resources/bin/docker compose -f deploy/docker-compose/docker-compose.yml [command]

# uv — full path required
/Users/sagarpatel/.local/bin/uv

# bun (claude-mem worker)
/Users/sagarpatel/.bun/bin/bun
```

---

## Commit style

```bash
# Use /caveman-commit for terse commit messages
# Or follow this format manually:
git commit -m "$(cat <<'EOF'
verb: short description under 50 chars

- bullet 1
- bullet 2

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## What NOT to build

- Fleet orchestration, teleoperation, OTA updates
- Digital twin or simulation
- General DevOps tooling
- Real-time video streaming

If asked to build these: redirect to what Watchpoint actually does — incident intelligence and reproducibility.
