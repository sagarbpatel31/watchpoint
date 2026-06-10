"""Seed endpoint for populating demo data directly into the database."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ai_layer import Framework, Inference, ModelRun, OODSignal
from app.models.device import Deployment, Device, DeviceStatus
from app.models.incident import Incident, IncidentStatus, Severity
from app.models.telemetry import EventLog, LogLevel, MetricPoint
from app.models.user import User
from app.models.workspace import Project, Workspace
from app.device_tokens import generate_device_token, hash_device_token
from app.security import hash_password

router = APIRouter(prefix="/seed", tags=["seed"])

# Fixed IDs for demo consistency
WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEVICE_IDS = [
    uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
    uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
    uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
]
DEPLOYMENT_IDS = [
    uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddd01"),
    uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddd02"),
    uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddd03"),
]
INCIDENT_IDS = [
    uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01"),
    uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeee02"),
    uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeee03"),
]
MODEL_RUN_IDS = [
    uuid.UUID("ffffffff-ffff-ffff-ffff-fffffffffff1"),
    uuid.UUID("ffffffff-ffff-ffff-ffff-fffffffffff2"),
    uuid.UUID("ffffffff-ffff-ffff-ffff-fffffffffff3"),
]
# Specific inference IDs that get OOD signals attached
_OOD_INF_IDS = [
    uuid.UUID("cccccccc-cccc-cccc-cccc-cc0000000001"),  # incident 01, frame 15 (t≈45s)
    uuid.UUID("cccccccc-cccc-cccc-cccc-cc0000000002"),  # incident 01, frame 16 (t≈48s)
    uuid.UUID("cccccccc-cccc-cccc-cccc-cc0000000003"),  # incident 02, frame 13 (t≈62s)
]


@router.post("/demo")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    """Seed the database with demo data for 3 devices and 3 incidents."""
    now = datetime.now(timezone.utc)
    base_time = now - timedelta(hours=1)

    # User
    user = User(
        id=USER_ID,
        email="demo@watchpoint.ai",
        name="Demo User",
        password_hash=hash_password("demo123"),
    )
    db.add(user)

    # Workspace
    workspace = Workspace(
        id=WORKSPACE_ID, name="Watchpoint Demo", slug="watchpoint-demo", owner_id=USER_ID
    )
    db.add(workspace)

    # Project
    project = Project(
        id=PROJECT_ID,
        workspace_id=WORKSPACE_ID,
        name="Warehouse Robotics Fleet",
        slug="warehouse-fleet",
    )
    db.add(project)

    # Devices
    devices_data = [
        {
            "id": DEVICE_IDS[0],
            "name": "jetson-orin-nav-01",
            "hardware": "NVIDIA Jetson Orin NX",
            "os": "Ubuntu 22.04 L4T",
            "agent": "0.1.0",
            "status": DeviceStatus.online,
        },
        {
            "id": DEVICE_IDS[1],
            "name": "rpi4-patrol-02",
            "hardware": "Raspberry Pi 4 Model B",
            "os": "Debian 12",
            "agent": "0.1.0",
            "status": DeviceStatus.online,
        },
        {
            "id": DEVICE_IDS[2],
            "name": "x86-warehouse-03",
            "hardware": "Intel NUC i7-1260P",
            "os": "Ubuntu 22.04",
            "agent": "0.1.0",
            "status": DeviceStatus.offline,
        },
    ]

    for d in devices_data:
        device_token = generate_device_token()
        device = Device(
            id=d["id"],
            project_id=PROJECT_ID,
            device_name=d["name"],
            api_token_hash=hash_device_token(device_token),
            hardware_model=d["hardware"],
            os_version=d["os"],
            agent_version=d["agent"],
            status=d["status"],
            last_seen_at=now - timedelta(minutes=5)
            if d["status"] == DeviceStatus.online
            else now - timedelta(hours=3),
            registered_at=now - timedelta(days=7),
        )
        db.add(device)

    # Deployments
    deployments_data = [
        {"id": DEPLOYMENT_IDS[0], "device_id": DEVICE_IDS[0], "version": "nav-stack-v2.3.1"},
        {"id": DEPLOYMENT_IDS[1], "device_id": DEVICE_IDS[1], "version": "patrol-v1.8.0"},
        {"id": DEPLOYMENT_IDS[2], "device_id": DEVICE_IDS[2], "version": "warehouse-v2.4.0"},
    ]

    for dep in deployments_data:
        deployment = Deployment(
            id=dep["id"],
            device_id=dep["device_id"],
            version=dep["version"],
            deployed_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
        )
        db.add(deployment)

    await db.flush()

    # --- INCIDENT 1: CPU contention causing topic degradation ---
    incident1 = Incident(
        id=INCIDENT_IDS[0],
        project_id=PROJECT_ID,
        device_id=DEVICE_IDS[0],
        deployment_id=DEPLOYMENT_IDS[0],
        title="CPU contention causing /cmd_vel topic degradation",
        severity=Severity.high,
        status=IncidentStatus.open,
        trigger_type="topic_rate_drop",
        started_at=base_time,
    )
    db.add(incident1)

    # Metrics for incident 1 - 90 seconds of data
    import random

    random.seed(42)

    for sec in range(90):
        ts = base_time + timedelta(seconds=sec)
        # CPU rises from 45% to 98%
        cpu = 45 + (53 * (sec / 90) ** 1.5) + random.uniform(-2, 2)
        cpu = min(cpu, 99)
        # Topic rate drops from 10Hz to 2Hz
        topic_rate = 10 - (8 * max(0, (sec - 20) / 70) ** 1.3) + random.uniform(-0.3, 0.3)
        topic_rate = max(topic_rate, 1)
        # Inference latency spikes from 15ms to 200ms
        latency = 15 + (185 * max(0, (sec - 30) / 60) ** 2) + random.uniform(-3, 3)
        # Memory stays relatively stable
        memory = 62 + (sec / 90) * 15 + random.uniform(-1, 1)
        # GPU temp rises
        gpu_temp = 55 + (sec / 90) * 25 + random.uniform(-1, 1)

        for name, value, unit in [
            ("cpu_percent", cpu, "%"),
            ("topic_rate_hz", topic_rate, "Hz"),
            ("inference_latency_ms", latency, "ms"),
            ("memory_percent", memory, "%"),
            ("gpu_temp_c", gpu_temp, "C"),
        ]:
            db.add(
                MetricPoint(
                    device_id=DEVICE_IDS[0],
                    incident_id=INCIDENT_IDS[0],
                    timestamp=ts,
                    metric_name=name,
                    value=round(value, 2),
                    unit=unit,
                )
            )

    # Events for incident 1
    events_1 = [
        (0, LogLevel.info, "system", "Agent started monitoring"),
        (5, LogLevel.info, "ros2_monitor", "Topic /cmd_vel publishing at 10.2 Hz"),
        (15, LogLevel.warn, "system", "CPU usage rising: 58%"),
        (22, LogLevel.warn, "ros2_monitor", "Topic /cmd_vel rate dropped to 8.1 Hz"),
        (30, LogLevel.error, "ros2_monitor", "Topic /cmd_vel rate below threshold: 6.3 Hz"),
        (35, LogLevel.warn, "inference", "Inference latency increased: 45ms (baseline: 15ms)"),
        (40, LogLevel.error, "system", "CPU usage critical: 89%"),
        (45, LogLevel.error, "ros2_monitor", "Topic /cmd_vel rate critically low: 3.8 Hz"),
        (50, LogLevel.warn, "navigation", "Motion planner receiving degraded inputs"),
        (55, LogLevel.error, "inference", "Inference latency spike: 120ms"),
        (60, LogLevel.fatal, "watchdog", "Navigation watchdog timeout - no valid /cmd_vel for 5s"),
        (65, LogLevel.error, "system", "CPU sustained above 95% for 30s"),
        (70, LogLevel.warn, "ros2_monitor", "Topic /scan subscriber backlog: 12 messages"),
        (75, LogLevel.error, "navigation", "Emergency stop triggered - topic starvation"),
        (80, LogLevel.info, "system", "Incident captured - uploading context window"),
    ]
    for offset, level, source, message in events_1:
        db.add(
            EventLog(
                device_id=DEVICE_IDS[0],
                incident_id=INCIDENT_IDS[0],
                timestamp=base_time + timedelta(seconds=offset),
                level=level,
                source=source,
                message=message,
            )
        )

    # --- INCIDENT 2: Thermal throttling ---
    incident2 = Incident(
        id=INCIDENT_IDS[1],
        project_id=PROJECT_ID,
        device_id=DEVICE_IDS[0],
        deployment_id=DEPLOYMENT_IDS[0],
        title="GPU thermal throttling during outdoor operation",
        severity=Severity.critical,
        status=IncidentStatus.investigating,
        trigger_type="thermal_threshold",
        started_at=base_time + timedelta(minutes=15),
    )
    db.add(incident2)

    t2_base = base_time + timedelta(minutes=15)
    for sec in range(120):
        ts = t2_base + timedelta(seconds=sec)
        gpu_temp = 65 + (27 * (sec / 120) ** 1.2) + random.uniform(-1, 1)
        inference_lat = 18 + (180 * max(0, (sec - 40) / 80) ** 2) + random.uniform(-2, 2)
        cpu = 55 + random.uniform(-5, 5)
        topic_rate = max(2, 10 - (8 * max(0, (sec - 60) / 60)) + random.uniform(-0.5, 0.5))

        for name, value, unit in [
            ("gpu_temp_c", gpu_temp, "C"),
            ("inference_latency_ms", inference_lat, "ms"),
            ("cpu_percent", cpu, "%"),
            ("topic_rate_hz", topic_rate, "Hz"),
        ]:
            db.add(
                MetricPoint(
                    device_id=DEVICE_IDS[0],
                    incident_id=INCIDENT_IDS[1],
                    timestamp=ts,
                    metric_name=name,
                    value=round(value, 2),
                    unit=unit,
                )
            )

    events_2 = [
        (0, LogLevel.info, "thermal", "GPU temperature: 65°C - normal range"),
        (20, LogLevel.warn, "thermal", "GPU temperature rising: 72°C"),
        (40, LogLevel.warn, "thermal", "GPU temperature: 78°C - approaching throttle threshold"),
        (50, LogLevel.error, "thermal", "GPU thermal throttling activated at 82°C"),
        (55, LogLevel.warn, "inference", "Inference latency increased: 65ms"),
        (70, LogLevel.error, "thermal", "GPU temperature critical: 88°C"),
        (80, LogLevel.error, "inference", "Inference latency spike: 150ms"),
        (90, LogLevel.fatal, "watchdog", "Inference watchdog timeout"),
        (95, LogLevel.error, "thermal", "GPU temperature: 91°C - emergency"),
        (100, LogLevel.info, "system", "Emergency thermal shutdown initiated"),
    ]
    for offset, level, source, message in events_2:
        db.add(
            EventLog(
                device_id=DEVICE_IDS[0],
                incident_id=INCIDENT_IDS[1],
                timestamp=t2_base + timedelta(seconds=offset),
                level=level,
                source=source,
                message=message,
            )
        )

    # --- INCIDENT 3: Version regression ---
    incident3 = Incident(
        id=INCIDENT_IDS[2],
        project_id=PROJECT_ID,
        device_id=DEVICE_IDS[2],
        deployment_id=DEPLOYMENT_IDS[2],
        title="Navigation regression after warehouse-v2.4.0 deployment",
        severity=Severity.medium,
        status=IncidentStatus.resolved,
        trigger_type="mission_abort",
        started_at=base_time + timedelta(minutes=30),
        resolved_at=base_time + timedelta(minutes=45),
    )
    db.add(incident3)

    t3_base = base_time + timedelta(minutes=30)
    for sec in range(60):
        ts = t3_base + timedelta(seconds=sec)
        cpu = 40 + random.uniform(-5, 10)
        latency = 25 + (sec / 60) * 40 + random.uniform(-3, 3)
        topic_rate = max(4, 10 - (sec / 60) * 4 + random.uniform(-0.5, 0.5))

        for name, value, unit in [
            ("cpu_percent", cpu, "%"),
            ("inference_latency_ms", latency, "ms"),
            ("topic_rate_hz", topic_rate, "Hz"),
        ]:
            db.add(
                MetricPoint(
                    device_id=DEVICE_IDS[2],
                    incident_id=INCIDENT_IDS[2],
                    timestamp=ts,
                    metric_name=name,
                    value=round(value, 2),
                    unit=unit,
                )
            )

    events_3 = [
        (0, LogLevel.info, "deployment", "New deployment warehouse-v2.4.0 active"),
        (5, LogLevel.info, "navigation", "Navigation stack initialized"),
        (10, LogLevel.warn, "navigation", "Path planner latency higher than v2.3.x baseline"),
        (20, LogLevel.warn, "navigation", "Missed 2 waypoints in sequence"),
        (
            30,
            LogLevel.error,
            "navigation",
            "Mission abort - could not reach waypoint within timeout",
        ),
        (
            35,
            LogLevel.info,
            "system",
            "Config diff detected: planner_hz changed from 20 to 10 in v2.4.0",
        ),
        (40, LogLevel.warn, "navigation", "v2.4.0 planner frequency is half of v2.3.x"),
        (
            50,
            LogLevel.info,
            "system",
            "Incident captured and correlated with deployment version change",
        ),
    ]
    for offset, level, source, message in events_3:
        db.add(
            EventLog(
                device_id=DEVICE_IDS[2],
                incident_id=INCIDENT_IDS[2],
                timestamp=t3_base + timedelta(seconds=offset),
                level=level,
                source=source,
                message=message,
            )
        )

    # -----------------------------------------------------------------------
    # AI layer — ModelRuns, Inferences, OODSignals
    # -----------------------------------------------------------------------
    ai_frame_count = _seed_ai_layer(db, base_time)

    await db.commit()

    return {
        "status": "ok",
        "seeded": {
            "users": 1,
            "workspaces": 1,
            "projects": 1,
            "devices": 3,
            "deployments": 3,
            "incidents": 3,
            "event_logs": len(events_1) + len(events_2) + len(events_3),
            "metric_points": 90 * 5 + 120 * 4 + 60 * 3,
            "model_runs": 3,
            "inference_frames": ai_frame_count,
            "ood_signals": 3,
        },
    }


def _seed_ai_layer(db: AsyncSession, base_time: datetime) -> int:
    """Seed ModelRun + Inference + OODSignal rows for all 3 demo incidents.

    Returns total inference frame count.

    Incident 01 — CPU contention (30 frames, 90s, DEVICE_IDS[0])
      Confidence: 0.93 → 0.41  (>30% drop — AI-001 fires)
      Latency:    15ms → 195ms
      OOD:        2 signals on frames 15+16 (AI-002 fires)

    Incident 02 — Thermal throttle (25 frames, 120s, DEVICE_IDS[0])
      Confidence: 0.91 → 0.48  (~38% drop — AI-001 fires)
      Latency:    18ms → 200ms
      OOD:        1 signal on frame 13 (AI-002 fires)

    Incident 03 — Version regression (10 frames, 60s, DEVICE_IDS[2])
      Confidence: 0.87 → 0.83  (<5% drop — AI-001 does NOT fire)
      Latency:    20ms → 45ms
      OOD:        none (AI-002 does NOT fire)
    """
    now = datetime.now(timezone.utc)

    # ---- Model runs --------------------------------------------------------
    model_runs = [
        ModelRun(
            id=MODEL_RUN_IDS[0],
            device_id=DEVICE_IDS[0],
            framework=Framework.pytorch,
            model_name="yolo-v8n",
            weights_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            started_at=base_time,
            metadata_json={"input_size": [640, 640], "batch_size": 1},
        ),
        ModelRun(
            id=MODEL_RUN_IDS[1],
            device_id=DEVICE_IDS[0],
            framework=Framework.pytorch,
            model_name="yolo-v8n",
            weights_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            started_at=base_time + timedelta(minutes=15),
            metadata_json={"input_size": [640, 640], "batch_size": 1},
        ),
        ModelRun(
            id=MODEL_RUN_IDS[2],
            device_id=DEVICE_IDS[2],
            framework=Framework.pytorch,
            model_name="nav-planner",
            weights_hash="b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3",
            started_at=base_time + timedelta(minutes=30),
            metadata_json={"input_size": [224, 224], "batch_size": 1},
        ),
    ]
    for mr in model_runs:
        db.add(mr)

    # ---- Incident 01: confidence collapse (30 frames, 3s spacing) ----------
    # First half (frames 0-14): median ~0.87 → Second half (frames 15-29): median ~0.44
    # Drop ≈ 49% → AI-001 fires
    i01_base = base_time
    i01_step_s = 3  # 90s / 30 frames

    # Pre-compute confidence + latency for all 30 frames
    # Confidence: smooth S-curve drop starting at frame 10
    i01_confs = []
    for f in range(30):
        if f < 10:
            c = 0.93 - f * 0.005  # 0.93 → 0.88 (slow decline)
        elif f < 15:
            c = 0.88 - (f - 10) * 0.065  # 0.88 → 0.555 (sharp drop)
        else:
            c = 0.51 - (f - 15) * 0.005  # 0.51 → 0.44 (plateau)
        i01_confs.append(round(max(c, 0.40), 3))

    i01_lats = []
    for f in range(30):
        if f < 12:
            lat = 15.0 + f * 0.5
        else:
            lat = 21.0 + (f - 12) ** 2.1 * 0.95
        i01_lats.append(round(min(lat, 200.0), 1))

    for f in range(30):
        ts_ns = int((i01_base + timedelta(seconds=f * i01_step_s)).timestamp() * 1e9)
        # Frames 15 and 16 get fixed UUIDs so we can attach OOD signals
        inf_id = _OOD_INF_IDS[0] if f == 15 else (_OOD_INF_IDS[1] if f == 16 else uuid.uuid4())
        db.add(
            Inference(
                id=inf_id,
                model_run_id=MODEL_RUN_IDS[0],
                device_id=DEVICE_IDS[0],
                incident_id=INCIDENT_IDS[0],
                timestamp_ns=ts_ns,
                confidence=i01_confs[f],
                latency_ms=i01_lats[f],
                layer_name="model.head",
                output_mean=round(0.55 - f * 0.003, 4),
                output_std=round(0.12 + f * 0.002, 4),
            )
        )

    # OOD signals for incident 01 (frames 15 + 16)
    db.add(
        OODSignal(
            id=uuid.uuid4(),
            inference_id=_OOD_INF_IDS[0],
            signal_type="embedding_distance",
            score=2.71,
            threshold=2.0,
            is_ood=True,
            created_at=now,
        )
    )
    db.add(
        OODSignal(
            id=uuid.uuid4(),
            inference_id=_OOD_INF_IDS[1],
            signal_type="softmax_entropy",
            score=0.81,
            threshold=0.60,
            is_ood=True,
            created_at=now,
        )
    )

    # ---- Incident 02: thermal throttle (25 frames, ~4.8s spacing) ----------
    # First half (frames 0-11): median ~0.85 → Second half (frames 12-24): median ~0.54
    # Drop ≈ 37% → AI-001 fires
    i02_base = base_time + timedelta(minutes=15)
    i02_step_s = 4.8  # 120s / 25 frames

    i02_confs = []
    for f in range(25):
        # Keep first 12 frames high, sharp drop in frames 12-24
        # First half (0-11) median ≈ 0.88, second half (12-24) median ≈ 0.56
        # Drop ≈ 36% → AI-001 fires comfortably
        if f < 12:
            c = 0.91 - f * 0.004  # 0.91 → 0.866 (gentle decline)
        else:
            c = 0.68 - (f - 12) * 0.020  # 0.68 → 0.44 (thermal cliff)
        i02_confs.append(round(max(c, 0.45), 3))

    i02_lats = []
    for f in range(25):
        if f < 10:
            lat = 18.0 + f * 0.8
        else:
            lat = 26.0 + (f - 10) ** 2.2 * 1.1
        i02_lats.append(round(min(lat, 200.0), 1))

    for f in range(25):
        ts_ns = int((i02_base + timedelta(seconds=f * i02_step_s)).timestamp() * 1e9)
        inf_id = _OOD_INF_IDS[2] if f == 13 else uuid.uuid4()
        db.add(
            Inference(
                id=inf_id,
                model_run_id=MODEL_RUN_IDS[1],
                device_id=DEVICE_IDS[0],
                incident_id=INCIDENT_IDS[1],
                timestamp_ns=ts_ns,
                confidence=i02_confs[f],
                latency_ms=i02_lats[f],
                layer_name="model.head",
                output_mean=round(0.52 - f * 0.002, 4),
                output_std=round(0.11 + f * 0.003, 4),
            )
        )

    # OOD signal for incident 02 (frame 13)
    db.add(
        OODSignal(
            id=uuid.uuid4(),
            inference_id=_OOD_INF_IDS[2],
            signal_type="softmax_entropy",
            score=0.74,
            threshold=0.60,
            is_ood=True,
            created_at=now,
        )
    )

    # ---- Incident 03: version regression (10 frames, 6s spacing) -----------
    # Confidence stable 0.87 → 0.83 — drop <5% → AI-001 does NOT fire
    # No OOD signals → AI-002 does NOT fire
    i03_base = base_time + timedelta(minutes=30)

    i03_confs = [round(0.87 - f * 0.004, 3) for f in range(10)]
    i03_lats = [round(20.0 + f * 2.5, 1) for f in range(10)]

    for f in range(10):
        ts_ns = int((i03_base + timedelta(seconds=f * 6)).timestamp() * 1e9)
        db.add(
            Inference(
                id=uuid.uuid4(),
                model_run_id=MODEL_RUN_IDS[2],
                device_id=DEVICE_IDS[2],
                incident_id=INCIDENT_IDS[2],
                timestamp_ns=ts_ns,
                confidence=i03_confs[f],
                latency_ms=i03_lats[f],
                layer_name="planner.backbone",
                output_mean=round(0.61 - f * 0.001, 4),
                output_std=round(0.08 + f * 0.001, 4),
            )
        )

    return 30 + 25 + 10  # 65 total frames
