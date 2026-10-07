import React, { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, BarChart3, Gauge, ShieldCheck, Sparkles, Target, Zap } from 'lucide-react'

const MODES = [
  {
    key: 'BEST_OVERALL',
    label: 'Best Overall',
    icon: Target,
    text: 'Best blend of projection, value, role and lineup correlation.',
  },
  {
    key: 'CASH_SAFE',
    label: 'Cash Safe',
    icon: ShieldCheck,
    text: 'Higher-floor core with extra injury and role-risk penalties.',
  },
  {
    key: 'TOURNAMENT_UPSIDE',
    label: 'Tournament Upside',
    icon: Zap,
    text: 'Ceiling-first build with stack and bring-back upside.',
  },
  {
    key: 'CONTRARIAN',
    label: 'Contrarian',
    icon: Sparkles,
    text: 'Leverage-aware when ownership exists; never fabricates ownership.',
  },
]

const money = value => {
  const n = Number(value)
  return Number.isFinite(n) ? '$' + Math.round(n).toLocaleString() : '—'
}

const number = (value, digits = 1) => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(digits) : '—'
}

const hasVerifiedOwnershipRow = row => {
  const verified = row?.verified_ownership_pct
  if (verified !== null && verified !== '' && Number.isFinite(Number(verified))) return true

  const projected = row?.projected_ownership_pct
  const source = String(row?.projected_ownership_source || '').trim().toUpperCase()
  if (
    projected !== null &&
    projected !== '' &&
    Number.isFinite(Number(projected)) &&
    source &&
    !/(HEURISTIC|MODELLED|MODELED|SHARKSNIP)/.test(source)
  ) return true

  return false
}

function freshness(value) {
  if (!value) return 'Updated time unavailable'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return 'Updated time unavailable'
  return 'Updated ' + d.toLocaleString()
}

function DfsPlayerRow({ player, locked, excluded, onLock, onExclude }) {
  const status = String(player.availability_status || 'AVAILABLE').toUpperCase()
  const risky = ['QUESTIONABLE', 'DOUBTFUL', 'OUT', 'INACTIVE'].includes(status)

  return (
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-black text-slate-950">{player.player}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-black text-slate-600">
            {player.position}
          </span>
          {risky && (
            <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-black text-amber-700">
              {status}
            </span>
          )}
        </div>
        <div className="mt-1 text-xs font-semibold text-slate-500">
          {player.team || '—'} · {money(player.salary)} · {number(player.projected_fantasy_points)} proj · {number(player.audit_value_per_1000, 2)} pts/$1K
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onLock}
          className={`rounded-xl border px-3 py-2 text-xs font-black transition ${locked ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-200'}`}
        >
          {locked ? 'LOCKED' : 'Lock'}
        </button>
        <button
          type="button"
          onClick={onExclude}
          className={`rounded-xl border px-3 py-2 text-xs font-black transition ${excluded ? 'border-rose-300 bg-rose-50 text-rose-700' : 'border-slate-200 bg-white text-slate-600 hover:border-rose-200'}`}
        >
          {excluded ? 'EXCLUDED' : 'Exclude'}
        </button>
      </div>
    </div>
  )
}

export default function DfsLineupLab() {
  const [context, setContext] = useState({ generated_at: null, datasets: { dfs: [] } })
  const [platform, setPlatform] = useState('DRAFTKINGS')
  const [mode, setMode] = useState('BEST_OVERALL')
  const [showPlayers, setShowPlayers] = useState(false)
  const [query, setQuery] = useState('')
  const [locked, setLocked] = useState([])
  const [excluded, setExcluded] = useState([])
  const [result, setResult] = useState(null)
  const [selectedLineup, setSelectedLineup] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const response = await fetch(`/ask_context.json?ts=${Date.now()}`, { cache: 'no-store' })
        if (!response.ok) throw new Error('DFS player pool is unavailable')
        const payload = await response.json()
        if (!cancelled) setContext(payload)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'DFS player pool is unavailable')
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const pool = useMemo(() => {
    return (context.datasets?.dfs || [])
      .filter(row =>
        String(row.sport || '').toUpperCase() === 'NFL' &&
        String(row.platform || '').toUpperCase() === platform &&
        row.salary != null &&
        row.projected_fantasy_points != null &&
        !['OUT', 'INACTIVE', 'INJURED_RESERVE', 'INJURED RESERVE', 'IR', 'SUSPENDED', 'PUP', 'NFI']
          .includes(String(row.availability_status || '').toUpperCase())
      )
      .sort((a, b) => Number(b.projected_fantasy_points || 0) - Number(a.projected_fantasy_points || 0))
  }, [context, platform])

  const verifiedOwnershipAvailable = useMemo(
    () => pool.some(hasVerifiedOwnershipRow),
    [pool],
  )

  const modelledOwnershipAvailable = useMemo(
    () => pool.some(row => {
      const value = row?.modelled_ownership_pct
      return value !== null && value !== '' && Number.isFinite(Number(value))
    }),
    [pool],
  )

  const visiblePlayers = useMemo(() => {
    const q = query.trim().toLowerCase()
    const rows = q
      ? pool.filter(row =>
          String(row.player || '').toLowerCase().includes(q) ||
          String(row.team || '').toLowerCase().includes(q) ||
          String(row.position || '').toLowerCase().includes(q)
        )
      : pool
    return rows.slice(0, 40)
  }, [pool, query])

  const selected = result?.lineups?.[selectedLineup] || null
  const selectedMode = MODES.find(item => item.key === mode) || MODES[0]

  const changePlatform = next => {
    setPlatform(next)
    setLocked([])
    setExcluded([])
    setResult(null)
    setSelectedLineup(0)
    setError('')
  }

  const changeMode = next => {
    setMode(next)
    setResult(null)
    setSelectedLineup(0)
    setError('')
  }

  const toggleLock = key => {
    setLocked(current => current.includes(key) ? current.filter(x => x !== key) : [...current, key])
    setExcluded(current => current.filter(x => x !== key))
    setResult(null)
  }

  const toggleExclude = key => {
    setExcluded(current => current.includes(key) ? current.filter(x => x !== key) : [...current, key])
    setLocked(current => current.filter(x => x !== key))
    setResult(null)
  }

  const build = async () => {
    if (loading || !pool.length) return

    if (mode === 'CONTRARIAN' && !verifiedOwnershipAvailable) {
      setResult({
        status: 'MODE_UNAVAILABLE',
        reason: 'Contrarian mode requires verified current slate ownership. Modelled or heuristic ownership does not unlock this mode.',
        ownership_available: false,
        verified_ownership_available: false,
        modelled_ownership_available: modelledOwnershipAvailable,
        lineups: [],
      })
      setError('')
      setSelectedLineup(0)
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await fetch('/api/dfs/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          platform,
          mode,
          locked_keys: locked,
          excluded_keys: excluded,
          alternatives: 4,
        }),
      })
      const payload = await response.json()
      if (!response.ok || payload.status === 'ERROR') throw new Error(payload.error || 'Could not build a legal lineup')

      if (payload.status === 'MODE_UNAVAILABLE') {
        setResult(payload)
        setSelectedLineup(0)
        return
      }

      if (!payload.lineups?.length) {
        throw new Error(
          `Current ${platform === 'DRAFTKINGS' ? 'DraftKings' : 'FanDuel'} projection coverage cannot form a legal Classic lineup yet. Try the other platform or wait for the next projection refresh.`
        )
      }
      setResult(payload)
      setSelectedLineup(0)
    } catch (err) {
      setResult(null)
      setError(err instanceof Error ? err.message : 'DFS optimizer failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[30px] border border-slate-200 bg-slate-950 p-6 text-white shadow-soft md:p-7">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-300">
              <Gauge size={15} /> DFS Lineup Lab
            </div>
            <h2 className="mt-2 text-3xl font-black tracking-tight md:text-4xl">
              Let the brain build the lineup.
            </h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">
              Pick a platform and style, then tap one button. You do not need to choose a single player.
              Locks and exclusions are optional.
            </p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs font-semibold text-slate-300">
            <div className="font-black text-white">{pool.length} current players</div>
            <div className="mt-1">{freshness(context.generated_at)}</div>
          </div>
        </div>
      </section>

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">1 · Platform</div>
            <div className="mt-1 text-lg font-black text-slate-950">Choose the contest site</div>
          </div>
          <div className="flex gap-2">
            {['DRAFTKINGS', 'FANDUEL'].map(item => (
              <button
                key={item}
                type="button"
                onClick={() => changePlatform(item)}
                className={`rounded-xl px-4 py-2 text-sm font-black transition ${platform === item ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-600'}`}
              >
                {item === 'DRAFTKINGS' ? 'DraftKings' : 'FanDuel'}
              </button>
            ))}
          </div>
        </div>
      </section>

      <section>
        <div>
          <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">2 · Build style</div>
          <div className="mt-1 text-lg font-black text-slate-950">What kind of lineup do you want?</div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {MODES.map(item => {
            const Icon = item.icon
            const active = item.key === mode
            const unavailable = item.key === 'CONTRARIAN' && !verifiedOwnershipAvailable
            return (
              <button
                key={item.key}
                type="button"
                disabled={unavailable}
                aria-disabled={unavailable || undefined}
                onClick={() => changeMode(item.key)}
                className={`rounded-3xl border p-5 text-left transition ${active ? 'border-emerald-300 bg-emerald-50 shadow-soft' : unavailable ? 'cursor-not-allowed border-amber-200 bg-amber-50/60 opacity-80' : 'border-slate-200 bg-white hover:border-slate-300'}`}
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-2xl ${active ? 'bg-emerald-100 text-emerald-700' : unavailable ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-600'}`}>
                  <Icon size={19} />
                </div>
                <div className="mt-4 font-black text-slate-950">{item.label}</div>
                <div className="mt-2 text-sm leading-5 text-slate-500">{item.text}</div>
                {unavailable && (
                  <div className="mt-3 text-xs font-black leading-5 text-amber-800">
                    Unavailable · verified slate ownership required.
                    {modelledOwnershipAvailable ? ' Modelled ownership exists but does not unlock this mode.' : ''}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
        <button
          type="button"
          onClick={() => setShowPlayers(value => !value)}
          className="flex w-full items-center justify-between gap-4 text-left"
        >
          <div>
            <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">Optional</div>
            <div className="mt-1 font-black text-slate-950">Customize players</div>
            <div className="mt-1 text-sm text-slate-500">Lock players you want or remove players you do not want.</div>
          </div>
          <div className="rounded-full bg-slate-100 px-3 py-1 text-xs font-black text-slate-600">
            {locked.length} locked · {excluded.length} out
          </div>
        </button>

        {showPlayers && (
          <div className="mt-5 border-t border-slate-100 pt-5">
            <input
              value={query}
              onChange={event => setQuery(event.target.value)}
              placeholder="Search player, team or position…"
              className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base font-semibold text-slate-900 outline-none transition focus:border-blue-300 focus:bg-white"
            />
            <div className="mt-4 max-h-[560px] space-y-2 overflow-y-auto pr-1">
              {visiblePlayers.map(player => {
                const key = String(player.player_key || player.player)
                return (
                  <DfsPlayerRow
                    key={key}
                    player={player}
                    locked={locked.includes(key)}
                    excluded={excluded.includes(key)}
                    onLock={() => toggleLock(key)}
                    onExclude={() => toggleExclude(key)}
                  />
                )
              })}
            </div>
          </div>
        )}
      </section>

      <section className="rounded-3xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
          <div>
            <div className="text-xs font-black uppercase tracking-[0.14em] text-blue-600">3 · Build</div>
            <div className="mt-1 text-xl font-black text-slate-950">{selectedMode.label}</div>
            <div className="mt-1 text-sm text-slate-600">No player selection required. Current locks/exclusions will be honored.</div>
          </div>
          <button
            type="button"
            onClick={build}
            disabled={loading || !pool.length || (mode === 'CONTRARIAN' && !verifiedOwnershipAvailable)}
            className="rounded-2xl bg-slate-950 px-6 py-4 text-sm font-black text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading
              ? 'BUILDING…'
              : mode === 'CONTRARIAN' && !verifiedOwnershipAvailable
                ? 'VERIFIED OWNERSHIP REQUIRED'
                : 'BUILD BEST LINEUP'}
          </button>
        </div>
      </section>

      {error && (
        <div className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm font-semibold text-rose-800">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {mode === 'CONTRARIAN' && !verifiedOwnershipAvailable && (
        <div className="flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <span>
            Contrarian mode is unavailable without verified current slate ownership.
            {modelledOwnershipAvailable ? ' Modelled heuristic ownership is present as research context, but it does not unlock leverage mode.' : ''}
            Sports Zenith does not invent or promote unverified ownership percentages.
          </span>
        </div>
      )}

      {result?.lineups?.length > 0 && (
        <section className="space-y-4">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Optimized result</p>
              <h2>{selectedMode.label} lineup</h2>
            </div>
            <span className="health-pill emerald">LEGAL BUILD · {platform}</span>
          </div>

          <div className="flex gap-2 overflow-x-auto pb-1">
            {result.lineups.map((_, index) => (
              <button
                key={index}
                type="button"
                onClick={() => setSelectedLineup(index)}
                className={`whitespace-nowrap rounded-xl px-4 py-2 text-xs font-black ${selectedLineup === index ? 'bg-slate-950 text-white' : 'border border-slate-200 bg-white text-slate-600'}`}
              >
                Lineup {index + 1}
              </button>
            ))}
          </div>

          {selected && (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                  <div className="text-xs font-black uppercase tracking-wide text-slate-400">Projected</div>
                  <div className="mt-2 text-2xl font-black text-slate-950">{number(selected.projected_points)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                  <div className="text-xs font-black uppercase tracking-wide text-slate-400">Salary used</div>
                  <div className="mt-2 text-2xl font-black text-slate-950">{money(selected.salary_used)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                  <div className="text-xs font-black uppercase tracking-wide text-slate-400">Remaining</div>
                  <div className="mt-2 text-2xl font-black text-slate-950">{money(selected.salary_remaining)}</div>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
                  <div className="text-xs font-black uppercase tracking-wide text-slate-400">Stack</div>
                  <div className="mt-2 text-base font-black text-slate-950">{String(selected.stack_pattern || '—').replaceAll('_', ' ')}</div>
                </div>
              </div>

              <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-soft">
                <table className="min-w-[900px] w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                      <th className="px-4 py-3">Slot</th>
                      <th className="px-4 py-3">Player</th>
                      <th className="px-4 py-3">Team</th>
                      <th className="px-4 py-3">Salary</th>
                      <th className="px-4 py-3">Proj</th>
                      <th className="px-4 py-3">Value</th>
                      <th className="px-4 py-3">Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.players.map((player, index) => (
                      <tr key={`${player.slot}-${player.player_key || player.player}-${index}`} className="border-b border-slate-100 align-top">
                        <td className="px-4 py-3 font-black text-slate-600">{player.slot}</td>
                        <td className="px-4 py-3">
                          <div className="font-black text-slate-950">{player.player}</div>
                          {player.locked && <div className="mt-1 text-[10px] font-black text-emerald-600">LOCKED BY YOU</div>}
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-600">{player.team || '—'}</td>
                        <td className="px-4 py-3 font-semibold text-slate-700">{money(player.salary)}</td>
                        <td className="px-4 py-3 font-black text-slate-950">{number(player.projected_fantasy_points)}</td>
                        <td className="px-4 py-3 font-semibold text-slate-700">{number(player.audit_value_per_1000, 2)}</td>
                        <td className="px-4 py-3 text-xs leading-5 text-slate-500">{player.why || 'Projection/value fit'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-500">
                <BarChart3 size={15} className="mr-2 inline text-blue-600" />
                Optimizer score is a lineup-construction score, not a probability of winning. Projections, injury status and contest information can change before lock.
              </div>
            </>
          )}
        </section>
      )}
    </div>
  )
}
