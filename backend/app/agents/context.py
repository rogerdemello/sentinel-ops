"""Context object passed to RCA agents.

Bundles the telemetry slice + graph context an agent needs, so agents stay pure
functions of their input and are easy to test.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import IncidentType, Service


@dataclass
class DiagnosisContext:
    failing_service: Service
    incident_type: IncidentType
    impacted_service_ids: list[str]
    # service_id -> {metric_name: value}
    metrics: dict[str, dict[str, float]]
    recent_events: list[str]  # human-readable recent event lines
    lead_metric: str | None = None  # metric whose trend triggered the prediction
    scenario_hint: str | None = None  # ground-truth hint when known (synthetic)
    recommended_actions: list[str] = field(default_factory=list)
    similar_incidents: list[str] = field(default_factory=list)  # RAG recall

    def similar_block(self) -> str:
        if not self.similar_incidents:
            return ""
        return "Similar past incidents (most relevant first):\n" + "\n".join(
            f"  - {s}" for s in self.similar_incidents
        )

    def metrics_table(self, focus_metrics: list[str] | None = None) -> str:
        lines = []
        for sid, m in self.metrics.items():
            items = m.items()
            if focus_metrics:
                items = [(k, v) for k, v in items if k in focus_metrics]
            if not items:
                continue
            metric_str = ", ".join(f"{k}={v:.1f}" for k, v in sorted(items))
            lines.append(f"  {sid}: {metric_str}")
        return "\n".join(lines)
