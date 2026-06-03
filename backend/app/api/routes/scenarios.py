"""Scenario injection + simulator control."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.clock import get_clock
from app.telemetry.scenario_manager import get_scenario_manager
from app.telemetry.scenarios import list_scenarios
from app.telemetry.simulator import get_simulator

router = APIRouter(prefix="/api", tags=["scenarios"])


@router.get("/scenarios")
def get_scenarios() -> dict:
    sm = get_scenario_manager()
    return {
        "scenarios": [
            {
                "key": s.key,
                "name": s.name,
                "target_service_id": s.target_service_id,
                "incident_type": s.incident_type.value,
                "severity": s.severity.value,
                "active": sm.is_active(s.key),
            }
            for s in list_scenarios()
        ]
    }


@router.post("/scenarios/{key}/trigger")
def trigger_scenario(key: str) -> dict:
    scenario = get_simulator().trigger(key)
    if scenario is None:
        raise HTTPException(status_code=404, detail=f"unknown scenario '{key}'")
    return {"triggered": key, "name": scenario.name}


@router.post("/scenarios/{key}/clear")
def clear_scenario(key: str) -> dict:
    get_scenario_manager().clear(key)
    return {"cleared": key}


@router.post("/scenarios/clear")
def clear_all() -> dict:
    get_scenario_manager().clear_all()
    return {"cleared": "all"}


@router.get("/sim/status")
def sim_status() -> dict:
    sim = get_simulator()
    return {"running": sim.running, "ticks": sim.ticks, "sim_time": get_clock().now()}


@router.post("/sim/start")
async def sim_start() -> dict:
    await get_simulator().start()
    return {"running": True}


@router.post("/sim/stop")
async def sim_stop() -> dict:
    await get_simulator().stop()
    return {"running": False}
