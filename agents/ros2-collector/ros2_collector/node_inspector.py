"""ROS2 node inspection.

Lists active nodes and gathers node metadata.
Provides simulated data when rclpy is not available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("ros2_collector.node_inspector")

# Simulated nodes representing a typical ROS2 navigation deployment
_SIMULATED_NODES: list[dict] = [
    {
        "name": "/nav2_controller",
        "namespace": "/",
        "subscribers": ["/odom", "/scan", "/tf", "/goal_pose"],
        "publishers": ["/cmd_vel", "/local_plan"],
        "services": ["/nav2_controller/get_state"],
    },
    {
        "name": "/nav2_planner",
        "namespace": "/",
        "subscribers": ["/map", "/odom", "/tf", "/goal_pose"],
        "publishers": ["/plan", "/global_costmap/costmap"],
        "services": ["/nav2_planner/get_state"],
    },
    {
        "name": "/slam_toolbox",
        "namespace": "/",
        "subscribers": ["/scan", "/odom", "/tf"],
        "publishers": ["/map", "/tf"],
        "services": ["/slam_toolbox/save_map"],
    },
    {
        "name": "/robot_state_publisher",
        "namespace": "/",
        "subscribers": ["/joint_states"],
        "publishers": ["/tf", "/tf_static", "/robot_description"],
        "services": [],
    },
    {
        "name": "/lidar_driver",
        "namespace": "/",
        "subscribers": [],
        "publishers": ["/scan"],
        "services": ["/lidar_driver/configure"],
    },
    {
        "name": "/camera_driver",
        "namespace": "/",
        "subscribers": [],
        "publishers": ["/camera/image_raw", "/camera/camera_info"],
        "services": [],
    },
    {
        "name": "/imu_driver",
        "namespace": "/",
        "subscribers": [],
        "publishers": ["/imu/data"],
        "services": [],
    },
    {
        "name": "/inference_node",
        "namespace": "/",
        "subscribers": ["/camera/image_raw"],
        "publishers": ["/detections", "/diagnostics"],
        "services": ["/inference_node/reload_model"],
    },
    {
        "name": "/diagnostic_aggregator",
        "namespace": "/",
        "subscribers": ["/diagnostics"],
        "publishers": ["/diagnostics_agg"],
        "services": [],
    },
]


@dataclass
class NodeInfo:
    """Information about a single ROS2 node."""

    name: str
    namespace: str
    subscribers: list[str] = field(default_factory=list)
    publishers: list[str] = field(default_factory=list)
    services: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "namespace": self.namespace,
            "subscribers": self.subscribers,
            "publishers": self.publishers,
            "services": self.services,
        }


class NodeInspector:
    """Inspects ROS2 nodes and gathers metadata."""

    def __init__(self, use_simulation: bool = True) -> None:
        self._use_simulation = use_simulation
        self._ros_node = None

        if not use_simulation:
            try:
                import rclpy
                from rclpy.node import Node  # noqa: F401  (availability probe)

                self._ros_node = rclpy.create_node("watchpoint_node_inspector")
                logger.info("Created ROS2 node for node inspection")
            except Exception:
                logger.exception("Failed to create ROS2 node, falling back to simulation")
                self._use_simulation = True

    def list_nodes(self) -> list[str]:
        """Return a list of active node names."""
        if self._use_simulation:
            return [n["name"] for n in _SIMULATED_NODES]

        node_names_and_namespaces = self._ros_node.get_node_names_and_namespaces()
        return [name for name, _ns in node_names_and_namespaces]

    def get_node_info(self, node_name: str) -> NodeInfo | None:
        """Return detailed info for a specific node."""
        if self._use_simulation:
            for n in _SIMULATED_NODES:
                if n["name"] == node_name:
                    return NodeInfo(
                        name=n["name"],
                        namespace=n["namespace"],
                        subscribers=n["subscribers"],
                        publishers=n["publishers"],
                        services=n["services"],
                    )
            return None

        # Live ROS2 introspection
        node_names_and_namespaces = self._ros_node.get_node_names_and_namespaces()
        for name, namespace in node_names_and_namespaces:
            if name == node_name:
                pubs = self._ros_node.get_publisher_names_and_types_by_node(name, namespace)
                subs = self._ros_node.get_subscriber_names_and_types_by_node(name, namespace)
                srvs = self._ros_node.get_service_names_and_types_by_node(name, namespace)
                return NodeInfo(
                    name=name,
                    namespace=namespace,
                    publishers=[p[0] for p in pubs],
                    subscribers=[s[0] for s in subs],
                    services=[s[0] for s in srvs],
                )
        return None

    def get_all_node_info(self) -> list[NodeInfo]:
        """Return info for all active nodes."""
        return [
            info for name in self.list_nodes() if (info := self.get_node_info(name)) is not None
        ]

    def destroy(self) -> None:
        """Clean up ROS2 resources."""
        if self._ros_node is not None:
            self._ros_node.destroy_node()
            self._ros_node = None
