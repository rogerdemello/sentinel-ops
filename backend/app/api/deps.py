"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from app.db.repository import DEFAULT_TENANT, Repository, get_repository
from app.graph.topology import seed_dependencies, seed_services


def tenant_repo(request: Request) -> Repository:
    """Resolve the per-request, tenant-scoped repository.

    The tenant id is set by the auth middleware from the ``X-Tenant-Id`` header
    (default: ``"default"`` — the tenant the live simulator runs against). A fresh
    tenant gets the shared service catalog seeded lazily so its dashboard renders,
    while its incidents/predictions/telemetry remain fully isolated from others'.
    """
    tid = getattr(request.state, "tenant_id", DEFAULT_TENANT)
    repo = get_repository(tid)
    if tid != DEFAULT_TENANT and not repo.list_services():
        for svc in seed_services():
            repo.add_service(svc)
        for dep in seed_dependencies():
            repo.add_dependency(dep)
    return repo
