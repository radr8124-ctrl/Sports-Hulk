-- Sports Zenith production account ownership foundation
-- Mirrors the proven InsForge staging ownership model.
-- No public read policies are defined on member-owned tables.

create table if not exists public.survivor_entries (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  entry_name text not null,
  is_active boolean not null default true,
  used_teams text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique(owner_id, entry_name)
);
create index if not exists idx_survivor_owner on public.survivor_entries(owner_id);
alter table public.survivor_entries enable row level security;
create policy "owners manage survivor entries"
  on public.survivor_entries
  for all
  to authenticated
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

create table if not exists public.survivor_decisions (
  id uuid primary key default gen_random_uuid(),
  entry_id uuid not null references public.survivor_entries(id) on delete cascade,
  week integer not null,
  season integer not null,
  team text not null,
  survival_probability numeric,
  pool_ownership numeric,
  future_value numeric,
  portfolio_role text,
  confidence text,
  rationale text,
  frozen_at timestamptz not null,
  result text,
  reviewed_at timestamptz,
  unique(entry_id, season, week)
);
alter table public.survivor_decisions enable row level security;
create policy "owners manage survivor decisions"
  on public.survivor_decisions
  for all
  to authenticated
  using (
    exists (
      select 1 from public.survivor_entries e
      where e.id = survivor_decisions.entry_id
        and e.owner_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.survivor_entries e
      where e.id = survivor_decisions.entry_id
        and e.owner_id = auth.uid()
    )
  );

create table if not exists public.fantasy_leagues (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  platform text not null,
  provider_league_id text,
  league_name text not null,
  season integer not null,
  scoring jsonb not null default '{}'::jsonb,
  roster_settings jsonb not null default '{}'::jsonb,
  sync_status text not null default 'manual',
  last_synced_at timestamptz,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index if not exists idx_fantasy_owner on public.fantasy_leagues(owner_id);
alter table public.fantasy_leagues enable row level security;
create policy "owners manage fantasy leagues"
  on public.fantasy_leagues
  for all
  to authenticated
  using (owner_id = auth.uid())
  with check (owner_id = auth.uid());

create table if not exists public.fantasy_rosters (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null references public.fantasy_leagues(id) on delete cascade,
  provider_team_id text,
  team_name text,
  roster jsonb not null default '[]'::jsonb,
  starters jsonb not null default '[]'::jsonb,
  bench jsonb not null default '[]'::jsonb,
  available_players jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);
alter table public.fantasy_rosters enable row level security;
create policy "owners manage fantasy rosters"
  on public.fantasy_rosters
  for all
  to authenticated
  using (
    exists (
      select 1 from public.fantasy_leagues l
      where l.id = fantasy_rosters.league_id
        and l.owner_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.fantasy_leagues l
      where l.id = fantasy_rosters.league_id
        and l.owner_id = auth.uid()
    )
  );

create table if not exists public.fantasy_advice (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null references public.fantasy_leagues(id) on delete cascade,
  advice_type text not null,
  subject text,
  recommendation jsonb not null default '{}'::jsonb,
  rationale text,
  risk_summary text,
  data_quality text not null default 'unknown',
  generated_at timestamptz not null default now()
);
alter table public.fantasy_advice enable row level security;
create policy "owners manage fantasy advice"
  on public.fantasy_advice
  for all
  to authenticated
  using (
    exists (
      select 1 from public.fantasy_leagues l
      where l.id = fantasy_advice.league_id
        and l.owner_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1 from public.fantasy_leagues l
      where l.id = fantasy_advice.league_id
        and l.owner_id = auth.uid()
    )
  );
