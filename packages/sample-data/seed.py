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
