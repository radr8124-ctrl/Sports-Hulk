import React, { useEffect, useMemo, useState } from 'react'

const NFL_TEAMS = [
  'Arizona Cardinals', 'Atlanta Falcons', 'Baltimore Ravens', 'Buffalo Bills',
  'Carolina Panthers', 'Chicago Bears', 'Cincinnati Bengals', 'Cleveland Browns',
  'Dallas Cowboys', 'Denver Broncos', 'Detroit Lions', 'Green Bay Packers',
  'Houston Texans', 'Indianapolis Colts', 'Jacksonville Jaguars', 'Kansas City Chiefs',
  'Las Vegas Raiders', 'Los Angeles Chargers', 'Los Angeles Rams', 'Miami Dolphins',
  'Minnesota Vikings', 'New England Patriots', 'New Orleans Saints', 'New York Giants',
  'New York Jets', 'Philadelphia Eagles', 'Pittsburgh Steelers', 'San Francisco 49ers',
  'Seattle Seahawks', 'Tampa Bay Buccaneers', 'Tennessee Titans', 'Washington Commanders',
]

export default function SurvivorPickEditor({ entryName, poolWeek, usedTeams = [],
  currentPicks = [], entryStatus, requiredPicks, ruleConfirmed, getAccessToken, onSaved }) {
  const [picks, setPicks] = useState([])
  const [newTeam, setNewTeam] = useState('')
  const [message, setMessage] = useState('')
  const [working, setWorking] = useState(false)

  const savedKey = JSON.stringify(currentPicks)
  useEffect(() => {
    setPicks(Array.isArray(currentPicks) ? currentPicks : [])
    setNewTeam('')
    setMessage('')
  }, [entryName, poolWeek, savedKey])

  const available = useMemo(() => NFL_TEAMS.filter(
    team => !usedTeams.includes(team) && !picks.includes(team)
  ), [usedTeams, picks])
  const maxPicks = Number.isInteger(requiredPicks) && requiredPicks > 0
    ? Math.min(requiredPicks, 4) : 4
  const blocked = String(entryStatus || '').toUpperCase() !== 'ALIVE'
  const unchanged = JSON.stringify(picks) === savedKey

  const save = async () => {
    if (working || blocked || unchanged || !entryName || !poolWeek) return
    setWorking(true)
    setMessage('')
    try {
      const bearer = await getAccessToken()
      if (!bearer) throw new Error('Sign in before saving your Survivor entry.')
      const response = await fetch('/api/survivor/save-picks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + bearer },
        body: JSON.stringify({ entry_name: entryName, week: poolWeek, teams: picks }),
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Could not save your Survivor picks.')
      setMessage('Saved in Sports HULK. Your external pool has NOT been submitted.')
      onSaved?.()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Pick saving unavailable.')
    } finally {
      setWorking(false)
    }
  }

  return (
    <section aria-label="Save this week Survivor picks" className="rounded-3xl border border-blue-200 bg-white p-5 shadow-soft md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">My Survivor</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Week {poolWeek} pick(s)</h2>
          <p className="mt-1 text-xs text-slate-600">
            {entryName} · {ruleConfirmed ? 'Pool pick count confirmed' : 'Pool pick-count rule not yet confirmed'}
          </p>
        </div>
        <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-black text-slate-800">
          {picks.length} / {Number.isInteger(requiredPicks) && requiredPicks > 0 ? requiredPicks : '?'} pick(s)
        </span>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-600">
        Select your current-week teams. Used teams are excluded. Picks are saved privately in Sports HULK—not submitted to your pool.
        Picks are locked after kickoff.
      </p>
      {picks.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {picks.map(team => (
            <span key={team} className="flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-xs font-black text-blue-900">
              {team}
              {!blocked && <button type="button" onClick={() => setPicks(items => items.filter(item => item !== team))}
                aria-label={'Remove ' + team} className="rounded px-1 text-blue-700 hover:bg-blue-100">×</button>}
            </span>
          ))}
        </div>
      )}
      {!blocked && (
        <div className="mt-4 flex flex-wrap gap-2">
          <select aria-label="Choose an unused NFL team" value={newTeam}
            onChange={event => setNewTeam(event.target.value)}
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-800">
            <option value="">Choose an unused team</option>
            {available.map(team => <option key={team} value={team}>{team}</option>)}
          </select>
          <button type="button" onClick={() => { if (newTeam && picks.length < maxPicks) {
            setPicks(items => [...items, newTeam]); setNewTeam('')
          } }} disabled={!newTeam || picks.length >= maxPicks}
            className="rounded-xl border border-blue-200 px-4 py-2.5 text-sm font-black text-blue-700 disabled:opacity-40">Add</button>
          <button type="button" onClick={save} disabled={working || unchanged}
            className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white disabled:opacity-40">
            {working ? 'Saving…' : 'Save picks'}
          </button>
        </div>
      )}
      {blocked && <p className="mt-3 text-xs font-bold text-amber-800">Only an active Survivor entry may save picks. Reentry must be verified first.</p>}
      {message && <p role="status" className="mt-3 text-xs font-bold text-blue-900">{message}</p>}
    </section>
  )
}
