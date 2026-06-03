"""Catalog of remediation actions.

Each entry is a template that, bound to a target service, becomes a concrete
``RemediationAction``. v1 actions are *simulated* (see workflow.py) — they never
touch real infrastructure.
"""

from __future__ import annotations

from app.models import RemediationAction, Service, Severity

# kind -> (description template, risk)
_CATALOG: dict[str, tuple[str, Severity]] = {
    "restart": ("Rolling restart of {name} to clear degraded workers/leaked memory", Severity.low),
    "scale": ("Scale out {name} (add replicas / raise connection-pool ceiling)", Severity.low),
    "rollback": ("Roll back {name} to the previous known-good deployment", Severity.medium),
    "block_traffic": ("Apply rate-limit / WAF rule to block malicious traffic to {name}", Severity.medium),
    "isolate": ("Isolate {name} (cordon + drain) to contain a suspected compromise", Severity.high),
    "failover": ("Fail {name} over to its standby/replica in another zone", Severity.medium),
}


def build_action(kind: str, service: Service) -> RemediationAction | None:
    entry = _CATALOG.get(kind)
    if entry is None:
        return None
    template, risk = entry
    return RemediationAction(
        kind=kind,
        target_service_id=service.id,
        description=template.format(name=service.name),
        risk=risk,
    )


def known_kinds() -> list[str]:
    return list(_CATALOG.keys())
