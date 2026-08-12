"""AI-005 — Decision-perception mismatch.

Trigger: The incident contains inferences with high detection confidence (>0.80)
whose linked policy decisions chose a non-safety action (continue / proceed / ignore),
AND the incident also has OOD signals — indicating the robot proceeded despite
the model encountering out-of-distribution inputs.

Severity: high
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_layer import Decision, Inference
from app.rca.ai_rules.base import AIBaseRule

# Confidence threshold above which a detection is considered "high confidence"
_HIGH_CONF_THRESHOLD = 0.80
# Actions that indicate the robot continued despite a detection
_CONTINUE_ACTIONS = {"continue", "proceed", "continue_navigation", "ignore", "pass"}


class RuleAI005(AIBaseRule):
    rule_id = "AI-005"
    name = "Decision-perception mismatch"

    async def evaluate(self, incident_id: uuid.UUID, db: AsyncSession) -> dict[str, Any] | None:
        # Check whether the incident has any OOD signals
        ood_signals = await self._get_ood_signals(incident_id, db)
        if not ood_signals:
            return None  # No OOD — mismatch pattern not applicable

        # Fetch all inferences for the incident with high confidence
        result = await db.execute(
            select(Inference)
            .where(
                Inference.incident_id == incident_id,
                Inference.confidence >= _HIGH_CONF_THRESHOLD,
            )
            .order_by(Inference.timestamp_ns)
        )
        high_conf_inferences = list(result.scalars().all())

        if not high_conf_inferences:
            return None

        # For each high-confidence inference, check for a linked "continue" decision
        mismatches: list[dict[str, Any]] = []
        for inf in high_conf_inferences:
            decisions_result = await db.execute(
                select(Decision).where(Decision.inference_id == inf.id)
            )
            decisions = list(decisions_result.scalars().all())

            for dec in decisions:
                action_lower = dec.action.lower().replace("-", "_").replace(" ", "_")
                if any(cont in action_lower for cont in _CONTINUE_ACTIONS):
                    mismatches.append(
                        {
                            "inference_id": str(inf.id),
                            "confidence": inf.confidence,
                            "action": dec.action,
                            "policy": dec.policy_name,
                        }
                    )

        if not mismatches:
            return None

        ood_count = len(ood_signals)
        mismatch_count = len(mismatches)
        avg_conf = sum(m["confidence"] for m in mismatches) / mismatch_count

        return {
            "rule_id": self.rule_id,
            "cause": "Decision-perception mismatch",
            "confidence": 0.72,
            "description": (
                f"Robot continued navigation ({mismatch_count} decision{'s' if mismatch_count > 1 else ''}) "
                f"while perception confidence was high ({avg_conf:.2f} avg) but "
                f"{ood_count} OOD signal{'s were' if ood_count > 1 else ' was'} active. "
                "The policy chose to proceed despite inputs that were statistically "
                "out-of-distribution from the training set — a potential safety gap."
            ),
            "evidence": [
                {
                    "signal": "decision_perception_mismatch",
                    "rule_id": self.rule_id,
                    "mismatch_count": mismatch_count,
                    "ood_signal_count": ood_count,
                    "avg_confidence_at_mismatch": round(avg_conf, 3),
                    "actions": list({m["action"] for m in mismatches}),
                    "description": (
                        f"{mismatch_count} continue decision{'s' if mismatch_count > 1 else ''} "
                        f"with {avg_conf:.2f} avg confidence + {ood_count} active OOD signals"
                    ),
                }
            ],
            "suggested_steps": [
                "Review policy logic for OOD-aware action gating — robot should slow or stop when OOD score exceeds threshold",
                "Add OOD score as an explicit input to the policy decision layer",
                "Define minimum confidence AND maximum OOD score thresholds for 'continue' actions",
                "Replay the incident with updated weights to verify the mismatch is model-dependent",
            ],
        }
