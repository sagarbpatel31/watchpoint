"""Watchpoint ROS2 Collector entry point.

Monitors ROS2 topics and nodes, sending telemetry to the Watchpoint API.
Falls back to simulation mode when rclpy is not available.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from datetime import datetime, timezone

from .node_inspector import NodeInspector
from .sender import WatchpointSender
from .topic_monitor import TopicMonitor

try:
    import rclpy
    from rclpy.node import Node  # noqa: F401  (availability probe)

    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False

logger = logging.getLogger("ros2_collector")

COLLECTION_INTERVAL_SEC = 5.0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watchpoint ROS2 Collector",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Watchpoint API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("WP_DEVICE_TOKEN", ""),
        help=(
            "Device token for ingest (default: $WP_DEVICE_TOKEN). Mint one with "
            "POST /api/v1/devices/{device_id}/tokens. The device this collector "
            "reports as is resolved from the token, so no device UUID is needed."
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=COLLECTION_INTERVAL_SEC,
        help=f"Collection interval in seconds (default: {COLLECTION_INTERVAL_SEC})",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        default=False,
        help="Force simulation mode even if rclpy is available",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )
    return parser.parse_args(argv)


async def collect_and_send(
    topic_monitor: TopicMonitor,
    node_inspector: NodeInspector,
    sender: WatchpointSender,
) -> None:
    """Run a single collection cycle: gather data and send to API."""
    # Explicit ISO-8601 UTC rather than a bare epoch float, so the wire format
    # is unambiguous alongside every other collector.
    timestamp = datetime.now(timezone.utc).isoformat()

    topics = topic_monitor.list_topics()
    topic_rates = topic_monitor.measure_rates()
    nodes = node_inspector.list_nodes()

    # Field names must match the ingest schemas exactly: `labels_json` and
    # `metadata_json`, not `labels` / `metadata`. The API rejects unknown fields
    # now, but it used to accept and discard them — which meant every
    # topic_rate_hz point arrived with no record of which topic it measured.
    #
    # device_id is deliberately absent: the backend attributes the batch to the
    # device that owns the token.
    metric_points = []
    for topic_name, rate_hz in topic_rates.items():
        metric_points.append(
            {
                "metric_name": "topic_rate_hz",
                "value": rate_hz,
                "timestamp": timestamp,
                "unit": "hz",
                "labels_json": {"topic": topic_name},
            }
        )

    metric_points.append(
        {
            "metric_name": "ros2_node_count",
            "value": len(nodes),
            "timestamp": timestamp,
            "labels_json": {},
        }
    )

    metric_points.append(
        {
            "metric_name": "ros2_topic_count",
            "value": len(topics),
            "timestamp": timestamp,
            "labels_json": {},
        }
    )

    await sender.send_metrics(metric_points)

    event = {
        "timestamp": timestamp,
        "level": "info",
        "source": "ros2_collector",
        "message": f"Collected {len(topics)} topics, {len(nodes)} nodes",
        "metadata_json": {
            "topics": topics,
            "nodes": nodes,
            "rates": topic_rates,
        },
    }
    await sender.send_logs([event])


async def run_loop(args: argparse.Namespace) -> None:
    """Main collection loop."""
    use_simulation = args.simulate or not ROS2_AVAILABLE

    if use_simulation:
        logger.info("Running in SIMULATION mode (rclpy not available or --simulate set)")
    else:
        logger.info("Running with live ROS2 connection")
        rclpy.init()

    topic_monitor = TopicMonitor(use_simulation=use_simulation)
    node_inspector = NodeInspector(use_simulation=use_simulation)
    sender = WatchpointSender(api_url=args.api_url, token=args.token)

    shutdown = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("Starting collection loop (interval=%.1fs)", args.interval)

    try:
        while not shutdown.is_set():
            try:
                await collect_and_send(topic_monitor, node_inspector, sender)
                logger.debug("Collection cycle complete")
            except Exception:
                logger.exception("Error during collection cycle")

            try:
                await asyncio.wait_for(shutdown.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        await sender.close()
        if not use_simulation:
            rclpy.shutdown()
        logger.info("Collector stopped")


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_loop(args))


if __name__ == "__main__":
    main()
