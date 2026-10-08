import React, { useState } from 'react'
import { CheckCircle2, ExternalLink, RefreshCw, ShieldCheck, Users } from 'lucide-react'
import { AccountButton, useAuth } from './AuthShell'

const OTHER_PLATFORMS = [
  {
    name: 'Yahoo Fantasy',
    url: 'https://football.fantasysports.yahoo.com/',
    description: 'Yahoo requires approved Fantasy API access and secure OAuth authorization. Sports Zenith linking is not active yet.',
  },
  {
    name: 'ESPN Fantasy',
    url: 'https://fantasy.espn.com/',
    description: 'ESPN private leagues do not have an authorized sign-in connection here yet. You can still use manual roster setup.',
  },
]

const currentSeason = new Date().getUTCFullYear()

export default function FantasyPlatformConnections({ onImported, onManualSetup }) {
  const { user, getAccessToken } = useAuth()
  const [username, setUsername] = useState('')
  const [busy, setBusy] = useState(false)
  const [found, setFound] = useState(null)
  const [message, setMessage] = useState('')
  const [connected, setConnected] = useState(null)
  const [savingLeague, setSavingLeague] = useState('')

  const request = async (operation, payload) => {
    const token = await getAccessToken()
    if (!token) throw new Error('Please sign in to Sports Zenith again.')
    const response = await fetch('/api/fantasy/sleeper/' + operation, {
      method: 'POST',
      headers: { 'content-type': 'application/json', authorization: 'Bearer ' + token },
      body: JSON.stringify(payload),
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(result.message || 'Could not reach Sleeper.')
    return result
  }

  const lookup = async event => {
    event?.preventDefault()
    if (!user || !username.trim() || busy) return
    setBusy(true)
    setMessage('')
    setFound(null)
    setConnected(null)
    try {
      const data = await request('lookup', {username: username.trim(), season:currentSeason})
      setFound(data)
      if (!data.leagues?.length) {
        setMessage('No NFL leagues found for that Sleeper username in ' + currentSeason + '. Check spelling or use manual setup.')
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not find your Sleeper account.')
    } finally {
      setBusy(false)
    }
  }

  const importLeague = async league => {
    if (!user || busy || savingLeague) return
    setSavingLeague(league.league_id)
    setMessage('')
    try {
      const result = await request('connect', {
        username:found.user.username,
        league_id:league.league_id,
        season:found.season,
      })
      setConnected(result)
      setMessage('Imported ' + result.roster_count + ' players from ' + result.league_name +
        '. This uses public Sleeper information; it does not verify account ownership or grant lineup-editing access.')
      onImported?.(result)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not import this league.')
    } finally {
      setSavingLeague('')
    }
  }

  return (
    <section aria-label="Fantasy platform connections" className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">Connect your leagues</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Fantasy accounts & rosters</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            Sign into Sports Zenith to save rosters here. Fantasy providers have separate accounts—only supported connections can import a team.
          </p>
        </div>
        {!user && <AccountButton />}
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[1.1fr_1fr_1fr]">
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-black text-slate-950">Sleeper NFL</h3>
            <span className="rounded-full bg-white px-2 py-1 text-[10px] font-black uppercase text-blue-700">Read-only import</span>
          </div>
          <p className="mt-2 text-xs leading-5 text-blue-950">
            Find your public Sleeper leagues by username. No Sleeper password needed. This does not authenticate your Sleeper identity.
          </p>
          <form className="mt-3 flex flex-wrap gap-2" onSubmit={lookup}>
            <input
              type="text" aria-label="Sleeper username" autoComplete="off" value={username}
              onChange={event => {
                setUsername(event.target.value); setFound(null); setConnected(null); setMessage('')
              }}
              maxLength={40} placeholder="Your Sleeper username"
              className="min-w-0 flex-1 rounded-xl border border-blue-200 bg-white px-3 py-2.5 text-sm font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
            <button type="submit" disabled={!user || !username.trim() || busy || Boolean(savingLeague)}
              className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white disabled:opacity-40">
              {busy ? 'Finding…' : 'Find leagues'}
            </button>
          </form>
          {!user && <p className="mt-2 text-[11px] font-semibold text-blue-900">Sign in to Sports Zenith first.</p>}
          <a href="https://sleeper.com/" target="_blank" rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1 text-[11px] font-black text-blue-800 underline-offset-2 hover:underline">
            Open Sleeper website <ExternalLink size={12} />
          </a>
        </div>
        {OTHER_PLATFORMS.map(platform => (
          <div key={platform.name} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-black text-slate-950">{platform.name}</h3>
              <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-black uppercase text-amber-800">Not connected</span>
            </div>
            <p className="mt-2 min-h-16 text-xs leading-5 text-slate-600">{platform.description}</p>
            <a href={platform.url} target="_blank" rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1 rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-xs font-black text-slate-800 hover:border-blue-300">
              Open official site <ExternalLink size={14} />
            </a>
          </div>
        ))}
      </div>

      {found?.leagues?.length > 0 && (
        <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/50 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <Users size={17} className="text-blue-700" />
            <h3 className="text-sm font-black text-slate-950">Found {found.leagues.length} NFL league(s) for {found.user.username}</h3>
          </div>
          <p className="mt-1 text-[11px] font-semibold text-slate-500">Choose the league you want to import. You can import more than one.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {found.leagues.map(league => (
              <div key={league.league_id} className="flex flex-col justify-between gap-3 rounded-xl border border-blue-100 bg-white p-3">
                <div>
                  <div className="text-sm font-black text-slate-950">{league.name}</div>
                  <div className="mt-1 text-xs text-slate-500">{league.team_count} teams · {league.season} · {league.status}</div>
                </div>
                <button type="button" onClick={() => importLeague(league)}
                  disabled={Boolean(savingLeague) || busy}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-700 px-3 py-2.5 text-xs font-black text-white disabled:opacity-50">
                  {savingLeague === league.league_id ? <><RefreshCw size={13} className="animate-spin" /> Importing…</> :
                    connected?.provider_league_id === league.league_id ? <><CheckCircle2 size={14}/> Refresh imported roster</> :
                      'Import roster'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
      {message && <p role="status" className="mt-3 rounded-xl bg-slate-50 px-4 py-3 text-xs font-bold leading-5 text-slate-700">{message}</p>}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
        <div className="flex max-w-2xl items-center gap-2 text-xs text-slate-500">
          <ShieldCheck size={17} className="shrink-0 text-blue-600" />
          Never enter ESPN, Yahoo, or Sleeper passwords or session cookies into Sports Zenith.
        </div>
        <button type="button" onClick={onManualSetup} className="text-xs font-black text-blue-700 underline-offset-2 hover:underline">
          Use manual roster setup instead
        </button>
      </div>
    </section>
  )
}
