# SentinelOps AI

**Autonomous Incident Prediction & Prevention Platform.**

SentinelOps continuously analyzes operational + security telemetry to move from
reactive operations (*issue → alert → investigate → fix*) to autonomous operations
(*predict → prevent → self-heal*). It predicts incidents before they occur, runs
multi-agent root-cause analysis, estimates business/blast-radius impact, and proposes
remediation that a human approves — at which point it self-heals (simulated in v1).

> **Status:** a complete, working end-to-end loop driven by **real host telemetry**
> (CPU / memory / disk / network sampled live via `psutil`) by default — load the
> machine and it predicts real incidents. A deterministic synthetic generator and a
> Prometheus scraper are selectable via `TELEMETRY_SOURCE`. Every heavy dependency sits
> behind an interface so it can grow (NetworkX → Neo4j, statistical → deep-learning
> forecasting, local → Prometheus/OTLP, simulated → real remediation) without rewrites.

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
| Telemetry | **Real host metrics (`psutil`)** by default · synthetic / Prometheus sources · injectable scenarios | `app/telemetry` |
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

By default remediation execution is **simulated** (clears the synthetic scenario;
touches no real infra) and requires **human approval**. Autonomous self-healing and
real executors (Kubernetes/webhook) are opt-in and **RBAC-gated**, and every executed
action is recorded in the **audit log** (`app/remediation/{workflow,executor}.py`).

## Advanced capabilities (all behind config-selected interfaces)

Every item below ships as real code that activates when its backing service is
configured and falls back safely otherwise — so the platform always runs.

| Capability | How to enable | Fallback |
|---|---|---|
| **Real LLM RCA + postmortems** | `AZURE_OPENAI_*` / `GEMINI_API_KEY` | heuristic |
| **Telemetry ingestion** | `TELEMETRY_SOURCE=prometheus` + `PROMETHEUS_URL`, or `POST /api/ingest/metrics` | synthetic |
| **Deep forecasting** | `FORECASTER=holtwinters` (or `prophet`) | trend extrapolation |
| **Neo4j graph backend** | `NEO4J_URI` + `NEO4J_PASSWORD` | in-memory NetworkX |
| **Real remediation** | `REMEDIATION_EXECUTOR=kubernetes\|webhook` + `RBAC_ENABLED=true` | simulated |
| **Audit log** | always on (`GET /api/audit`, dashboard *Audit Log*) | — |
| **Alerting** | `SLACK_WEBHOOK_URL` / `PAGERDUTY_ROUTING_KEY` / `ALERT_WEBHOOK_URL` | no-op |
| **AI postmortems** | always on (`POST /api/postmortem/{id}`) | heuristic |
| **WebSocket live push** | always on (`/ws/stream`) | REST polling |
| **API auth + tenancy** | `API_KEY` (+ `X-Tenant-Id`) | open |
| **Autonomous self-healing** | sidebar toggle / `AUTO_REMEDIATE=true` | manual approval |
| **RAG incident memory** | `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` + `DATABASE_URL` (pgvector) | disabled |
| **NL Ops Copilot** | LLM configured (`/api/copilot`, dashboard *Ops Copilot*) | state summary |
| **Evaluation harness** | `python scripts/evaluate.py` → `/api/eval/report` | — |

### Measured performance (offline eval, `scripts/evaluate.py`)

Against the five injected scenarios with a clean-baseline control:

```
recall 1.00 · precision 1.00 · 0 false positives
early-warning 80% (predicted before breach) · mean lead time 5.6 min
```

RAG: resolved incidents are embedded (ada-002) into pgvector; new incidents recall
the most similar past cases (e.g. 0.87 cosine) to ground the RCA.

## Deploy

```bash
docker compose up --build      # backend :8000 + frontend (nginx) :8080
```

Cloud blueprints: `render.yaml` at the repo root (Render — deploys backend + frontend
together; Render only detects the Blueprint at the root) and `deploy/fly.toml` (Fly.io).
Set secrets in the platform dashboard; the frontend proxies `/api` + `/ws` to the backend.

## Roadmap

Graph Neural Network failure-propagation learning · full Temporal Fusion Transformer
training pipeline · Supabase Auth UI + per-tenant RLS · Loki/OTel trace ingestion.
