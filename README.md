# SentinelOps AI

**Autonomous Incident Prediction & Prevention Platform.**

SentinelOps continuously analyzes operational + security telemetry to move from
reactive operations (*issue → alert → investigate → fix*) to autonomous operations
(*predict → prevent → self-heal*). It predicts incidents before they occur, runs
multi-agent root-cause analysis, estimates business/blast-radius impact, and proposes
remediation that a human approves — at which point it self-heals (simulated in v1).

> **v1 status:** a complete, working end-to-end loop on **synthetic telemetry**, built
> as a production-grade foundation. Every heavy dependency sits behind an interface so it
> can grow (NetworkX → Neo4j, statistical → deep-learning forecasting, synthetic → real
> integrations, simulated → real remediation) without rewrites.

---

## The loop

```
Synthetic telemetry ─► Forecast + anomaly detection ─► Prediction (prob + ETA)
        │                                                      │
        │                                          ┌───────────┘
        ▼                                          ▼
  Dependency graph                      Multi-agent RCA (Infra/App/Security → Orchestrator)
        │                                          │
        ├──► Blast radius ──► Business impact ($ + users)
        │                                          │
        └──────────────────► Remediation plan ──► Human approval ──► (simulated) self-heal
```

## Architecture

| Layer | Tech | Notes |
|-------|------|-------|
| Backend | Python · **FastAPI** | `backend/app` |
| Telemetry | Synthetic generator + injectable scenarios | `app/telemetry` |
| Forecasting | Trend extrapolation + `IsolationForest`/robust z-score | `app/forecasting` |
| Graph | **NetworkX** behind `GraphStore` (Neo4j-ready) | `app/graph` |
| RCA | Multi-agent + LLM router (**Azure OpenAI → Gemini failover**) | `app/agents` |
| Impact | Blast-radius-weighted users + revenue | `app/impact` |
| Remediation | Action catalog + human-approval workflow (simulated exec) | `app/remediation` |
| Persistence | **Supabase** write-through (optional); in-memory source of truth | `app/db` |
| Frontend | **React + Vite + TS + Tailwind** | `frontend/` |

**Runs with zero external setup.** Supabase and the LLM providers are optional — without
them the platform uses in-memory persistence and a deterministic heuristic RCA, so the
full demo works offline. Configure them in `.env` to enable persistence/Realtime and
genuine LLM-driven analysis.

## Quick start

```bash
# 1. Backend deps (uv recommended)
cd backend
uv venv .venv
uv pip install --python ./.venv/Scripts/python.exe -e ".[dev]"   # Windows
# (macOS/Linux: --python ./.venv/bin/python)

# 2. Frontend deps
cd ../frontend && npm install

# 3. (optional) configure providers
cp ../.env.example ../.env   # then fill in Supabase / Azure OpenAI / Gemini

# 4. Run both (from repo root)
./scripts/dev.ps1      # Windows PowerShell
./scripts/dev.sh       # macOS / Linux / Git Bash
```

- Backend: http://localhost:8000  (`/docs` for OpenAPI)
- Frontend: http://localhost:5173

Or run individually:

```bash
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev
```

## Demo

1. Open the dashboard → **Overview** (live KPIs: outages prevented, auto-healed, MTTR,
   revenue protected; plus **live time-series charts**).
2. Click a scenario under **Inject Incident Scenario** (e.g. *Orders DB connection-pool
   exhaustion*).
3. Within seconds a **Prediction** appears (probability + ETA) and an **Incident** opens.
4. Open the incident: see the **lead-signal chart** (with threshold line), **multi-agent
   RCA**, **business impact** (users + $ at risk), the **remediation plan**, and the full
   **incident timeline** (detected → RCA → impact → planned → resolved). The **Dependency
   Graph** highlights the blast radius.
5. **Approve** the remediation plan → the (simulated) action clears the scenario,
   metrics recover, and the incident resolves.

### Autonomous self-healing

Flip **Self-Healing** in the sidebar (or `PUT /api/policy {auto_remediate:true}`). The
engine then auto-executes any remediation plan whose maximum action risk is at/below the
configured ceiling (e.g. `low`), while riskier plans still wait for human approval.
Auto-healed incidents are tagged ⚡ and recorded in the timeline as `auto_healed`. This is
the platform's headline capability: prediction → prevention → self-healing, end to end.

## Scenarios

`db_pool_exhaustion` · `memory_leak` · `bad_deploy` · `auth_attack` · `cascading_failure`
(see `backend/app/telemetry/scenarios.py`).

## Persistence (Supabase)

Apply `supabase/migrations/0001_init.sql` to a Supabase/Postgres project, set
`SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in `.env`, and the backend mirrors
predictions/incidents/telemetry there (and enables Realtime for the dashboard). The
running engine remains in-memory, so this is purely additive.

## Tests

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q
```

Covers forecasting/anomaly, blast-radius graph traversal, LLM router failover, and the
full engine → incident → approval/recovery workflow.

## Safety

v1 remediation is **recommend-only with mandatory human approval**, and execution is
**simulated** (it clears the synthetic scenario; it never touches real infrastructure).
This boundary lives in `app/remediation/workflow.py` — the seam where a real,
RBAC-gated executor would later plug in.

## Roadmap (behind existing interfaces)

Real integrations (Prometheus/Loki/OTel/K8s/cloud) · Neo4j + GNN graph backend ·
deep forecasting (TFT/LSTM/Prophet) · real remediation execution with audit/RBAC ·
multi-tenant auth · alerting (PagerDuty/Slack).
