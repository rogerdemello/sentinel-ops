-- SentinelOps AI — initial schema.
-- Apply against a Supabase/Postgres project. The backend mirrors writes here when
-- SUPABASE_URL/SERVICE_KEY are configured; the running engine itself is in-memory.

create table if not exists services (
    id              text primary key,
    name            text not null,
    kind            text not null,
    tier            int  not null default 0,
    region          text not null default 'us-east-1',
    users           bigint not null default 0,
    revenue_per_min double precision not null default 0
);

create table if not exists dependencies (
    source_id   text not null references services(id) on delete cascade,
    target_id   text not null references services(id) on delete cascade,
    kind        text not null default 'sync',
    criticality double precision not null default 1.0,
    primary key (source_id, target_id)
);

create table if not exists telemetry_metrics (
    id         text primary key,
    service_id text not null,
    name       text not null,
    value      double precision not null,
    ts         double precision not null
);
create index if not exists idx_metrics_service_ts on telemetry_metrics (service_id, name, ts);

create table if not exists telemetry_events (
    id         text primary key,
    service_id text not null,
    type       text not null,
    severity   text not null default 'info',
    message    text not null,
    ts         double precision not null,
    attributes jsonb not null default '{}'::jsonb
);
create index if not exists idx_events_ts on telemetry_events (ts);

create table if not exists predictions (
    id            text primary key,
    service_id    text not null,
    incident_type text not null,
    probability   double precision not null,
    eta_seconds   int not null,
    metric        text not null,
    summary       text not null,
    features      jsonb not null default '{}'::jsonb,
    created_at    double precision not null
);

create table if not exists incidents (
    id            text primary key,
    service_id    text not null,
    incident_type text not null,
    status        text not null default 'predicted',
    severity      text not null default 'medium',
    title          text not null default '',
    scenario_key   text,
    probability    double precision not null default 0,
    eta_seconds    int not null default 0,
    lead_metric    text,
    lead_threshold double precision,
    root_cause     text,
    diagnosis      text,
    findings       jsonb not null default '[]'::jsonb,
    impact         jsonb,
    plan           jsonb,
    timeline       jsonb not null default '[]'::jsonb,
    auto_remediated boolean not null default false,
    postmortem     text,
    created_at     double precision not null default 0,
    updated_at     double precision not null default 0
);

create table if not exists audit_log (
    id                text primary key,
    at                double precision not null,
    actor             text not null,
    role              text not null,
    incident_id       text not null,
    action_kind       text not null,
    target_service_id text not null,
    executor          text not null,
    result_status     text not null,
    detail            text not null default ''
);
create index if not exists idx_audit_at on audit_log (at);

-- Enable Realtime so the dashboard can subscribe to live changes.
do $$
begin
    if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
        alter publication supabase_realtime add table predictions;
        alter publication supabase_realtime add table incidents;
        alter publication supabase_realtime add table telemetry_metrics;
        alter publication supabase_realtime add table telemetry_events;
    end if;
exception when duplicate_object then
    null;
end $$;
