"""ROS2 topic monitoring.

Lists active topics and measures their publish rates.
Provides simulated data when rclpy is not available.
"""

from __future__ import annotations

import logging
import math
import random
import time

logger = logging.getLogger("ros2_collector.topic_monitor")

# Simulated topics that mirror a typical ROS2 navigation stack
_SIMULATED_TOPICS: list[dict] = [
    {"name": "/cmd_vel", "type": "geometry_msgs/msg/Twist", "base_rate": 10.0},
    {"name": "/odom", "type": "nav_msgs/msg/Odometry", "base_rate": 50.0},
    {"name": "/scan", "type": "sensor_msgs/msg/LaserScan", "base_rate": 20.0},
    {"name": "/imu/data", "type": "sensor_msgs/msg/Imu", "base_rate": 100.0},
    {"name": "/camera/image_raw", "type": "sensor_msgs/msg/Image", "base_rate": 30.0},
    {"name": "/tf", "type": "tf2_msgs/msg/TFMessage", "base_rate": 100.0},
    {"name": "/diagnostics", "type": "diagnostic_msgs/msg/DiagnosticArray", "base_rate": 1.0},
    {"name": "/map", "type": "nav_msgs/msg/OccupancyGrid", "base_rate": 0.2},
    {"name": "/goal_pose", "type": "geometry_msgs/msg/PoseStamped", "base_rate": 0.1},
    {"name": "/robot_description", "type": "std_msgs/msg/String", "base_rate": 0.01},
]


class TopicMonitor:
    """Monitors ROS2 topics and measures their publish rates."""

    def __init__(self, use_simulation: bool = True) -> None:
        self._use_simulation = use_simulation
        self._ros_node = None

        if not use_simulation:
            try:
                import rclpy
                from rclpy.node import Node  # noqa: F401  (availability probe)

                self._ros_node = rclpy.create_node("watchpoint_topic_monitor")
                logger.info("Created ROS2 node for topic monitoring")
            except Exception:
                logger.exception("Failed to create ROS2 node, falling back to simulation")
                self._use_simulation = True

    def list_topics(self) -> list[str]:
        """Return a list of active topic names."""
        if self._use_simulation:
            return [t["name"] for t in _SIMULATED_TOPICS]

        topic_names_and_types = self._ros_node.get_topic_names_and_types()
        return [name for name, _types in topic_names_and_types]

    def list_topics_with_types(self) -> list[dict]:
        """Return topics with their message types."""
        if self._use_simulation:
            return [{"name": t["name"], "type": t["type"]} for t in _SIMULATED_TOPICS]

        topic_names_and_types = self._ros_node.get_topic_names_and_types()
        return [
            {"name": name, "type": types[0] if types else "unknown"}
            for name, types in topic_names_and_types
        ]

    def measure_rates(self) -> dict[str, float]:
        """Measure the publish rate (Hz) for each active topic.

        Returns a mapping of topic name to rate in Hz.
        """
        if self._use_simulation:
            return self._simulate_rates()

        # Live ROS2 rate measurement would require subscribing to each topic
        # and measuring inter-message intervals. For now, return placeholder.
        rates: dict[str, float] = {}
        for name in self.list_topics():
            rates[name] = 0.0
        return rates

    def _simulate_rates(self) -> dict[str, float]:
        """Generate realistic simulated topic rates with jitter."""
        rates: dict[str, float] = {}
        t = time.time()
        for topic in _SIMULATED_TOPICS:
            base = topic["base_rate"]
            # Add gaussian jitter (5% std dev)
            jitter = random.gauss(0, base * 0.05)
            # Add slow sinusoidal variation
            variation = base * 0.02 * math.sin(t * 0.1 + hash(topic["name"]) % 100)
            rate = max(0.0, base + jitter + variation)
            rates[topic["name"]] = round(rate, 2)
        return rates

    def destroy(self) -> None:
        """Clean up ROS2 resources."""
        if self._ros_node is not None:
            self._ros_node.destroy_node()
            self._ros_node = None
