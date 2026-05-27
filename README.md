# Watchpoint

**End-to-end traces, replay, and root-cause analysis for ROS2 and edge AI systems.**

Watchpoint is an incident analysis platform for physical AI systems. When a robot fails in the field, Watchpoint captures telemetry across the stack — logs, metrics, ROS2 topics, inference timing, hardware state — and generates replayable failure bundles with AI-assisted root-cause analysis.

> *Stop guessing why your robot failed.*

## Quick Start

```bash
# Clone the repo
git clone https://github.com/sagarbpatel31/watchpoint.git
cd watchpoint

# Start all services (requires Docker)
cd deploy/docker-compose
docker compose up --build -d

# Seed demo data (3 devices, 3 incidents, 1000+ metric points)
curl -X POST http://localhost:8000/api/v1/seed/demo

# Open the app
open http://localhost:3000
```

## Architecture

```
watchpoint/
  apps/
    web/                # Next.js frontend (TypeScript, Tailwind, shadcn/ui)
    api/                # FastAPI backend (Python, SQLAlchemy, PostgreSQL)
  agents/
    edge-agent/         # Go agent for Linux/Jetson devices
    ros2-collector/     # Python ROS2 topic/node monitor
  packages/
    sample-data/        # Demo fixtures and seed script
  deploy/
    docker-compose/     # Local development stack
```

### Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Pydantic v2 |
| Edge Agent | Go (stdlib only), cross-compiled for Linux/ARM |
| ROS2 Collector | Python, rclpy (with simulation fallback) |
| Infrastructure | Docker Compose, Alembic migrations |

## MVP Scope

### What it does

- **Edge Agent** — lightweight Go binary that collects CPU, memory, GPU, disk metrics + tails logs on Linux/Jetson
- **ROS2 Collector** — monitors topic publish rates, node health, message lag
- **Incident Capture** — automatic triggers on CPU threshold, topic rate drop, thermal throttling, process crash
- **Correlation Timeline** — single-page view connecting metrics, events, ROS2 state, and deployment version
- **Root Cause Analysis** — rules-based engine that identifies resource contention, thermal throttling, version regressions, and failure chains
- **Replay Bundles** — downloadable .zip with incident metadata, metrics, logs, deployment config, and analysis summary

### What it intentionally does NOT do (yet)

Teleoperation, fleet orchestration, OTA updates, digital twin, simulation, billing, mobile app.

## Demo Scenarios

The seed data includes three real-world failure patterns:

1. **CPU Contention** — Navigation topic degrades from 10Hz to 2Hz as CPU spikes to 98% on Jetson Orin
2. **Thermal Throttling** — GPU overheats to 92°C during outdoor operation, inference latency spikes 10x
3. **Version Regression** — New deployment causes mission aborts due to planner frequency config change

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/devices/register` | Register a new device |
| POST | `/api/v1/ingest/logs` | Batch log ingestion |
| POST | `/api/v1/ingest/metrics` | Batch metric ingestion |
| POST | `/api/v1/ingest/events` | App event ingestion |
| GET | `/api/v1/incidents/` | List incidents |
| GET | `/api/v1/incidents/{id}` | Incident detail |
| POST | `/api/v1/incidents/{id}/analyze` | Run root cause analysis |
| POST | `/api/v1/incidents/{id}/replay-bundle` | Generate replay bundle |
| GET | `/api/v1/bundles/{id}` | Download replay bundle |

Full interactive API docs at `http://localhost:8000/docs`.

## Development

```bash
# Backend only (requires PostgreSQL running)
cd apps/api
pip install -e .
uvicorn app.main:app --reload

# Frontend only
cd apps/web
npm install
npm run dev

# Edge agent
cd agents/edge-agent
go build ./cmd/agent
./agent --api-url http://localhost:8000 --device-name my-robot

# Full stack
cd deploy/docker-compose
docker compose up --build
```

## Target Users

- Early robotics startups using ROS2
- Teams deploying on Jetson, x86 Linux, Raspberry Pi, or ARM Linux
- Companies running field pilots where failures are expensive and hard to diagnose

**Verticals:** inspection robots, warehouse robots, delivery robots, security patrol, construction/site robots, drone ground-station workflows.

## License

Proprietary. All rights reserved.
