import uuid

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.telemetry import EventLog, MetricPoint
from app.rca.ai_rules import RuleAI001, RuleAI002, RuleAI003, RuleAI004, RuleAI005

_AI_RULES = [RuleAI001(), RuleAI002(), RuleAI003(), RuleAI004(), RuleAI005()]


async def generate_llm_summary(
    incident_title: str,
    top_cause: dict,
    evidence_signals: list[str],
) -> str:
    """Generate a terse 2-sentence incident summary using Claude Haiku.

    Token budget:
    - Input: ~120 tokens (prompt + evidence, capped at 4 signals)
    - Output: max_tokens=80 (hard ceiling — 2 sentences ≈ 40–60 tokens)
    - Model: claude-haiku-4-5 (~25× cheaper than Sonnet for this task)
    - Cost: ~$0.03 per 1,000 incident analyses

    Falls back to the rules-based cause string if ANTHROPIC_API_KEY is not set.
    """
    if not settings.anthropic_api_key:
        return top_cause.get("description", top_cause.get("cause", "Analysis unavailable."))

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Cap evidence at 4 signals to keep input tokens tight
    evidence_str = "; ".join(evidence_signals[:4]) if evidence_signals else "none"

    prompt = (
        f"Incident: {incident_title}\n"
        f"Top cause: {top_cause['cause']} (confidence: {top_cause['confidence']:.0%})\n"
        f"Evidence: {evidence_str}\n"
        f"Remediation hint: {top_cause.get('description', 'investigate')}\n\n"
        "Write 2 sentences: what failed and what to do. Terse. No preamble."
    )

    message = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=80,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def analyze_incident(
    incident_id: uuid.UUID, db: AsyncSession, incident_title: str = ""
) -> dict:
    """Rules-based root cause analysis for an incident.

    Analyzes metric patterns and event logs to determine probable causes.
    Start rules-based, not fully agentic — add LLM summarization later.
    """
    # Fetch metrics for this incident
    metrics_result = await db.execute(
        select(MetricPoint)
        .where(MetricPoint.incident_id == incident_id)
        .order_by(MetricPoint.timestamp)
    )
    metrics = metrics_result.scalars().all()

    # Fetch events for this incident
    events_result = await db.execute(
        select(EventLog).where(EventLog.incident_id == incident_id).order_by(EventLog.timestamp)
    )
    events = events_result.scalars().all()

    # Build metric summaries
    metric_map: dict[str, list[float]] = {}
    for m in metrics:
        metric_map.setdefault(m.metric_name, []).append(m.value)

    # Detect patterns
    probable_causes = []
    evidence = []
    suggested_steps = []

    # Rule 1: High CPU + topic drop => resource contention
    cpu_values = metric_map.get("cpu_percent", [])
    topic_rate_values = metric_map.get("topic_rate_hz", [])

    if cpu_values and max(cpu_values) > 85:
        evidence.append(
            {
                "signal": "cpu_percent",
                "peak": max(cpu_values),
                "threshold": 85,
                "description": f"CPU peaked at {max(cpu_values):.1f}%",
            }
        )
        if topic_rate_values and min(topic_rate_values) < 5:
            probable_causes.append(
                {
                    "cause": "Resource contention",
                    "confidence": 0.85,
                    "description": "High CPU utilization caused topic publish rate degradation. "
                    "The system was under compute pressure, leading to dropped or delayed messages.",
                }
            )
            evidence.append(
                {
                    "signal": "topic_rate_hz",
                    "minimum": min(topic_rate_values),
                    "threshold": 5,
                    "description": f"Topic rate dropped to {min(topic_rate_values):.1f} Hz",
                }
            )
            suggested_steps.append("Profile CPU-intensive nodes to identify bottlenecks")
            suggested_steps.append("Consider offloading inference to GPU or dedicated process")
            suggested_steps.append("Add CPU resource limits to non-critical containers")

    # Rule 2: Rising temperature + latency spike => thermal throttling
    temp_values = metric_map.get("gpu_temp_c", []) or metric_map.get("cpu_temp_c", [])
    latency_values = metric_map.get("inference_latency_ms", [])

    if temp_values and max(temp_values) > 75:
        evidence.append(
            {
                "signal": "temperature",
                "peak": max(temp_values),
                "threshold": 75,
                "description": f"Temperature peaked at {max(temp_values):.1f}°C",
            }
        )
        if latency_values and max(latency_values) > 100:
            probable_causes.append(
                {
                    "cause": "Thermal throttling",
                    "confidence": 0.80,
                    "description": "GPU/CPU temperature exceeded thermal limits, causing frequency throttling "
                    "and increased inference latency.",
                }
            )
            evidence.append(
                {
                    "signal": "inference_latency_ms",
                    "peak": max(latency_values),
                    "threshold": 100,
                    "description": f"Inference latency peaked at {max(latency_values):.1f}ms",
                }
            )
            suggested_steps.append("Improve device cooling or reduce ambient temperature exposure")
            suggested_steps.append("Lower inference frequency or model complexity")
            suggested_steps.append("Add thermal monitoring alerts before throttling threshold")

    # Rule 3: Node crash + watchdog timeout => process failure chain
    crash_events = [
        e for e in events if "crash" in e.message.lower() or "exit" in e.message.lower()
    ]
    watchdog_events = [
        e for e in events if "watchdog" in e.message.lower() or "timeout" in e.message.lower()
    ]

    if crash_events and watchdog_events:
        probable_causes.append(
            {
                "cause": "Process failure chain",
                "confidence": 0.75,
                "description": "A node crash triggered cascading watchdog timeouts. "
                "The initial failure propagated to dependent nodes.",
            }
        )
        evidence.append(
            {
                "signal": "events",
                "crash_count": len(crash_events),
                "watchdog_count": len(watchdog_events),
                "description": f"{len(crash_events)} crash events, {len(watchdog_events)} watchdog timeouts",
            }
        )
        suggested_steps.append("Check crash logs for the first node that failed")
        suggested_steps.append("Review node dependency graph for cascading failure paths")
        suggested_steps.append("Add restart policies and health checks to critical nodes")

    # Rule 4: Version regression — deployment/version keyword in events + latency increase
    deployment_events = [
        e
        for e in events
        if any(
            kw in e.message.lower()
            for kw in ("deployment", "version", "config", "v2.", "v1.", "deploy")
        )
    ]
    regression_events = [
        e
        for e in events
        if any(
            kw in e.message.lower()
            for kw in ("regression", "abort", "missed", "baseline", "higher than")
        )
    ]

    if deployment_events and regression_events:
        probable_causes.append(
            {
                "cause": "Version regression",
                "confidence": 0.82,
                "description": "A recent deployment introduced a configuration or behavior change "
                "that degraded system performance. Event logs reference both a new deployment "
                "and degraded behavior compared to the previous version.",
            }
        )
        evidence.append(
            {
                "signal": "deployment_events",
                "count": len(deployment_events),
                "description": f"{len(deployment_events)} deployment/version-related events detected",
            }
        )
        evidence.append(
            {
                "signal": "regression_events",
                "count": len(regression_events),
                "description": f"{len(regression_events)} events indicating degraded behavior vs baseline",
            }
        )
        suggested_steps.append(
            "Diff the configuration between the current and previous deployment versions"
        )
        suggested_steps.append("Roll back to the previous version and verify the issue resolves")
        suggested_steps.append("Check for changed parameters (frequencies, thresholds, timeouts)")
        suggested_steps.append("Add deployment-gated regression tests for critical metrics")

    # Rule 5: Mission abort pattern
    abort_events = [
        e
        for e in events
        if any(
            kw in e.message.lower() for kw in ("abort", "emergency stop", "e-stop", "mission fail")
        )
    ]
    if abort_events:
        evidence.append(
            {
                "signal": "mission_abort",
                "count": len(abort_events),
                "description": f"{len(abort_events)} mission abort / emergency stop events",
            }
        )
        if not any(c["cause"] == "Version regression" for c in probable_causes):
            suggested_steps.append("Review mission parameters and abort trigger conditions")

    # Rule 6: Inference latency degradation (without thermal cause)
    if latency_values and max(latency_values) > 50 and not temp_values:
        if max(latency_values) / (min(latency_values) + 0.01) > 2:
            evidence.append(
                {
                    "signal": "inference_latency_ms",
                    "peak": max(latency_values),
                    "baseline": min(latency_values),
                    "description": f"Inference latency degraded from {min(latency_values):.0f}ms to {max(latency_values):.0f}ms ({max(latency_values) / max(min(latency_values), 1):.1f}x increase)",
                }
            )

    # Rule 7: Error log spike
    error_events = [e for e in events if e.level.value in ("error", "fatal")]
    if len(error_events) > 3:
        evidence.append(
            {
                "signal": "error_logs",
                "count": len(error_events),
                "description": f"{len(error_events)} error/fatal log entries during incident",
            }
        )

    # AI layer rules (AI-001, AI-002, ...)
    # These query the inference / OOD tables and append findings in the same format.
    for ai_rule in _AI_RULES:
        finding = await ai_rule.evaluate(incident_id, db)
        if finding:
            probable_causes.append(
                {
                    "cause": finding["cause"],
                    "confidence": finding["confidence"],
                    "description": finding["description"],
                    "rule_id": finding["rule_id"],
                }
            )
            evidence.extend(finding.get("evidence", []))
            suggested_steps.extend(finding.get("suggested_steps", []))

    # Fallback if no rules matched
    if not probable_causes:
        probable_causes.append(
            {
                "cause": "Unknown — manual investigation needed",
                "confidence": 0.3,
                "description": "No clear pattern matched the available telemetry. "
                "Manual review of logs and metrics is recommended.",
            }
        )
        suggested_steps.append("Review the full event log chronologically")
        suggested_steps.append("Check for external factors (network, power, physical environment)")

    # Sort by confidence
    probable_causes.sort(key=lambda x: x["confidence"], reverse=True)

    # Collect evidence signal descriptions (for LLM prompt)
    evidence_signals = [e.get("description", "") for e in evidence if e.get("description")]

    # Generate terse 2-sentence summary via Claude Haiku (falls back to rules text if no API key)
    summary = await generate_llm_summary(
        incident_title=incident_title or str(incident_id),
        top_cause=probable_causes[0],
        evidence_signals=evidence_signals,
    )

    return {
        "summary": summary,
        "probable_causes": probable_causes,
        "evidence": evidence,
        "suggested_steps": suggested_steps,
        "metrics_analyzed": len(metrics),
        "events_analyzed": len(events),
    }
