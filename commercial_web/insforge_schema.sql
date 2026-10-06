-- Sports HULK commercial dashboard schema draft.
-- Apply through InsForge CLI only after the project is linked.
-- Public schema only; raw provider payloads remain outside product-facing tables.

create table if not exists public.dashboard_games (
  id uuid primary key default gen_random_uuid(),
  sport text not null,
  canonical_game_id text not null unique,
  away_team text not null,
  home_team text not null,
  start_time timestamptz not null,
  status text not null check (status in ('scheduled','live','final','postponed','cancelled')),
  away_score integer,
  home_score integer,
  period text,
  clock_label text,
  prediction_label text,
  source text not null,
  source_updated_at timestamptz,
  collected_at timestamptz not null default now(),
  data_quality text not null default 'UNKNOWN'
);

create index if not exists dashboard_games_start_idx
  on public.dashboard_games(start_time desc);
create table if not exists public.predictions (
  id uuid primary key default gen_random_uuid(),
  canonical_game_id text not null references public.dashboard_games(canonical_game_id),
  sport text not null,
  prediction_type text not null,
  pick_label text,
  line numeric,
  direction text,
  confidence_label text,
  edge_label text,
  decision text not null default 'PASS',
  frozen_at timestamptz not null,
  evidence_hash text not null,
  data_status text not null default 'CURRENT',
  is_current boolean not null default true,
  graded_result text,
  created_at timestamptz not null default now()
);

create index if not exists predictions_game_idx
  on public.predictions(canonical_game_id, frozen_at desc);

create table if not exists public.evidence_factors (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null references public.predictions(id) on delete cascade,
  factor_key text not null,
  factor_label text not null,
  value_text text,
  numeric_value numeric,
  impact text not null default 'UNKNOWN',
  data_quality text not null default 'UNKNOWN',
  source text,
  source_timestamp timestamptz,
  source_reference text,
  contribution_note text,
  created_at timestamptz not null default now()
);

create table if not exists public.learning_reviews (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid not null unique references public.predictions(id) on delete cascade,
  final_result text not null,
  grade text not null,
  autopsy_summary text,
  what_was_right jsonb not null default '[]'::jsonb,
  what_was_wrong jsonb not null default '[]'::jsonb,
  what_changed jsonb not null default '[]'::jsonb,
  reusable_lessons jsonb not null default '[]'::jsonb,
  reviewed_at timestamptz not null default now()
);
create table if not exists public.system_health (
  id uuid primary key default gen_random_uuid(),
  source_name text not null unique,
  status text not null check (status in ('healthy','warning','stale','issue','unknown')),
  last_success_at timestamptz,
  last_attempt_at timestamptz,
  message text,
  details jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create table if not exists public.survivor_entries (
  id uuid primary key default gen_random_uuid(),
  entry_name text not null unique,
  active boolean not null default true,
  current_week integer,
  current_pick text,
  used_teams text[] not null default '{}',
  status text not null default 'ACTIVE',
  pool_name text,
  updated_at timestamptz not null default now()
);

create table if not exists public.survivor_decisions (
  id uuid primary key default gen_random_uuid(),
  entry_id uuid not null references public.survivor_entries(id) on delete cascade,
  week integer not null,
  candidate_team text not null,
  survival_probability numeric,
  pool_ownership numeric,
  future_value numeric,
  leverage_score numeric,
  portfolio_role text,
  decision text not null default 'PASS',
  evidence_quality text not null default 'UNKNOWN',
  reason_summary text,
  evidence_hash text,
  frozen_at timestamptz not null,
  unique(entry_id, week, candidate_team, frozen_at)
);

create table if not exists public.fantasy_leagues (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid,
  platform text not null check (platform in ('manual','sleeper','cbs','yahoo','espn')),
  provider_league_id text,
  league_name text not null,
  scoring jsonb not null default '{}'::jsonb,
  roster_settings jsonb not null default '{}'::jsonb,
  sync_status text not null default 'UNKNOWN',
  synced_at timestamptz,
  source_refs jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.fantasy_rosters (
  id uuid primary key default gen_random_uuid(),
  league_id uuid not null references public.fantasy_leagues(id) on delete cascade,
  provider_team_id text,
  team_name text,
  provider_owner_id text,
  owner_name text,
  player_ids jsonb not null default '[]'::jsonb,
  starters jsonb not null default '[]'::jsonb,
  bench jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

-- Product-facing tables intentionally hold normalized evidence only.
-- Raw provider receipts remain in protected runtime/storage.
-- RLS is intentionally deferred until auth/ownership requirements are
-- confirmed in the linked InsForge project. Do not expose these tables
-- anonymously by default.
