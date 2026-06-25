# SentinelOps — Improvement Plan & Execution Log

A senior-architect review of SentinelOps produced the findings below. This file
tracks what has been **done** in this pass and the **remaining backlog**, ordered
by priority. Audits covered: backend correctness/security, frontend UX/first-time
experience, and onboarding/deploy/docs.

---

## ✅ Done in this pass (P0 + P1 + real data)

### Real-world data (replaces synthetic mock by default)
- **`app/telemetry/sources/system.py`** — a new `SystemSource` that samples **real
  host metrics via `psutil`** (CPU, memory, disk, network throughput/errors,
  connection counts) every tick, mapped onto the seeded service topology so the
  dependency-graph / blast-radius / impact story stays intact. Injected demo
  scenarios still layer on top, so you get real data by default *and* repeatable
  on-demand incidents.
- `TELEMETRY_SOURCE` now defaults to **`system`** (`config.py`); `synthetic` and
  `prometheus` remain selectable. Tests are pinned to `synthetic` for determinism.
- Verified end-to-end: real host memory pressure (~94%) genuinely drives
  `infra_failure`/`degradation` incidents with real Azure-OpenAI root-cause analysis.

### P0 — Security
- **RBAC bypass fixed.** `POST /api/remediation/{id}/approve` no longer trusts a
  client-supplied `X-Role` header. The caller's role is now derived **from the
  authenticating API key** in the auth middleware (`main.py`): `ADMIN_API_KEY` →
  `admin`, `API_KEY` → `operator`, otherwise `DEFAULT_ROLE` (least-privilege
  `operator`, configurable). See `config.py`, `main.py`, `api/routes/remediation.py`.

### P1 — Backend robustness
- **Event-loop offload** — `run_cycle` now runs via `run_in_executor` so blocking
  LLM/DB calls during incident analysis don't freeze WebSocket/HTTP (`simulator.py`).
- **Thread-safety** — `Repository` now guards all shared-collection iteration/mutation
  with a reentrant lock, eliminating the "dictionary changed size during iteration"
  race between the engine thread and the HTTP threadpool (`db/repository.py`).
- **Persistence observability** — swallowed `debug` write failures raised to
  `warning`/`error`; added a **circuit breaker** to the Postgres writer (pauses mirror
  writes for a cooldown and logs once per outage instead of flooding), with a dropped-
  write counter surfaced in `/health.persistence` (`db/writer.py`, `db/supabase_client.py`,
  `api/routes/health.py`).
- **LLM router** — `llm_max_retries` guarded with `max(1, n)` (0 no longer skips every
  provider); JSON-salvage parse failures now wrapped in `LLMError` so failover handles
  them (`agents/llm/router.py`).

### P1 — Frontend first-time-user experience
- **No more "silently broken" UI** — `usePoll` now exposes `loading`; a global
  "backend unreachable" banner renders on health-poll error (`Layout.tsx`, `usePoll.ts`).
- **Loading vs empty disambiguation** — Overview shows skeletons on first paint and a
  guided **"all nominal — trigger a scenario"** call-to-action instead of a wall of
  zeros (`Overview.tsx`, `ui.tsx` `Skeleton`/`StatSkeletons`/`EmptyState`/`Banner`).
- **No unhandled rejections** — added `.catch` + user-visible error feedback to every
  fire-and-forget handler (`AutoHealToggle`, `MetricChart`, `ScenarioBar`, `Copilot`,
  `Incidents`).
- **Crash resilience** — top-level `ErrorBoundary` wraps the app (`main.tsx`,
  `ErrorBoundary.tsx`).
- **Accessibility** — `role="switch"`/`aria-checked`/`aria-label` on the self-healing
  toggle; `<label>` on the Copilot input.
- **Polish** — typed the eval report (removed `any`), branded `<title>`, meta
  description, inline SVG favicon (`index.html`, `api.ts`).
- **Tests** — added `tests/test_system_source.py`; full suite green (25 passed).

---

## 🔴 P0 — ACTION REQUIRED BY YOU (cannot be done in code)

**Rotate the secrets in `E:\sentinelops\.env`.** The file is correctly gitignored and
was never committed, but it holds live plaintext credentials that were shared into an
audit:
- `AZURE_OPENAI_API_KEY`
- `SUPABASE_SERVICE_KEY`
- `DATABASE_URL` (contains the Postgres superuser password)

Rotate all three at their providers, then update `.env`. (The current `DATABASE_URL`
host no longer resolves — the circuit breaker now reports this cleanly in `/health`.)

---

## ✅ Done in the second pass (the deep-work backlog)

### Security
- **`/ws/stream` is now gated** — token-on-connect (query param for browsers, header
  for clients), enforced when `API_KEY` is set (`api/routes/stream.py`).
- **Auth/RBAC tests added** (`tests/test_auth_rbac.py`): the approve route can't be
  escalated by a role header, the RBAC gate denies unlisted roles, and the stream
  requires a token when keyed.

### Deployment / DevEx
- **Render blueprint fixed** — `nginx.conf` upstream is now `${BACKEND_ORIGIN}`
  (envsubst at container start); frontend Dockerfile templates it and accepts a
  build-time `VITE_API_BASE`; `api.ts` reads `VITE_API_BASE`; `render.yaml`/compose pass
  `BACKEND_ORIGIN`. A split deploy no longer 502s.
- **CI** (`.github/workflows/ci.yml`): ruff + pytest (backend), build (frontend).
- **LICENSE** (MIT), non-root + healthcheck Dockerfiles, compose healthcheck, `dev.sh`
  POSIX-first fix, and `supabase/migrations/0002_incident_memory.sql` (pgvector DDL).

### Architecture / durability
- **Tenant-aware store** — `get_repository(tenant_id)` is tenant-keyed (no-arg →
  `default`, so the engine/tests are unchanged); read routes resolve the per-request
  store via the `tenant_repo` dependency; a fresh tenant gets the service catalog but
  fully isolated incident/telemetry data. Verified live (`X-Tenant-Id: acme` → 0
  incidents, 12 services). Tests in `tests/test_tenancy.py`.
- **Boot rehydration** — `db/rehydrate.py` reloads persisted incidents/predictions from
  Postgres on startup (best-effort) so a restart resumes state.

### Correctness
- **Explicit `already_breached` flag** on `Forecast` replaces the overloaded
  `eta_seconds == 0` sentinel (engine promotes predicted→active on the flag).
- **Anomaly detection wired in** — `robust_zscore` now corroborates the trend forecast
  in the engine (additive confidence boost), making the advertised capability real.
- **Honest eval harness** — `correct_root` is now measured (incident on the true root)
  vs. `reacted` (opened anything), with a `root_accuracy` / `mis_attributed` metric;
  no longer tautological.

### UI
- **Full "Daylight" redesign** — calm parchment + sage/clay palette, editorial serif
  (Fraunces) + warm grotesque (Hanken), soft shadows, gentle motion, light-themed
  charts/graph. Cohesive, hand-crafted, accessible.

## ✅ Done in the third pass (the "remaining" backlog)

- **Per-tenant ingestion pipeline** — `/api/ingest/*` is tenant-aware, and the simulator
  now runs an isolated engine cycle for every tenant with telemetry. `run_cycle` /
  `_open_incident` / `approve_and_execute` thread the tenant repo. **Verified live**:
  pushing a breaching series for tenant `acme` opened 1 isolated incident (default had
  3 from real host metrics, zero leakage). Tests: `tests/test_per_tenant_pipeline.py`.
- **Engine robustness under real LLM load** (all found via live testing):
  - `_MAX_OPENS_PER_CYCLE` caps incidents opened per cycle so one tick never does
    unbounded blocking RCA work (deferred candidates keep predictions, open next tick).
  - **LLM call timeout** (`llm_timeout_seconds`, default 20s) on both Azure + Gemini —
    the OpenAI SDK default is 600s, so a slow/hung provider could stall a tick for
    minutes; now bounded, failing over to heuristic RCA.
  - **Parallel domain agents** — the 3 RCA agents run concurrently (independent LLM
    calls), cutting per-incident RCA wall-time ~3×. Verified: after the first slow
    detection tick, the sim runs at its normal 2s cadence.
- **Real webhook executor — verified live end-to-end.** A local receiver captured all 3
  remediation actions (POST → 202 → audit `ok`). Tests: `tests/test_executors.py`.
- **Forecaster irregular timestamps** — confirmed the trend forecaster fits on real
  timestamps (handles uneven sampling) and doesn't false-breach on flat irregular series.
  **Prometheus scrape→metric mapping** unit-tested. `tests/test_sources_and_forecast.py`.
- **Durability** — graceful-shutdown queue flush + boot rehydration; full
  write→rehydrate roundtrip integration-tested against a fake connection.
  `tests/test_durability.py`.
- **Deploy templating verified for real** — rendered `nginx.conf` with `envsubst`
  (proxy upstream resolves, nginx vars preserved), hardened with `NGINX_ENVSUBST_FILTER`,
  and confirmed `VITE_API_BASE` bakes into the production bundle.

**Test suite: 43 passing · ruff clean · frontend builds clean.**

## 🟡 Genuinely remaining (large refactor or needs infra I don't have)

- **Postgres as the *authoritative* store** (vs. durable mirror + boot rehydration, which
  is done). A true read-through/event-sourced design is a deliberate architecture change.
- **Remove global `@lru_cache` singletons → full DI.** The repository is already
  tenant-keyed; threading an injected `AppContext` through every accessor is a large,
  cross-cutting refactor best done as its own reviewed pass (deliberately NOT faked here
  with a no-op wrapper).
- **Container build + real Render/Fly deploy.** Docker isn't installed on this machine and
  there's no cloud account — the blueprints/templating are verified, but the actual image
  build and cloud run are yours to execute.
- **Live durability restart-resume against a real Postgres** — needs a reachable DB DSN
  (the one in `.env` is unreachable). Give me a DSN and I'll verify restart-resume live.
- **K8s executor** — real, but needs a cluster/`kubectl` to exercise (webhook path is the
  verified one).
