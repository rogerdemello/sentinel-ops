"""Controlled evaluation of the prediction engine.

For each scenario: inject it, run the engine, and measure whether SentinelOps
opened an incident on the *correct* root service and **before** the lead metric
breached its critical threshold (the whole value proposition). A clean baseline
run measures false positives. Produces precision / recall / mean-lead-time.

Runs against fresh in-process state (resets singletons), so it must be used from
a script or test — never against the live server's running simulator.
"""

from __future__ import annotations

from statistics import mean

from app.bootstrap import seed_topology
from app.clock import get_clock
from app.config import get_settings
from app.db.repository import get_repository
from app.graph.service import get_graph
from app.models import IncidentStatus
from app.policy import get_policy
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.scenarios import SCENARIOS


def _reset() -> None:
    import app.telemetry.simulator as sim_mod

    for fn in (get_repository, get_clock, get_graph, get_scenario_manager, get_policy):
        fn.cache_clear()
    sim_mod._simulator = None


def _run_scenario(key: str, max_ticks: int) -> dict:
    from app.telemetry.simulator import get_simulator

    _reset()
    seed_topology()
    repo = get_repository()
    sim = get_simulator()
    scenario = SCENARIOS[key]
    mins_per_tick = get_settings().sim_minutes_per_tick

    get_scenario_manager().trigger(key, get_clock().now())

    detect_tick: int | None = None
    breach_tick: int | None = None
    for t in range(max_ticks):
        sim.tick()
        if breach_tick is None:
            mp = repo.latest_metric(scenario.target_service_id, scenario.primary_metric)
            if mp and mp.value >= scenario.breach_threshold:
                breach_tick = t
        if detect_tick is None:
            hit = [
                i for i in repo.list_incidents()
                if i.service_id == scenario.target_service_id
            ]
            if hit:
                detect_tick = t
        if detect_tick is not None and breach_tick is not None:
            break

    detected = detect_tick is not None
    before_breach = detected and (breach_tick is None or detect_tick <= breach_tick)
    lead_min = None
    if detected and breach_tick is not None:
        lead_min = (breach_tick - detect_tick) * mins_per_tick
    return {
        "scenario": key,
        "detected": detected,
        "correct_root": detected,  # matched on target service id by construction
        "detected_before_breach": before_breach,
        "lead_time_min": lead_min,
        "incidents_opened": len(repo.list_incidents()),
    }


def _baseline_false_positives(max_ticks: int) -> int:
    from app.telemetry.simulator import get_simulator

    _reset()
    seed_topology()
    repo = get_repository()
    sim = get_simulator()
    for _ in range(max_ticks):
        sim.tick()  # no scenario triggered
    return len(repo.list_incidents())


def evaluate(max_ticks: int = 60) -> dict:
    runs = [_run_scenario(k, max_ticks) for k in SCENARIOS]
    false_positives = _baseline_false_positives(max_ticks)

    total = len(runs)
    detected = sum(r["detected"] for r in runs)
    before = sum(r["detected_before_breach"] for r in runs)
    leads = [r["lead_time_min"] for r in runs if r["lead_time_min"] is not None]
    true_positives = detected

    recall = detected / total if total else 0.0
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives)
        else 1.0
    )
    return {
        "scenarios": total,
        "detected": detected,
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "detected_before_breach": before,
        "early_warning_rate": round(before / total, 3) if total else 0.0,
        "mean_lead_time_min": round(mean(leads), 1) if leads else None,
        "false_positives_baseline": false_positives,
        "runs": runs,
    }
