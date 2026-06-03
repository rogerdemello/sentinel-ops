"""Remediation executors behind one interface.

The default ``SimulatedExecutor`` is safe (no real side effects). Real backends —
Kubernetes and an external runbook webhook — are selected via
``REMEDIATION_EXECUTOR`` and only act when their backing system is reachable.
This is the isolated seam where production automation plugs in, gated by RBAC.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic import BaseModel

from app.config import get_settings
from app.models import RemediationAction

logger = logging.getLogger(__name__)


class ExecResult(BaseModel):
    action_id: str
    kind: str
    target_service_id: str
    status: str  # simulated | ok | failed
    detail: str


class Executor:
    name = "base"

    def execute(self, action: RemediationAction) -> ExecResult:  # pragma: no cover
        raise NotImplementedError


class SimulatedExecutor(Executor):
    name = "simulated"

    def execute(self, action: RemediationAction) -> ExecResult:
        return ExecResult(
            action_id=action.id, kind=action.kind,
            target_service_id=action.target_service_id, status="simulated",
            detail=f"Simulated '{action.kind}' on {action.target_service_id} (no real infra touched).",
        )


class KubernetesExecutor(Executor):
    """Maps actions to kubectl operations. Runs only if kubectl + cluster exist."""

    name = "kubernetes"

    _CMDS = {
        "restart": ["rollout", "restart", "deployment/{svc}"],
        "scale": ["scale", "deployment/{svc}", "--replicas=5"],
        "rollback": ["rollout", "undo", "deployment/{svc}"],
        "isolate": ["cordon", "{svc}"],
    }

    def execute(self, action: RemediationAction) -> ExecResult:
        import shutil
        import subprocess

        tmpl = self._CMDS.get(action.kind)
        if not tmpl or shutil.which("kubectl") is None:
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id, status="failed",
                detail="kubectl unavailable or action unsupported by k8s executor.",
            )
        cmd = ["kubectl"] + [p.format(svc=action.target_service_id) for p in tmpl]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            ok = out.returncode == 0
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id,
                status="ok" if ok else "failed",
                detail=(out.stdout or out.stderr).strip()[:300],
            )
        except Exception as exc:  # noqa: BLE001
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id, status="failed",
                detail=str(exc)[:300],
            )


class WebhookExecutor(Executor):
    """POSTs the action to an external runbook/automation webhook."""

    name = "webhook"

    def execute(self, action: RemediationAction) -> ExecResult:
        import httpx

        url = get_settings().remediation_webhook_url
        if not url:
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id, status="failed",
                detail="REMEDIATION_WEBHOOK_URL not configured.",
            )
        try:
            resp = httpx.post(url, json=action.model_dump(mode="json"), timeout=10)
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id,
                status="ok" if resp.is_success else "failed",
                detail=f"webhook responded {resp.status_code}",
            )
        except Exception as exc:  # noqa: BLE001
            return ExecResult(
                action_id=action.id, kind=action.kind,
                target_service_id=action.target_service_id, status="failed",
                detail=str(exc)[:300],
            )


_REGISTRY = {
    "simulated": SimulatedExecutor,
    "kubernetes": KubernetesExecutor,
    "webhook": WebhookExecutor,
}


@lru_cache
def get_executor() -> Executor:
    return _REGISTRY.get(get_settings().remediation_executor, SimulatedExecutor)()
