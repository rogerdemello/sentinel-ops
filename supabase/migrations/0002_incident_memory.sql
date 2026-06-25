-- SentinelOps AI — RAG incident memory (pgvector).
-- Mirrors the schema created at runtime by backend/app/memory/store.py so a
-- managed Supabase/Postgres deploy has the table/extension ahead of time.
-- text-embedding-ada-002 produces 1536-dimensional vectors.

create extension if not exists vector;

create table if not exists incident_memory (
    id          text primary key,
    incident_id text not null,
    summary     text not null,
    severity    text,
    root_cause  text,
    embedding   vector(1536),
    created_at  double precision not null default 0
);

-- Approximate-nearest-neighbor index for cosine similarity (embedding <=> query).
create index if not exists idx_incident_memory_embedding
    on incident_memory using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
