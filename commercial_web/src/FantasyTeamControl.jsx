import { CheckCircle2, ChevronRight, Clock3, RefreshCw, Settings2, ShieldCheck, Users } from 'lucide-react'

function humanize(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatDate(value) {
  if (!value) return 'Never'
  try {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return 'Unknown'
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  } catch {
    return 'Unknown'
  }
}

function countStarterSlots(settings = {}) {
  const slots = settings?.starting_slots && typeof settings.starting_slots === 'object'
    ? settings.starting_slots
    : {}
  return Object.values(slots)
    .map((value) => Number(value))
    .filter(Number.isFinite)
    .reduce((sum, value) => sum + Math.max(0, value), 0)
}

function scoringLabel(scoring = {}) {
  const preset = String(scoring?.preset || '').toLowerCase()
  if (preset === 'half_ppr') return 'Half-PPR'
  if (preset === 'standard') return 'Standard'
  if (preset === 'ppr') return 'PPR'
  return 'Not set'
}

export default function FantasyTeamControl({
  teams = [],
  selectedLeagueId = null,
  loading = false,
  onSelect,
  onManage,
}) {
  const selected = teams.find((team) => team.league_id === selectedLeagueId) || teams[0] || null

  if (loading && !selected) {
    return (
      <section className="rounded-[26px] border border-slate-200 bg-white p-5 shadow-soft">
        <div className="flex items-center gap-3 text-sm font-black text-slate-600">
          <RefreshCw size={16} className="animate-spin text-blue-600" />
          Loading your fantasy teams…
        </div>
      </section>
    )
  }

  if (!selected) {
    return (
      <section className="rounded-[26px] border border-blue-200 bg-blue-50 p-5 shadow-soft">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">Fantasy Team Control</div>
            <div className="mt-1 text-lg font-black text-slate-950">No saved fantasy team yet</div>
            <div className="mt-1 text-xs font-semibold leading-5 text-blue-900">
              Save a roster first, then Sports Zenith will use that team across Start/Sit, Waivers, IR, Defense, IDP and Ask.
            </div>
          </div>
          <button type="button" onClick={onManage} className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white">
            Save first team
          </button>
        </div>
      </section>
    )
  }

  const scoring = selected.scoring && typeof selected.scoring === 'object' ? selected.scoring : {}
  const settings = selected.roster_settings && typeof selected.roster_settings === 'object' ? selected.roster_settings : {}
  const rosterSize = Array.isArray(selected.roster) ? selected.roster.length : 0
  const starterSlots = countStarterSlots(settings)
  const irSlots = Number.isFinite(Number(settings.ir_slots)) ? Number(settings.ir_slots) : 0
  const faabBudget = scoring.faab_budget ?? settings.faab_budget
  const faabRemaining = scoring.faab_remaining ?? settings.faab_remaining
  const faabConnected = Number.isFinite(Number(faabBudget)) && Number(faabBudget) > 0
  const scoringConnected = ['ppr', 'half_ppr', 'standard'].includes(String(scoring.preset || '').toLowerCase())
  const slotsConnected = starterSlots > 0
  const setupReady = scoringConnected && slotsConnected && rosterSize > 0
  const platform = String(selected.platform || 'manual').toLowerCase()
  const manual = platform === 'manual' || String(selected.sync_status || '').toLowerCase() === 'manual'
  const lastRosterSave = selected.roster_updated_at || selected.last_synced_at || null
  const lastSettingsSave = selected.settings_updated_at || null
  const lastAnalysis = selected.last_analysis?.generated_at || null

  return (
    <section className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-soft">
      <div className="border-b border-slate-100 bg-gradient-to-r from-slate-50 to-blue-50/60 px-5 py-4 md:px-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">Fantasy Team Control</div>
              <span className="rounded-full bg-white px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.1em] text-slate-500">
                Private
              </span>
              <span className={`rounded-full px-2.5 py-1 text-[9px] font-black uppercase tracking-[0.1em] ${setupReady ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                {setupReady ? 'Core setup ready' : 'Setup needs review'}
              </span>
            </div>
            <div className="mt-2 flex flex-wrap items-end gap-x-3 gap-y-1">
              <h2 className="truncate text-2xl font-black tracking-tight text-slate-950">
                {selected.team_name || selected.league_name || 'My Team'}
              </h2>
              <div className="pb-0.5 text-xs font-semibold text-slate-400">
                {selected.league_name || 'Manual league'} · {selected.season || '—'}
              </div>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] font-semibold text-slate-500">
              <span className="inline-flex items-center gap-1.5"><Users size={13} /> {rosterSize} roster players</span>
              <span className="inline-flex items-center gap-1.5"><ShieldCheck size={13} /> {manual ? 'Manual saved roster' : humanize(selected.platform || selected.sync_status || 'Connected')}</span>
              <span className="inline-flex items-center gap-1.5"><Clock3 size={13} /> Roster updated {formatDate(lastRosterSave)}</span>
              {lastSettingsSave && <span className="inline-flex items-center gap-1.5"><Settings2 size={13} /> Settings updated {formatDate(lastSettingsSave)}</span>}
            </div>
          </div>

          <button
            type="button"
            onClick={onManage}
            className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white"
          >
            <Settings2 size={15} /> Roster & league settings
          </button>
        </div>
      </div>

      <div className="grid gap-px bg-slate-100 sm:grid-cols-2 xl:grid-cols-5">
        <div className="bg-white px-4 py-3">
          <div className="text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">Scoring</div>
          <div className={`mt-1 text-sm font-black ${scoringConnected ? 'text-slate-950' : 'text-amber-700'}`}>{scoringLabel(scoring)}</div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">{scoringConnected ? 'Connected to Start/Sit context' : 'Choose league scoring'}</div>
        </div>
        <div className="bg-white px-4 py-3">
          <div className="text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">Starter structure</div>
          <div className={`mt-1 text-sm font-black ${slotsConnected ? 'text-slate-950' : 'text-amber-700'}`}>{starterSlots} saved slots</div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">{slotsConnected ? 'Slot-aware research enabled' : 'Starter slots not configured'}</div>
        </div>
        <div className="bg-white px-4 py-3">
          <div className="text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">IR capacity</div>
          <div className="mt-1 text-sm font-black text-slate-950">{irSlots} {irSlots === 1 ? 'slot' : 'slots'}</div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">Used by personalized IR planning</div>
        </div>
        <div className="bg-white px-4 py-3">
          <div className="text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">FAAB</div>
          <div className={`mt-1 text-sm font-black ${faabConnected ? 'text-slate-950' : 'text-slate-500'}`}>
            {faabConnected ? `${faabRemaining ?? faabBudget} / ${faabBudget} left` : 'Not set'}
          </div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">{faabConnected ? 'Budget translation enabled' : 'Generic % research only'}</div>
        </div>
        <div className="bg-white px-4 py-3">
          <div className="text-[9px] font-black uppercase tracking-[0.12em] text-slate-400">Team analysis</div>
          <div className="mt-1 text-sm font-black text-slate-950">{lastAnalysis ? formatDate(lastAnalysis) : 'Not analyzed yet'}</div>
          <div className="mt-1 text-[10px] font-semibold text-slate-400">{manual ? 'Re-run Rate My Team after roster changes' : 'Last saved team-analysis run'}</div>
        </div>
      </div>

      {teams.length > 1 && (
        <div className="border-t border-slate-100 px-5 py-4 md:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Switch saved team</div>
            <div className="text-[10px] font-semibold text-slate-400">{teams.length} teams</div>
          </div>
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
            {teams.map((team) => {
              const active = team.league_id === selected.league_id
              return (
                <button
                  key={team.league_id}
                  type="button"
                  aria-label={`Switch active fantasy team to ${team.team_name || team.league_name || 'My Team'}`}
                  onClick={() => onSelect?.(team.league_id)}
                  className={`min-w-[175px] rounded-xl border px-3 py-2.5 text-left transition ${active ? 'border-blue-300 bg-blue-50' : 'border-slate-200 bg-slate-50 hover:border-blue-200'}`}
                >
                  <div className="flex items-center gap-2">
                    {active ? <CheckCircle2 size={13} className="shrink-0 text-blue-700" /> : <ChevronRight size={13} className="shrink-0 text-slate-300" />}
                    <div className="truncate text-xs font-black text-slate-950">{team.team_name || team.league_name || 'My Team'}</div>
                  </div>
                  <div className="mt-1 truncate text-[10px] font-semibold text-slate-400">{team.league_name || 'Manual league'} · {team.season || '—'}</div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
