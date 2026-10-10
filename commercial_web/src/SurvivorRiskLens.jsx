import React, { useMemo, useState } from 'react'
import { AlertTriangle, CalendarDays, ShieldAlert, Users } from 'lucide-react'

const RISK_NAMES = {
  ROAD_FAVORITE: 'On the road',
  WEAK_FORM: 'Weak recent results',
  NEG_POINT_DIFF: 'Negative point difference',
  WIND: 'Wind forecast flag',
  PRECIP: 'Rain/snow forecast flag',
  REST_DISADVANTAGE: 'Rest disadvantage',
}

function matchupFlags(row) {
  return [...new Set(String(row?.risk_signals || '').split('|').map(s => s.trim())
    .filter(s => s && !s.includes('STALE_PRIMARY_MARKET') && !s.includes('PRIMARY_MARKET_PRICE_STALE')))]
    .slice(0, 5)
    .map(code => RISK_NAMES[code] || code.replaceAll('_', ' ').toLowerCase())
}

function nextMatchup(schedule, week) {
  const parts = String(schedule || '').split(' | ').map(s => s.trim())
  const found = parts.find(s => s.startsWith(`W${week} `))
  return found ? found.replace(/^W\d+ ([AH]) vs /, (_, side) => side === 'H' ? 'Home vs ' : 'Away vs ') : null
}

export default function SurvivorRiskLens({
  week, boardWeek, ruleConfirmed, candidates = [], usedTeams = [], historical = {}, currentPicks = [],
}) {
  const [slots, setSlots] = useState({})
  const [manualHolds, setManualHolds] = useState([])
  const used = useMemo(() => new Set(usedTeams), [usedTeams])
  const validWeek = Number.isInteger(Number(week)) && Number(week) === Number(boardWeek)
  const available = validWeek
    ? candidates.filter(r => r?.team && r?.opponent && !used.has(r.team))
    : []
  const byTeam = new Map(available.map(r => [r.team, r]))
  const preferred = Number(week) === 5
    ? ['Cincinnati Bengals', 'Houston Texans', 'Jacksonville Jaguars']
    : available.slice(0, 3).map(r => r.team)
  const defaultTeams = [...preferred.filter(team => byTeam.has(team)), ...available.map(r => r.team)]
    .filter((team, i, rows) => rows.indexOf(team) === i).slice(0, 3)
  const chosen = defaultTeams.map((team, i) => byTeam.get(byTeam.has(slots[i]) ? slots[i] : team))
    .filter(Boolean)
  const historyReady = historical?.status === 'HISTORICAL_PRIOR_WEEK_ONLY' &&
    Number(historical.source_week) < Number(week) && Number(historical.sample_size) > 0
  const historyByTeam = new Map((historyReady && Array.isArray(historical.teams) ? historical.teams : [])
    .map(row => [row.team, row]))
  const nextWeek = Number(week) + 1
  const nextWeekDouble = ruleConfirmed && [3, 6, 9, 12].includes(nextWeek)
  const saveCandidates = available
    .filter(r => ['SAVE_VALUE', 'SOME_FUTURE_VALUE'].includes(r.future_value_label) &&
      nextMatchup(r.future_schedule, nextWeek))
    .sort((a, b) => (Number(b.future_value_index) || 0) - (Number(a.future_value_index) || 0))
    .slice(0, 3)

  return (
    <section aria-label="Risk-first Survivor comparison" className="rounded-3xl border border-[#BFD7EE] bg-[#F3F8FD] p-4 shadow-soft md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <p className="eyebrow">Survivor strategy · Your risk lens</p>
          <h2 className="mt-1 text-xl font-black text-slate-950 md:text-2xl">Beyond the biggest favorite</h2>
          <p className="mt-2 text-xs font-medium leading-5 text-slate-600 md:text-sm">
            Compare why teams can lose, who has already burned them, and whether to save them.
            This is a what-if research view, not a prediction or submitted pick.
          </p>
        </div>
        <span className="rounded-full border border-[#BDD6EF] bg-white px-3 py-1.5 text-[10px] font-black text-blue-900">
          RISK FIRST · NOT SPREAD RANKED
        </span>
      </div>

      {historyReady ? (
        <p className="mt-3 rounded-xl border border-blue-200 bg-white p-3 text-xs leading-5 text-slate-700">
          <Users size={14} className="mr-1 inline text-blue-700" />
          <b>Actual prior pool history:</b> {historical.sample_size} entries marked active or unconfirmed on the imported Week {historical.source_week} sheet.
          Figures below show teams <b>already used before Week {week}</b> — not how many will pick them in Week {week}.
        </p>
      ) : (
        <p className="mt-3 rounded-xl border border-amber-200 bg-white p-3 text-xs font-semibold leading-5 text-amber-900">
          Current pool ownership is not verified. Prior-week usage is {historical?.status === 'PRIOR_WEEK_SNAPSHOT_REQUIRED' ? 'not usable for this comparison' : 'temporarily unavailable'}. No crowd-pick percentage will be invented.
        </p>
      )}

      {!validWeek || !available.length ? (
        <p className="mt-3 rounded-xl bg-white p-4 text-sm font-semibold text-amber-900">
          <AlertTriangle size={16} className="mr-1 inline" />
          Current-week candidates are not verified. Wait for the correct weekly board.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            {defaultTeams.map((team, i) => (
              <label key={i} className="block text-[11px] font-black text-slate-700">
                Compare team {i + 1}
                <select
                  aria-label={`Compare team ${i + 1}`}
                  className="mt-1 w-full min-w-0 rounded-xl border border-[#C7D7E7] bg-white px-3 py-2 text-xs font-bold text-slate-950"
                  value={chosen[i]?.team || team}
                  onChange={e => setSlots(previous => ({ ...previous, [i]: e.target.value }))}
                >
                  {available.map(r => <option key={r.team} value={r.team}>{r.team}</option>)}
                </select>
              </label>
            ))}
          </div>
          <div className="mt-3 grid gap-3 lg:grid-cols-3">
            {chosen.map((row, i) => {
              const flags = matchupFlags(row)
              const historicalUsage = historyByTeam.get(row.team)
              const held = manualHolds.includes(row.team)
              return (
                <article key={`${row.team}:${i}`} className={`min-w-0 rounded-2xl border p-4 ${held ? 'border-amber-300 bg-amber-50' : 'border-slate-200 bg-white'}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-[10px] font-black uppercase tracking-wider text-blue-700">Comparison {i + 1} · not ranked</div>
                      <h3 className="mt-1 text-base font-black text-slate-950">{row.team}</h3>
                      <p className="mt-1 text-xs font-semibold text-slate-500">vs {row.opponent}</p>
                    </div>
                    <ShieldAlert size={19} className={held ? 'shrink-0 text-amber-700' : 'shrink-0 text-blue-700'} />
                  </div>
                  <div className="mt-3 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-700">
                    <b>What could go wrong?</b>
                    <p className="mt-1">{flags.length ? flags.join(' · ') : 'No specific matchup warning verified in this feed; that does not prove the team is consistent or safe.'}</p>
                    <p className="mt-1 font-semibold text-amber-800">Current primary price and independent model advantage are not verified here.</p>
                  </div>
                  <div className="mt-3 text-xs leading-5 text-slate-700">
                    <b>Pool usage:</b>{' '}
                    {historicalUsage
                      ? `${historicalUsage.used_count} of ${historical.sample_size} entries had already used this team (${historicalUsage.previously_used_share_pct}%)`
                      : 'Previous-week team usage unavailable'}
                  </div>
                  <div className="mt-2 text-xs leading-5 text-slate-700">
                    <b>Save for later:</b> {String(row.future_value_label || 'Unverified').replaceAll('_', ' ').toLowerCase()}
                    {nextMatchup(row.future_schedule, nextWeek)
                      ? ` · Week ${nextWeek}: ${nextMatchup(row.future_schedule, nextWeek)}`
                      : ` · Week ${nextWeek} matchup not listed in this board`}
                  </div>
                  <button
                    type="button"
                    aria-pressed={held}
                    className={`mt-3 rounded-xl border px-3 py-2 text-xs font-black ${held ? 'border-amber-300 bg-white text-amber-900' : 'border-blue-200 bg-blue-50 text-blue-800'}`}
                    onClick={() => setManualHolds(before => held ? before.filter(team => team !== row.team) : [...before, row.team])}
                  >
                    {held ? 'Remove my concern' : 'Mark as too risky for me'}
                  </button>
                </article>
              )
            })}
          </div>
        </>
      )}

      <div className="mt-4 rounded-xl border border-[#B7D2EB] bg-white p-3 text-xs leading-5 text-slate-700">
        <CalendarDays size={15} className="mr-1 inline text-blue-700" />
        <b>Next-week planning:</b> {nextWeekDouble
          ? `Week ${nextWeek} requires TWO different unused teams. Don't spend both of your strongest future options this week.`
          : `Check Week ${nextWeek} opponents before spending a team today.`}
        {saveCandidates.length > 0 && <p className="mt-1">
          Teams with schedule-based future value: {saveCandidates.map(r =>
            `${r.team} (${nextMatchup(r.future_schedule, nextWeek)})`).join(' · ')}.
          These are planning notes, not future-week forecasts.
        </p>}
        {currentPicks.length > 0 && <p className="mt-1 font-semibold text-amber-900">Your private pick already has {currentPicks.length} team(s) saved. This comparison does not change them.</p>}
        <p className="mt-1 text-slate-500">Your concern markers are temporary in this view. You must save your official pick separately and receive the pool organizer's acknowledgement.</p>
      </div>
    </section>
  )
}
