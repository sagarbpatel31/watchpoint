"""Seed the Watchpoint API with sample data from fixture files.

Usage:
    python seed.py [--api-url http://localhost:8000]

Loads devices, deployments, incidents, event logs, and metric points
from the fixtures/ directory and posts them to the Watchpoint API.
Timestamps use relative offsets so data always appears fresh.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# IDs used consistently across all fixtures
WORKSPACE_ID = "00000000-0000-0000-0000-000000000000"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"


def load_json(path: Path) -> list | dict:
    """Load and parse a JSON fixture file."""
    with open(path) as f:
        return json.load(f)


def compute_base_time() -> float:
    """Return a base timestamp that is 'now minus 1 hour' for freshness."""
    return time.time() - 3600


def resolve_timestamp(base_time: float, offset_seconds: float | int | None) -> str:
    """Convert a relative offset to an ISO 8601 timestamp string."""
    if offset_seconds is None:
        return None
    ts = base_time + offset_seconds
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


async def seed_workspace(client: httpx.AsyncClient, base_time: float) -> None:
    """Create the demo workspace."""
    print("[1/6] Creating workspace...")
    payload = {
        "id": WORKSPACE_ID,
        "name": "Watchpoint Demo",
        "slug": "watchpoint-demo",
    }
    resp = await client.post("/api/v1/workspaces", json=payload)
    if resp.status_code in (200, 201, 409):
        print(f"  Workspace created (status={resp.status_code})")
    else:
        print(f"  WARNING: Workspace creation returned {resp.status_code}: {resp.text[:200]}")


async def seed_project(client: httpx.AsyncClient, base_time: float) -> None:
    """Create the demo project."""
    print("[2/6] Creating project...")
    payload = {
        "id": PROJECT_ID,
        "workspace_id": WORKSPACE_ID,
        "name": "Warehouse Robotics Fleet",
        "description": "Fleet of autonomous robots for warehouse logistics and patrol operations",
    }
    resp = await client.post("/api/v1/projects", json=payload)
    if resp.status_code in (200, 201, 409):
        print(f"  Project created (status={resp.status_code})")
    else:
        print(f"  WARNING: Project creation returned {resp.status_code}: {resp.text[:200]}")


async def seed_devices(client: httpx.AsyncClient, base_time: float) -> None:
    """Register all devices from the fixtures."""
    print("[3/6] Registering devices...")
    devices = load_json(FIXTURES_DIR / "devices.json")
    for device in devices:
        payload = {
            "device_id": device["id"],
            "project_id": device["project_id"],
            "name": device["name"],
            "hardware": device["hardware"],
            "os": device["os"],
            "labels": device.get("labels", {}),
        }
        resp = await client.post("/api/v1/devices/register", json=payload)
        status = "ok" if resp.status_code in (200, 201, 409) else f"WARN({resp.status_code})"
        print(f"  Device {device['name']}: {status}")


async def seed_deployments(client: httpx.AsyncClient, base_time: float) -> None:
    """Create deployments for each device."""
    print("[4/6] Creating deployments...")
    deployments = load_json(FIXTURES_DIR / "deployments.json")
    for dep in deployments:
        payload = {
            "id": dep["id"],
            "device_id": dep["device_id"],
            "project_id": dep["project_id"],
            "version": dep["version"],
            "status": dep["status"],
            "deployed_at": dep["deployed_at"],
            "commit_sha": dep.get("commit_sha"),
            "notes": dep.get("notes"),
        }
        resp = await client.post("/api/v1/deployments", json=payload)
        status = "ok" if resp.status_code in (200, 201, 409) else f"WARN({resp.status_code})"
        print(f"  Deployment {dep['version']} -> {dep['device_id'][:8]}: {status}")


async def seed_incidents(client: httpx.AsyncClient, base_time: float) -> None:
    """Create incidents and load their event logs and metric points."""
    print("[5/6] Creating incidents with events and metrics...")

    incident_files = sorted((FIXTURES_DIR / "incidents").glob("*.json"))

    for incident_path in incident_files:
        incident = load_json(incident_path)
        slug = incident_path.stem  # e.g., "cpu-contention-001"

        # Resolve relative timestamps
        created_at = resolve_timestamp(base_time, incident.get("created_at_offset_seconds", 0))
        resolved_at = resolve_timestamp(base_time, incident.get("resolved_at_offset_seconds"))

        payload = {
            "id": incident["id"],
            "project_id": incident["project_id"],
            "device_id": incident["device_id"],
            "deployment_id": incident.get("deployment_id"),
            "title": incident["title"],
            "description": incident["description"],
            "severity": incident["severity"],
            "status": incident["status"],
            "root_cause": incident.get("root_cause"),
            "labels": incident.get("labels", {}),
            "created_at": created_at,
            "resolved_at": resolved_at,
        }
        resp = await client.post("/api/v1/incidents", json=payload)
        status = "ok" if resp.status_code in (200, 201, 409) else f"WARN({resp.status_code})"
        print(f"  Incident '{incident['title'][:50]}...': {status}")

        # Load event logs
        events_path = FIXTURES_DIR / "event-logs" / f"{slug}-events.json"
        if events_path.exists():
            events = load_json(events_path)
            event_payloads = []
            for evt in events:
                event_ts = resolve_timestamp(
                    base_time + incident.get("created_at_offset_seconds", 0),
                    evt["offset_seconds"],
                )
                event_payloads.append(
                    {
                        "id": evt["id"],
                        "incident_id": evt["incident_id"],
                        "device_id": evt["device_id"],
                        "timestamp": event_ts,
                        "level": evt["level"],
                        "source": evt["source"],
                        "message": evt["message"],
                    }
                )
            resp = await client.post(
                "/api/v1/ingest/logs",
                json={"events": event_payloads},
            )
            status = "ok" if resp.status_code in (200, 201) else f"WARN({resp.status_code})"
            print(f"    Events ({len(event_payloads)}): {status}")

        # Load metric points
        metrics_path = FIXTURES_DIR / "metric-points" / f"{slug}-metrics.json"
        if metrics_path.exists():
            metrics_data = load_json(metrics_path)
            metric_payloads = []
            incident_start = base_time + incident.get("created_at_offset_seconds", 0)

            for metric_name, values in metrics_data["metrics"].items():
                for i, value in enumerate(values):
                    metric_ts = resolve_timestamp(incident_start, i)
                    metric_payloads.append(
                        {
                            "incident_id": metrics_data["incident_id"],
                            "device_id": metrics_data["device_id"],
                            "metric_name": metric_name,
                            "value": value,
                            "timestamp": metric_ts,
                        }
                    )

            # Send in batches of 500
            batch_size = 500
            total_sent = 0
            for i in range(0, len(metric_payloads), batch_size):
                batch = metric_payloads[i : i + batch_size]
                resp = await client.post(
                    "/api/v1/ingest/metrics",
                    json={"metrics": batch},
                )
                if resp.status_code not in (200, 201):
                    print(f"    Metrics batch WARN({resp.status_code})")
                total_sent += len(batch)
            print(f"    Metrics ({total_sent} points across {len(metrics_data['metrics'])} series): ok")


async def seed_ai_layer_demo4(client: httpx.AsyncClient, base_time: float) -> None:
    """Seed Demo 4 AI layer data via REST API ingest endpoints.

    Creates ModelRun + 30 Inferences + 3 OODSignals + 4 Decisions for the
    shadow misclassification incident (inc-00400-...).
    """
    print("[7/7] Seeding Demo 4 AI layer (model-collector data)...")

    DEVICE_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    INCIDENT_ID = "inc-00400-0004-0004-0004-000000000004"
    MODEL_RUN_ID = "ffffffff-ffff-ffff-ffff-fffffffffff4"
    t4_base = base_time + 50 * 60  # 50 min after base_time

    # 1. Create ModelRun
    resp = await client.post("/api/v1/ingest/model-runs", json={
        "id": MODEL_RUN_ID,
        "device_id": DEVICE_ID,
        "framework": "pytorch",
        "model_name": "yolov8n-warehouse",
        "weights_hash": "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5",
        "started_at": datetime.fromtimestamp(t4_base, tz=timezone.utc).isoformat(),
        "metadata": {"input_size": [640, 640], "batch_size": 1},
    })
    status = "ok" if resp.status_code in (200, 201, 409) else f"WARN({resp.status_code})"
    print(f"  ModelRun: {status}")

    # 2. Build 30 inference frames
    ood_frame_ids = {
        14: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000014",
        17: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000017",
        22: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000022",
    }
    continue_frame_ids = {
        3: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000003",
        6: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000006",
        9: "d4d4d4d4-d4d4-d4d4-d4d4-d4d400000009",
    }

    def _conf(f: int) -> float:
        if f < 10:
            return round(0.93 - f * 0.002, 3)
        elif f < 20:
            return round(max(0.21, 0.91 - (f - 10) * 0.070), 3)
        else:
            return 0.21

    inferences = []
    for f in range(30):
        ts_ns = int((t4_base + f * 4.0) * 1e9)
        inf_id = ood_frame_ids.get(f) or continue_frame_ids.get(f)
        outputs = None
        if 14 <= f <= 22:
            outputs = {"top_class": "shadow", "top_score": _conf(f)}

        item: dict = {
            "model_run_id": MODEL_RUN_ID,
            "device_id": DEVICE_ID,
            "incident_id": INCIDENT_ID,
            "timestamp_ns": ts_ns,
            "confidence": _conf(f),
            "latency_ms": round(35.0 + f * 0.57, 1),
            "layer_name": "model.head",
            "output_mean": round(0.48 - f * 0.008, 4),
            "output_std": round(0.14 + f * 0.003, 4),
        }
        if inf_id:
            item["inference_id"] = inf_id
        if outputs:
            item["outputs"] = outputs
        inferences.append(item)

    resp = await client.post("/api/v1/ingest/inferences", json={"inferences": inferences})
    status = "ok" if resp.status_code in (200, 201) else f"WARN({resp.status_code})"
    print(f"  Inferences (30 frames): {status}")

    # 3. OOD signals
    ood_signals_data = [
        {"inference_id": ood_frame_ids[14], "signal_type": "embedding_distance", "score": 2.71, "threshold": 2.0, "is_ood": True},
        {"inference_id": ood_frame_ids[17], "signal_type": "softmax_entropy", "score": 0.81, "threshold": 0.60, "is_ood": True},
        {"inference_id": ood_frame_ids[22], "signal_type": "embedding_distance", "score": 2.93, "threshold": 2.0, "is_ood": True},
    ]
    # OOD signals go via ingest endpoint if available; skip silently if not wired
    for sig in ood_signals_data:
        resp = await client.post("/api/v1/ingest/ood-signals", json=sig)
        if resp.status_code not in (200, 201, 404, 405):
            print(f"  OOD signal WARN({resp.status_code})")

    # 4. Decisions — "continue" actions (trigger AI-005) + final emergency stop
    decisions = [
        {"inference_id": continue_frame_ids[3], "policy_name": "nav_policy_v2", "action": "continue_navigation", "confidence": _conf(3)},
        {"inference_id": continue_frame_ids[6], "policy_name": "nav_policy_v2", "action": "continue_navigation", "confidence": _conf(6)},
        {"inference_id": continue_frame_ids[9], "policy_name": "nav_policy_v2", "action": "continue_navigation", "confidence": _conf(9)},
        {"inference_id": ood_frame_ids[14], "policy_name": "nav_policy_v2", "action": "emergency_stop", "confidence": 0.89},
    ]
    resp = await client.post("/api/v1/ingest/decisions", json={"decisions": decisions})
    status = "ok" if resp.status_code in (200, 201) else f"WARN({resp.status_code})"
    print(f"  Decisions (4): {status}")


async def verify_seed(client: httpx.AsyncClient) -> None:
    """Quick verification that seeded data is accessible."""
    print("[6/6] Verifying seeded data...")
    checks = [
        ("/api/v1/devices", "devices"),
        ("/api/v1/incidents", "incidents"),
    ]
    for endpoint, label in checks:
        try:
            resp = await client.get(endpoint)
            if resp.status_code == 200:
                data = resp.json()
                count = len(data) if isinstance(data, list) else data.get("total", "?")
                print(f"  {label}: {count} records")
            else:
                print(f"  {label}: endpoint returned {resp.status_code}")
        except Exception as e:
            print(f"  {label}: could not verify ({e})")


async def main(api_url: str) -> None:
    """Run the full seed process."""
    print(f"Seeding Watchpoint API at {api_url}")
    print("=" * 60)

    base_time = compute_base_time()
    base_dt = datetime.fromtimestamp(base_time, tz=timezone.utc)
    print(f"Base time: {base_dt.isoformat()} (now - 1 hour)\n")

    async with httpx.AsyncClient(
        base_url=api_url,
        timeout=30.0,
        headers={"Content-Type": "application/json"},
    ) as client:
        # Check API health first
        try:
            resp = await client.get("/api/v1/health")
            if resp.status_code != 200:
                print(f"WARNING: Health check returned {resp.status_code}")
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to API at {api_url}")
            print("Make sure the API is running (e.g., docker compose up)")
            sys.exit(1)

        await seed_workspace(client, base_time)
        await seed_project(client, base_time)
        await seed_devices(client, base_time)
        await seed_deployments(client, base_time)
        await seed_incidents(client, base_time)
        await seed_ai_layer_demo4(client, base_time)
        await verify_seed(client)

    print("\n" + "=" * 60)
    print("Seed complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Watchpoint with sample data")
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Watchpoint API base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.api_url))
