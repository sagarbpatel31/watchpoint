# Watchpoint — root Makefile
# Targets: dev, test, lint, typecheck, build-web, seed, clean
#
# Tool resolution: prefer whatever is on PATH, fall back to the usual macOS
# install locations, so the same targets work on a dev laptop, a Linux box, and
# CI. Override any of them explicitly:  make test UV=/path/to/uv

UV     ?= $(shell command -v uv     2>/dev/null || echo $(HOME)/.local/bin/uv)
BUN    ?= $(shell command -v bun    2>/dev/null || echo $(HOME)/.bun/bin/bun)
DOCKER ?= $(shell command -v docker 2>/dev/null || echo /Applications/Docker.app/Contents/Resources/bin/docker)
GO     ?= $(shell command -v go     2>/dev/null || echo /usr/local/go/bin/go)

# Web tasks run through bun when present, npx otherwise (CI images often have
# neither bun nor a global next).
WEB_RUNNER ?= $(shell command -v bun >/dev/null 2>&1 && echo "$(BUN) x" || echo "npx")

.PHONY: dev test test-api test-model-collector test-ros2-collector test-edge-agent \
        lint lint-api lint-model-collector lint-ros2-collector lint-web lint-edge-agent \
        typecheck-web build-web build-edge-agent seed clean check tools

# ── Tool check ─────────────────────────────────────────────────────────────

tools:
	@test -x "$(UV)" || { echo "✗ uv not found at '$(UV)' — install from https://docs.astral.sh/uv/ or pass UV=/path/to/uv"; exit 1; }
	@echo "✓ uv     $(UV)"
	@command -v node >/dev/null 2>&1 && echo "✓ node   $$(command -v node)" || echo "… node not found (web targets will fail)"

# ── Local dev stack ────────────────────────────────────────────────────────

dev:
	$(DOCKER) compose -f deploy/docker-compose/docker-compose.yml up -d

# ── Tests ──────────────────────────────────────────────────────────────────

test: test-api test-model-collector test-ros2-collector test-edge-agent

test-api:
	@echo "▶ api tests"
	cd apps/api && $(UV) run --extra dev pytest -q

test-model-collector:
	@echo "▶ model-collector tests"
	cd agents/model-collector && $(UV) run --extra dev pytest -q

test-ros2-collector:
	@echo "▶ ros2-collector tests"
	cd agents/ros2-collector && $(UV) run --extra dev pytest -q

test-edge-agent:
	@echo "▶ edge-agent tests"
	cd agents/edge-agent && $(GO) test ./...

# ── Lint ───────────────────────────────────────────────────────────────────

lint: lint-api lint-model-collector lint-ros2-collector lint-web lint-edge-agent

lint-api:
	@echo "▶ lint api"
	cd apps/api && $(UV) run --extra dev ruff check app/ tests/ && $(UV) run --extra dev ruff format --check app/ tests/

lint-model-collector:
	@echo "▶ lint model-collector"
	cd agents/model-collector && $(UV) run --extra dev ruff check model_collector/ tests/ && $(UV) run --extra dev ruff format --check model_collector/ tests/

lint-ros2-collector:
	@echo "▶ lint ros2-collector"
	cd agents/ros2-collector && $(UV) run --extra dev ruff check ros2_collector/ tests/ && $(UV) run --extra dev ruff format --check ros2_collector/ tests/

lint-web:
	@echo "▶ lint web"
	cd apps/web && $(WEB_RUNNER) eslint --max-warnings 0

lint-edge-agent:
	@echo "▶ lint edge-agent"
	@cd agents/edge-agent && unformatted="$$($(GO)fmt -l .)"; \
		if [ -n "$$unformatted" ]; then \
			echo "✗ gofmt needed:"; echo "$$unformatted"; exit 1; \
		fi
	cd agents/edge-agent && $(GO) vet ./...

# ── Typecheck / build ──────────────────────────────────────────────────────

typecheck-web:
	@echo "▶ typecheck web"
	cd apps/web && $(WEB_RUNNER) tsc --noEmit

build-web:
	@echo "▶ build web"
	cd apps/web && $(WEB_RUNNER) next build

# The agent ships to robots on all three Linux targets; darwin/arm64 proves the
# non-Linux fallback still compiles on a dev laptop.
build-edge-agent:
	@echo "▶ build edge-agent (all targets)"
	@cd agents/edge-agent && for t in linux/amd64 linux/arm64 linux/arm darwin/arm64; do \
		echo "  $$t"; \
		GOOS=$${t%/*} GOARCH=$${t#*/} $(GO) build -o /dev/null ./cmd/agent || exit 1; \
	done

# Everything CI runs.
check: lint test typecheck-web

# ── Seed ───────────────────────────────────────────────────────────────────

seed:
	curl -s -X POST http://localhost:8000/api/v1/seed/demo | python3 -m json.tool

# ── Clean ──────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .venv -not -path "*/node_modules/*" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "clean done"
