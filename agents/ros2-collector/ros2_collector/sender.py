"""HTTP client for sending telemetry data to the Watchpoint API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("ros2_collector.sender")

DEFAULT_TIMEOUT = 10.0
MAX_RETRIES = 3


class WatchpointSender:
    """Sends collected ROS2 data to the Watchpoint API via HTTP."""

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        timeout: float = DEFAULT_TIMEOUT,
        token: str | None = None,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if token:
            # Ingest is device-token authenticated; the backend resolves which
            # device a batch belongs to from this, so no device_id is sent.
            headers["X-Device-Token"] = token
        else:
            logger.warning(
                "No device token configured — ingest will be rejected with 401. "
                "Pass --token or set WP_DEVICE_TOKEN."
            )
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            timeout=timeout,
            headers=headers,
        )
        logger.info("Initialized sender targeting %s", self._api_url)

    async def send_metrics(self, metric_points: list[dict[str, Any]]) -> bool:
        """Send metric data points to the ingest endpoint.

        Returns True on success, False on failure.
        """
        if not metric_points:
            return True

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.post(
                    "/api/v1/ingest/metrics",
                    json={"metrics": metric_points},
                )
                response.raise_for_status()
                logger.debug(
                    "Sent %d metric points (status=%d)",
                    len(metric_points),
                    response.status_code,
                )
                return True
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "API returned %d on metrics send (attempt %d/%d): %s",
                    exc.response.status_code,
                    attempt,
                    MAX_RETRIES,
                    exc.response.text[:200],
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "Network error sending metrics (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

        logger.error("Failed to send metrics after %d attempts", MAX_RETRIES)
        return False

    async def send_logs(self, events: list[dict[str, Any]]) -> bool:
        """Send event log entries to the ingest endpoint.

        The envelope key is `logs`, matching LogBatchIngest. It previously sent
        `events`, which /ingest/logs rejects with a 422 — /ingest/events is the
        route that takes that key.

        Returns True on success, False on failure.
        """
        if not events:
            return True

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self._client.post(
                    "/api/v1/ingest/logs",
                    json={"logs": events},
                )
                response.raise_for_status()
                logger.debug(
                    "Sent %d log events (status=%d)",
                    len(events),
                    response.status_code,
                )
                return True
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "API returned %d on log send (attempt %d/%d): %s",
                    exc.response.status_code,
                    attempt,
                    MAX_RETRIES,
                    exc.response.text[:200],
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "Network error sending logs (attempt %d/%d): %s",
                    attempt,
                    MAX_RETRIES,
                    exc,
                )

        logger.error("Failed to send logs after %d attempts", MAX_RETRIES)
        return False

    # Device registration is no longer an agent concern: /devices/register now
    # requires an operator JWT. An operator creates the device, mints a token,
    # and configures the agent with it.

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
        logger.info("Sender closed")
