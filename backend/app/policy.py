"""Runtime self-healing policy.

Initialized from settings but mutable at runtime via the API, so operators can
flip autonomous mode and tune the risk ceiling without a restart.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings
from app.models import Severity

_RISK_ORDER = [Severity.low, Severity.medium, Severity.high, Severity.critical]


class Policy:
    def __init__(self) -> None:
        s = get_settings()
        self.auto_remediate: bool = s.auto_remediate
        self.max_auto_risk: Severity = Severity(s.auto_remediate_max_risk)

    def allows_auto(self, plan_max_risk: Severity) -> bool:
        if not self.auto_remediate:
            return False
        return _RISK_ORDER.index(plan_max_risk) <= _RISK_ORDER.index(self.max_auto_risk)

    def as_dict(self) -> dict:
        return {
            "auto_remediate": self.auto_remediate,
            "max_auto_risk": self.max_auto_risk.value,
        }

    def update(self, *, auto_remediate: bool | None = None,
               max_auto_risk: str | None = None) -> None:
        if auto_remediate is not None:
            self.auto_remediate = auto_remediate
        if max_auto_risk is not None:
            self.max_auto_risk = Severity(max_auto_risk)


@lru_cache
def get_policy() -> Policy:
    return Policy()
