-- Sports Zenith Survivor claim hardening
-- Customers may read only their own entry. Claim/ownership writes are server-admin only.

drop policy if exists "owners manage survivor entries" on public.survivor_entries;
create policy "owners read survivor entries"
  on public.survivor_entries
  for select
  to authenticated
  using (owner_id = auth.uid());

drop policy if exists "owners manage survivor decisions" on public.survivor_decisions;
create policy "owners read survivor decisions"
  on public.survivor_decisions
  for select
  to authenticated
  using (
    exists (
      select 1 from public.survivor_entries e
      where e.id = survivor_decisions.entry_id
        and e.owner_id = auth.uid()
    )
  );
