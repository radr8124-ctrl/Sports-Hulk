import React, { useEffect, useMemo, useState } from 'react'
import {verifySurvivorSavedAgainstPrivateState} from '../survivor_save_client_verification.js'

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
  currentPicks = [], entryStatus, requiredPicks, ruleConfirmed, pickWindow,
  getAccessToken, onSaved }) {
  const [picks, setPicks] = useState([])
  const [newTeam, setNewTeam] = useState('')
  const [message, setMessage] = useState('')
  const [verificationPending, setVerificationPending] = useState(false)
  const [working, setWorking] = useState(false)
  const [nowMs, setNowMs] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNowMs(Date.now()), 10_000)
    return () => window.clearInterval(timer)
  }, [])

  const savedKey = JSON.stringify(currentPicks)
  useEffect(() => {
    setPicks(Array.isArray(currentPicks) ? currentPicks : [])
    setNewTeam('')
    setMessage('')
    setVerificationPending(false)
  }, [entryName, poolWeek, savedKey])

  // Never rely on the ALIVE label to imply a still-open deadline. The server
  // derives verified week/team deadlines from original rules + ESPN identities.
  const sourceOpen = pickWindow?.status === 'WINDOW_OPEN'
  const saturdayMs = Date.parse(pickWindow?.week_saturday_deadline || '')
  const saturdayClosed = Number.isFinite(saturdayMs) && nowMs >= saturdayMs
  const allowedTeams = Array.isArray(pickWindow?.editable_teams) ? pickWindow.editable_teams : []
  const teamIsEditable = team => {
    const time = Date.parse(pickWindow?.editable_team_cutoffs?.[team] || '')
    return sourceOpen && !saturdayClosed && allowedTeams.includes(team) &&
      Number.isFinite(time) && nowMs < time
  }
  const lockedSavedPick = currentPicks.some(team => !teamIsEditable(team))
  const blocked = String(entryStatus || '').toUpperCase() !== 'ALIVE' ||
    !ruleConfirmed || !sourceOpen || saturdayClosed || lockedSavedPick
  const available = useMemo(() => NFL_TEAMS.filter(
    team => !usedTeams.includes(team) && !picks.includes(team) &&
      allowedTeams.includes(team) &&
      Number.isFinite(Date.parse(pickWindow?.editable_team_cutoffs?.[team] || '')) &&
      nowMs < Date.parse(pickWindow?.editable_team_cutoffs?.[team])
  ), [usedTeams, picks, pickWindow, allowedTeams, nowMs])
  const maxPicks = Number.isInteger(requiredPicks) && requiredPicks > 0
    ? Math.min(requiredPicks, 4) : 4
  const unchanged = JSON.stringify(picks) === savedKey

  const save = async () => {
    if (working || blocked || unchanged || verificationPending || !entryName || !poolWeek ||
      picks.length===0 || picks.some(team => !teamIsEditable(team))) return
    setWorking(true)
    setMessage('')
    const requestedTeams=[...picks]
    try {
      const bearer = await getAccessToken()
      if (!bearer) throw new Error('Sign in before saving your Survivor entry.')
      const response = await fetch('/api/survivor/save-picks', {
        method: 'POST',cache:'no-store',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + bearer },
        body: JSON.stringify({ entry_name: entryName, week: poolWeek, teams: requestedTeams }),
      })
      const receipt = await response.json()
      if (!response.ok) throw new Error(receipt.message || 'Could not save your Survivor picks.')
      // Server must first reopen the original source file and verify its
      // persisted ticket. A generic 200 response is NOT a success receipt.
      if (receipt.status!=='PERSISTED_IN_ZENITH_NOT_EXTERNAL_POOL'||
        receipt.verified_disk_readback!==true){
        setVerificationPending(true)
        throw new Error('Save could not be verified in Zenith. Refresh your entry before trying again. Do not assume external submission.')
      }
      setMessage('Checking your private Survivor record…')
      const query=new URLSearchParams({entry:entryName,save_check:String(Date.now())})
      let state=null
      try {
        const checked=await fetch('/api/survivor/state?'+query.toString(),{
          headers:{Authorization:'Bearer '+bearer},cache:'no-store',
        })
        if(checked.ok)state=await checked.json()
      } catch { /* Keep the exact requested draft, never claim it saved. */ }
      const proof=verifySurvivorSavedAgainstPrivateState({
        receipt,state,entryName,week:poolWeek,teams:requestedTeams,
      })
      if(!proof.success){
        setVerificationPending(true)
        throw new Error('Zenith reported a disk save but your private dashboard did not confirm it. Refresh before retrying. No external pool submission is verified.')
      }
      setVerificationPending(false)
      setMessage(proof.complete
        ? 'Saved and verified in Sports Zenith. Your external pool has NOT been submitted.'
        : `Partial draft saved and verified in Sports Zenith (${requestedTeams.length} of ${proof.required_picks} picks). Your external pool has NOT been submitted.`)
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
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-xl bg-slate-50 px-3 py-2 text-xs font-black text-slate-800">
            {picks.length} / {Number.isInteger(requiredPicks) && requiredPicks > 0 ? requiredPicks : '?'} pick(s)
          </span>
          {pickWindow?.status==='WINDOW_CLOSED'&&(
            <span className="rounded-lg border border-amber-300 bg-amber-50 px-2.5 py-2 text-[10px] font-black text-amber-900">DEADLINE PASSED</span>
          )}
        </div>
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-600">
        {pickWindow?.status === 'WINDOW_CLOSED'
          ? 'The verified Week 5 selection window is closed. Past picks remain available above; no new team can be added here.'
          : 'Select unused teams while the original pool window is open. Saturday 6 PM Eastern, or two hours before an earlier game. Sports Zenith saves privately but does not submit to the external pool.'}
      </p>
      {!unchanged && picks.length > 0 && (
        <p data-survivor-draft-warning role="status" className="mt-2 rounded-lg border border-[#E8C68C] bg-[#FFF8E8] px-2.5 py-2 text-[11px] font-black text-[#855A25]">
          DRAFT ONLY — selecting or adding a team does not save it.
        </p>
      )}
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
          <button type="button" onClick={save} disabled={working || unchanged || verificationPending || !picks.length}
            className="rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-black text-white disabled:opacity-40">
            {working ? 'Saving…' : 'Save picks'}
          </button>
        </div>
      )}
      {blocked && (
        <p data-survivor-pick-lock role="status" className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs font-semibold leading-5 text-amber-900">
          {entryStatus!=='ALIVE'
            ? 'Only an active Survivor entry may save picks. Reentry must be verified first.'
            : pickWindow?.status==='WINDOW_CLOSED'||saturdayClosed
              ? 'The pool deadline has passed. This entry is read-only. Recorded ALIVE status does not confirm an organizer submission or Week 5 result.'
              : lockedSavedPick
                ? 'A previously saved game is locked by its verified kickoff or pool deadline. No pick changes can be made here.'
                : 'Verified NFL fixtures, original rules or source times are unavailable. New picks are locked until the source can be checked.'}
        </p>
      )}
      {message && <p role="status" className="mt-3 text-xs font-bold text-blue-900">{message}</p>}
    </section>
  )
}
