-- Sports Zenith private Survivor claim storage
-- No public/authenticated policies: server-admin access only.

create table if not exists public.survivor_claims (
  entry_name text primary key,
  code_sha256 text not null,
  claimed_by uuid,
  claimed_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.survivor_claims enable row level security;
