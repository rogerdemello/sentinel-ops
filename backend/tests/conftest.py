"""Reset process-wide singletons between tests for isolation.

Also neutralizes live credentials so the suite never hits real Azure OpenAI / the
production database (tests must be hermetic, free, and side-effect-free).
"""

import os

# Must run before any Settings() instantiation. Env vars override the .env file.
for _k in (
    "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
    "GEMINI_API_KEY", "DATABASE_URL", "SUPABASE_URL", "SUPABASE_SERVICE_KEY",
):
    os.environ[_k] = ""
os.environ["AUTO_REMEDIATE"] = "false"
os.environ["PERSIST_TELEMETRY"] = "false"

import pytest

import app.telemetry.simulator as sim_mod
from app.clock import get_clock
from app.db.repository import get_repository
from app.graph.service import get_graph
from app.policy import get_policy
from app.telemetry.scenario_manager import get_scenario_manager


@pytest.fixture(autouse=True)
def _reset_state():
    for fn in (get_repository, get_clock, get_graph, get_scenario_manager, get_policy):
        fn.cache_clear()
    sim_mod._simulator = None
    yield
    for fn in (get_repository, get_clock, get_graph, get_scenario_manager, get_policy):
        fn.cache_clear()
    sim_mod._simulator = None
