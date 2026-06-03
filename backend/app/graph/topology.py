"""Seed service topology for the demo.

Models a realistic e-commerce stack:

    User -> Frontend -> API Gateway -> {Checkout, Catalog, Auth, Payments}
    Checkout -> {Orders DB, Payments, Cart Cache}
    Catalog  -> {Catalog DB}
    Auth     -> {Auth DB}
    Payments -> {Payments Gateway (edge/external)}

Business weights (users / revenue) flow downstream so the impact estimator can
translate an infrastructure failure into customer + revenue terms.
"""

from __future__ import annotations

from app.models import Dependency, Service, ServiceKind

# (id, name, kind, tier, users, revenue_per_min)
_SERVICES: list[tuple[str, str, ServiceKind, int, int, float]] = [
    ("user", "End Users", ServiceKind.edge, 0, 1_000_000, 0.0),
    ("frontend", "Web Frontend", ServiceKind.frontend, 1, 1_000_000, 0.0),
    ("gateway", "API Gateway", ServiceKind.gateway, 2, 1_000_000, 0.0),
    ("checkout", "Checkout Service", ServiceKind.service, 3, 850_000, 21_000.0),
    ("catalog", "Catalog Service", ServiceKind.service, 3, 950_000, 4_000.0),
    ("auth", "Auth Service", ServiceKind.service, 3, 1_000_000, 1_500.0),
    ("payments", "Payments Service", ServiceKind.service, 4, 850_000, 21_000.0),
    ("orders_db", "Orders Database", ServiceKind.datastore, 5, 850_000, 21_000.0),
    ("catalog_db", "Catalog Database", ServiceKind.datastore, 4, 950_000, 4_000.0),
    ("auth_db", "Auth Database", ServiceKind.datastore, 4, 1_000_000, 1_500.0),
    ("cart_cache", "Cart Cache", ServiceKind.cache, 4, 850_000, 5_000.0),
    ("pay_gw", "Payments Gateway (ext)", ServiceKind.edge, 5, 850_000, 21_000.0),
]

# (source, target, criticality)
_DEPS: list[tuple[str, str, float]] = [
    ("user", "frontend", 1.0),
    ("frontend", "gateway", 1.0),
    ("gateway", "checkout", 1.0),
    ("gateway", "catalog", 0.8),
    ("gateway", "auth", 1.0),
    ("checkout", "payments", 1.0),
    ("checkout", "orders_db", 1.0),
    ("checkout", "cart_cache", 0.6),
    ("catalog", "catalog_db", 1.0),
    ("auth", "auth_db", 1.0),
    ("payments", "pay_gw", 1.0),
    ("payments", "orders_db", 0.7),
]


def seed_services() -> list[Service]:
    return [
        Service(
            id=sid,
            name=name,
            kind=kind,
            tier=tier,
            users=users,
            revenue_per_min=rev,
        )
        for sid, name, kind, tier, users, rev in _SERVICES
    ]


def seed_dependencies() -> list[Dependency]:
    return [
        Dependency(source_id=src, target_id=tgt, criticality=crit)
        for src, tgt, crit in _DEPS
    ]
