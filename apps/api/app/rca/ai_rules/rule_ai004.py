"""AI-004 — Per-layer inference latency anomaly.

Trigger: For any captured layer, the median latency in the second half of the
incident window exceeds 5× the median in the first half.

Severity: low
Min inferences per layer: 6 (3 per half)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.rca.ai_rules.base import AIBaseRule

# Minimum ratio (second-half p50 / first-half p50) to fire
_RATIO_THRESHOLD = 5.0
# Minimum inference count per layer to evaluate
_MIN_PER_LAYER = 6


class RuleAI004(AIBaseRule):
    rule_id = "AI-004"
    name = "Per-layer latency anomaly"

    async def evaluate(self, incident_id: uuid.UUID, db: AsyncSession) -> dict[str, Any] | None:
        inferences = await self._get_inferences(incident_id, db)

        # Group by layer_name — skip inferences without latency or layer info
        by_layer: dict[str, list[float]] = defaultdict(list)
        for inf in inferences:
            if inf.latency_ms is not None and inf.layer_name:
                by_layer[inf.layer_name].append(inf.latency_ms)

        worst_ratio = 0.0
        worst_layer = ""
        worst_baseline = 0.0
        worst_spike = 0.0

        for layer_name, latencies in by_layer.items():
            if len(latencies) < _MIN_PER_LAYER:
                continue

            mid = len(latencies) // 2
            baseline = self._median(latencies[:mid])
            spike = self._median(latencies[mid:])

            if baseline == 0:
                continue

            ratio = spike / baseline
            if ratio > worst_ratio:
                worst_ratio = ratio
                worst_layer = layer_name
                worst_baseline = baseline
                worst_spike = spike

        if worst_ratio < _RATIO_THRESHOLD:
            return None

        confidence = min(0.55 + (worst_ratio - _RATIO_THRESHOLD) * 0.03, 0.82)

        return {
            "rule_id": self.rule_id,
            "cause": "Per-layer inference latency anomaly",
            "confidence": round(confidence, 3),
            "description": (
                f"Layer '{worst_layer}' latency spiked {worst_ratio:.1f}× "
                f"(from {worst_baseline:.0f}ms → {worst_spike:.0f}ms median) "
                "during the second half of the incident. This points to "
                "resource starvation or thermal throttling affecting a specific "
                "network layer rather than the whole model."
            ),
            "evidence": [
                {
                    "signal": "per_layer_latency",
                    "rule_id": self.rule_id,
                    "layer_name": worst_layer,
                    "baseline_ms": round(worst_baseline, 1),
                    "spike_ms": round(worst_spike, 1),
                    "ratio": round(worst_ratio, 2),
                    "description": (
                        f"Layer {worst_layer}: {worst_baseline:.0f}ms → {worst_spike:.0f}ms "
                        f"({worst_ratio:.1f}× spike)"
                    ),
                }
            ],
            "suggested_steps": [
                f"Profile layer '{worst_layer}' during normal operation to establish a stable baseline",
                "Check for GPU memory pressure or cache eviction at the layer boundary",
                "Consider quantization or layer fusion if the layer is compute-bound",
                "Correlate the latency spike timestamp with thermal and CPU metrics",
            ],
        }
