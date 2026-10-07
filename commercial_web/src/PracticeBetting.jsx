import React, { useEffect, useMemo, useState } from 'react'
import { BookOpenCheck, FlaskConical, RotateCcw, ShieldCheck, Target, WalletCards } from 'lucide-react'
import BetMeaning, { betDisplayLabel, formatAmericanOdds } from './BetMeaning'

const STORAGE_KEY = 'sports-hulk-practice-account-v1'
const STARTING_BANKROLL = 1000
const SPORTS = ['NFL', 'MLB', 'NBA', 'NHL', 'CFB', 'CBB']
const SCORE_ENDPOINTS = Object.fromEntries(SPORTS.map(sport => [sport, `/${sport.toLowerCase()}_scores.json`]))

const money = value => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString(undefined, { style: 'currency', currency: 'USD' }) : '—'
}

const pct = value => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(1) + '%' : '—'
}

const numberOrNull = value => {
  const n = Number(value)
  return Number.isFinite(n) ? n : null
}

const signed = value => {
  const n = numberOrNull(value)
  if (n == null) return ''
  return n > 0 ? `+${n}` : String(n)
}

const initialAccount = () => ({
  starting_bankroll: STARTING_BANKROLL,
  balance: STARTING_BANKROLL,
  bets: [],
  created_at: new Date().toISOString(),
})

function loadAccount() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || 'null')
    if (saved && Number.isFinite(Number(saved.balance)) && Array.isArray(saved.bets)) return saved
  } catch {}
  return initialAccount()
}

function americanProfit(stake, odds) {
  const s = Number(stake)
  const o = Number(odds)
  if (!Number.isFinite(s) || !Number.isFinite(o) || s <= 0 || o === 0) return 0
  return o > 0 ? s * (o / 100) : s * (100 / Math.abs(o))
}

function normalizeGames(payload, league) {
  const source = league === 'MLB'
    ? [
        ...(payload.today_games || []),
        ...(payload.next_games || []),
        ...(payload.recent_games || []),
      ]
    : (payload.games || [])

  const seen = new Set()
  return source.flatMap(game => {
    const eventId = String(game.event_id ?? game.gamePk ?? '')
    if (!eventId) return []
    const key = `${league}|${eventId}`
    if (seen.has(key)) return []
    seen.add(key)

    return [{
      ...game,
      league,
      event_id: eventId,
      start_time: game.start_time || game.gameDate || null,
      away_abbr: game.away_abbr || game.away || 'AWAY',
      home_abbr: game.home_abbr || game.home || 'HOME',
      away: game.away || game.away_abbr || 'Away',
      home: game.home || game.home_abbr || 'Home',
    }]
  })
}

function legacyGameKey(game) {
  const away = String(game.away_abbr || '').toUpperCase()
  const home = String(game.home_abbr || '').toUpperCase()
  return away && home ? `${away}@${home}` : ''
}

function findGameForBet(bet, games) {
  if (bet.event_id && bet.sport) {
    const exact = games.find(game =>
      String(game.league) === String(bet.sport)
      && String(game.event_id) === String(bet.event_id)
    )
    if (exact) return exact
  }

  if (bet.game_key) {
    return games.find(game =>
      String(game.league) === 'NFL'
      && legacyGameKey(game) === String(bet.game_key)
    ) || null
  }

  return null
}

function gradePracticeBet(bet, game) {
  const awayScore = numberOrNull(game.away_score)
  const homeScore = numberOrNull(game.home_score)
  if (awayScore == null || homeScore == null) return null

  const market = String(bet.market || 'MONEYLINE').toUpperCase()
  const side = String(bet.selection_key || '').toUpperCase()
  const line = numberOrNull(bet.line)

  if (market === 'MONEYLINE') {
    if (awayScore === homeScore) {
      return { grade: 'PUSH', explanation: `The game ended tied ${awayScore}-${homeScore}, so the moneyline pushes.` }
    }

    if (side === 'HOME' || side === 'AWAY') {
      const selectedScore = side === 'HOME' ? homeScore : awayScore
      const opponentScore = side === 'HOME' ? awayScore : homeScore
      const grade = selectedScore > opponentScore ? 'WIN' : 'LOSS'
      return {
        grade,
        explanation: `${bet.selection} ${grade === 'WIN' ? 'won' : 'did not win'} the game, ${selectedScore}-${opponentScore}.`,
      }
    }

    const winner = awayScore > homeScore ? String(game.away || '') : String(game.home || '')
    const grade = winner.trim().toLowerCase() === String(bet.selection || '').trim().toLowerCase() ? 'WIN' : 'LOSS'
    return {
      grade,
      explanation: `${winner || 'The winning team'} won ${Math.max(awayScore, homeScore)}-${Math.min(awayScore, homeScore)}.`,
    }
  }

  if (market === 'SPREAD' && line != null && ['HOME', 'AWAY'].includes(side)) {
    const selectedScore = side === 'HOME' ? homeScore : awayScore
    const opponentScore = side === 'HOME' ? awayScore : homeScore
    const adjusted = selectedScore + line
    const grade = adjusted > opponentScore ? 'WIN' : adjusted < opponentScore ? 'LOSS' : 'PUSH'
    const margin = selectedScore - opponentScore
    return {
      grade,
      explanation: `${bet.selection} finished with a ${margin >= 0 ? '+' : ''}${margin}-point margin. With ${signed(line)} applied, this spread ${grade === 'WIN' ? 'covers' : grade === 'PUSH' ? 'pushes' : 'does not cover'}.`,
    }
  }

  if (market === 'TOTAL' && line != null && ['OVER', 'UNDER'].includes(side)) {
    const combined = awayScore + homeScore
    const grade = combined === line
      ? 'PUSH'
      : side === 'OVER'
        ? (combined > line ? 'WIN' : 'LOSS')
        : (combined < line ? 'WIN' : 'LOSS')

    return {
      grade,
      explanation: `The teams combined for ${combined} points. ${side} ${line} ${grade === 'WIN' ? 'wins' : grade === 'PUSH' ? 'pushes' : 'loses'}.`,
    }
  }

  return null
}

function settleAccount(account, games) {
  let balance = Number(account.balance || 0)
  let changed = false

  const bets = (account.bets || []).map(bet => {
    if (bet.status !== 'PENDING') return bet
    const game = findGameForBet(bet, games)
    if (!game || !game.final) return bet

    const result = gradePracticeBet(bet, game)
    if (!result) return bet

    const stake = Number(bet.stake || 0)
    const profit = americanProfit(stake, bet.odds)
    if (result.grade === 'WIN') balance += stake + profit
    if (result.grade === 'PUSH') balance += stake
    changed = true

    return {
      ...bet,
      status: result.grade,
      result: `${game.away_abbr} ${game.away_score} - ${game.home_score} ${game.home_abbr}`,
      grade_explanation: result.explanation,
      profit_loss: result.grade === 'WIN' ? Number(profit.toFixed(2)) : result.grade === 'LOSS' ? -stake : 0,
      settled_at: new Date().toISOString(),
    }
  })

  return changed ? { ...account, balance: Number(balance.toFixed(2)), bets } : account
}

function sortGames(rows) {
  return [...rows].sort((a, b) => {
    const stateRank = game => game.live ? 1 : game.final ? 2 : 0
    return stateRank(a) - stateRank(b)
      || String(a.start_time || '').localeCompare(String(b.start_time || ''))
  })
}

function gameLabel(game) {
  return `${game.away_abbr || game.away} @ ${game.home_abbr || game.home} · ${game.status || 'Scheduled'}`
}

export default function PracticeBetting() {
  const [account, setAccount] = useState(loadAccount)
  const [games, setGames] = useState([])
  const [message, setMessage] = useState('')
  const [mode, setMode] = useState('LEARN')
  const [sport, setSport] = useState('NFL')
  const [eventId, setEventId] = useState('')
  const [market, setMarket] = useState('MONEYLINE')
  const [selectionKey, setSelectionKey] = useState('HOME')
  const [lineInput, setLineInput] = useState('')
  const [oddsInput, setOddsInput] = useState('-110')
  const [stakeInput, setStakeInput] = useState('25')
  const [loadingScores, setLoadingScores] = useState(true)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(account))
  }, [account])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      setLoadingScores(true)
      try {
        const responses = await Promise.all(
          SPORTS.map(async league => {
            const response = await fetch(`${SCORE_ENDPOINTS[league]}?ts=${Date.now()}`, { cache: 'no-store' })
            const payload = response.ok ? await response.json() : {}
            return normalizeGames(payload, league)
          }),
        )
        const allGames = responses.flat()
        if (!cancelled) {
          setGames(allGames)
          setAccount(current => settleAccount(current, allGames))
        }
      } catch {
        if (!cancelled) setGames([])
      } finally {
        if (!cancelled) setLoadingScores(false)
      }
    }

    load()
    const timer = window.setInterval(load, 30000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const sportGames = useMemo(
    () => sortGames(games.filter(game => game.league === sport)),
    [games, sport],
  )

  useEffect(() => {
    if (sportGames.some(game => String(game.event_id) === String(eventId))) return
    const upcoming = sportGames.find(game => !game.live && !game.final)
    setEventId(String((upcoming || sportGames[0])?.event_id || ''))
  }, [sportGames, eventId])

  useEffect(() => {
    if (market === 'TOTAL') setSelectionKey('OVER')
    else setSelectionKey('HOME')
    setLineInput('')
  }, [market])

  const selectedGame = sportGames.find(game => String(game.event_id) === String(eventId)) || null
  const selectedTeam = selectedGame
    ? selectionKey === 'AWAY'
      ? selectedGame.away
      : selectedGame.home
    : ''

  const line = market === 'MONEYLINE' ? null : numberOrNull(lineInput)
  const odds = numberOrNull(oddsInput)

  const preview = {
    market,
    selection_key: selectionKey,
    selection: market === 'TOTAL' ? selectionKey : selectedTeam,
    line,
    american_odds: odds,
  }

  const validLine = market === 'MONEYLINE' || line != null
  const validOdds = odds != null && odds !== 0 && Math.abs(odds) >= 100
  const canLearn = Boolean(selectedGame && validLine && validOdds)
  const canTest = Boolean(canLearn && !selectedGame.live && !selectedGame.final)

  const settled = (account.bets || []).filter(bet => ['WIN', 'LOSS', 'PUSH'].includes(bet.status))
  const wins = settled.filter(bet => bet.status === 'WIN').length
  const losses = settled.filter(bet => bet.status === 'LOSS').length
  const pushes = settled.filter(bet => bet.status === 'PUSH').length
  const pending = (account.bets || []).filter(bet => bet.status === 'PENDING')
  const risked = pending.reduce((sum, bet) => sum + Number(bet.stake || 0), 0)
  const pnl = Number(account.balance || 0) + risked - Number(account.starting_bankroll || STARTING_BANKROLL)
  const roi = Number(account.starting_bankroll) > 0 ? (pnl / Number(account.starting_bankroll)) * 100 : 0

  const placePracticeBet = () => {
    if (!canTest || !selectedGame) {
      setMessage(selectedGame?.live || selectedGame?.final
        ? 'Practice bets must be added before the game starts.'
        : 'Complete the game, market, line and price first.')
      return
    }

    const stake = Number(stakeInput)
    if (!Number.isFinite(stake) || stake <= 0) {
      setMessage('Enter a valid practice stake.')
      return
    }
    if (stake > Number(account.balance)) {
      setMessage('That practice stake is larger than your available bankroll.')
      return
    }

    const key = [
      sport,
      selectedGame.event_id,
      market,
      selectionKey,
      line == null ? '' : line,
      odds,
    ].join('|')

    const duplicatePending = (account.bets || []).some(
      bet => bet.status === 'PENDING' && bet.bet_key === key,
    )
    if (duplicatePending) {
      setMessage('That exact practice bet is already pending.')
      return
    }

    const newBet = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      bet_key: key,
      sport,
      event_id: String(selectedGame.event_id),
      game_key: legacyGameKey(selectedGame),
      market,
      selection: preview.selection,
      selection_key: selectionKey,
      line,
      odds,
      stake: Number(stake.toFixed(2)),
      potential_profit: Number(americanProfit(stake, odds).toFixed(2)),
      status: 'PENDING',
      placed_at: new Date().toISOString(),
      practice_only: true,
      away: selectedGame.away,
      home: selectedGame.home,
    }

    setAccount(current => ({
      ...current,
      balance: Number((Number(current.balance) - stake).toFixed(2)),
      bets: [newBet, ...(current.bets || [])],
    }))
    setMessage(`Practice bet added: ${betDisplayLabel(newBet)} ${formatAmericanOdds(odds)}.`)
  }

  const reset = () => {
    if (!window.confirm('Reset the practice bankroll and erase all practice bet history on this device?')) return
    setAccount(initialAccount())
    setMessage('Practice account reset to $1,000.')
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[30px] border border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 p-6 text-white shadow-soft md:p-7">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-start">
          <div className="max-w-3xl">
            <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-300">
              <FlaskConical size={16} /> Bet Lab
            </div>
            <h2 className="mt-2 text-3xl font-black tracking-tight md:text-4xl">
              Understand it. Test it. Learn without risking real money.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
              Build a single-game moneyline, spread or total from the connected score center. Sports Zenith explains exactly how it wins, how it loses and when it pushes before you add anything to the fake bankroll.
            </p>
          </div>
          <span className="inline-flex rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1.5 text-xs font-black text-emerald-200">
            PRACTICE ONLY · $0 REAL MONEY
          </span>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[
            ['Available', money(account.balance)],
            ['Pending risk', money(risked)],
            ['P/L', money(pnl)],
            ['Record', `${wins}-${losses}-${pushes}`],
            ['Practice ROI', pct(roi)],
          ].map(([label, value]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">{label}</div>
              <div className="mt-2 text-2xl font-black">{value}</div>
            </div>
          ))}
        </div>
      </section>

      {message && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-950">
          {message}
        </div>
      )}

      <section className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div>
            <p className="eyebrow">Build your own</p>
            <h2>What bet do you want to understand?</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              Start from a real game in the connected score window. You can learn any listed game; only pregame selections can be added to the Practice Bankroll.
            </p>
          </div>
          <div className="flex gap-2 rounded-2xl border border-slate-200 bg-slate-50 p-2">
            <button
              type="button"
              onClick={() => setMode('LEARN')}
              className={`min-h-11 rounded-xl px-4 text-sm font-black ${mode === 'LEARN' ? 'bg-slate-950 text-white' : 'text-slate-500'}`}
            >
              LEARN THIS BET
            </button>
            <button
              type="button"
              onClick={() => setMode('TEST')}
              className={`min-h-11 rounded-xl px-4 text-sm font-black ${mode === 'TEST' ? 'bg-slate-950 text-white' : 'text-slate-500'}`}
            >
              TEST THIS BET
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="block">
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Sport</span>
            <select
              aria-label="Bet Lab sport"
              value={sport}
              onChange={event => setSport(event.target.value)}
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
            >
              {SPORTS.map(item => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>

          <label className="block md:col-span-1 xl:col-span-2">
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Game</span>
            <select
              aria-label="Bet Lab game"
              value={eventId}
              onChange={event => setEventId(event.target.value)}
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
            >
              {!sportGames.length && <option value="">No connected games in the current window</option>}
              {sportGames.map(game => (
                <option key={game.event_id} value={game.event_id}>{gameLabel(game)}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Market</span>
            <select
              aria-label="Bet Lab market"
              value={market}
              onChange={event => setMarket(event.target.value)}
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
            >
              <option value="MONEYLINE">Moneyline</option>
              <option value="SPREAD">Spread</option>
              <option value="TOTAL">Total</option>
            </select>
          </label>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="block">
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">
              {market === 'TOTAL' ? 'Side' : 'Team'}
            </span>
            <select
              aria-label="Bet Lab selection"
              value={selectionKey}
              onChange={event => setSelectionKey(event.target.value)}
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
            >
              {market === 'TOTAL' ? (
                <>
                  <option value="OVER">Over</option>
                  <option value="UNDER">Under</option>
                </>
              ) : (
                <>
                  <option value="HOME">{selectedGame?.home || 'Home team'}</option>
                  <option value="AWAY">{selectedGame?.away || 'Away team'}</option>
                </>
              )}
            </select>
          </label>

          {market !== 'MONEYLINE' && (
            <label className="block">
              <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">
                {market === 'SPREAD' ? 'Spread line' : 'Total line'}
              </span>
              <input
                aria-label="Bet Lab line"
                type="number"
                step="0.5"
                value={lineInput}
                onChange={event => setLineInput(event.target.value)}
                placeholder={market === 'SPREAD' ? '-3.5' : '47.5'}
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
              />
            </label>
          )}

          <label className="block">
            <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">American price</span>
            <input
              aria-label="Bet Lab odds"
              type="number"
              step="1"
              value={oddsInput}
              onChange={event => setOddsInput(event.target.value)}
              placeholder="-110"
              className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
            />
          </label>

          {mode === 'TEST' && (
            <label className="block">
              <span className="text-[10px] font-black uppercase tracking-[0.12em] text-slate-400">Practice stake</span>
              <input
                aria-label="Bet Lab stake"
                type="number"
                min="1"
                step="1"
                value={stakeInput}
                onChange={event => setStakeInput(event.target.value)}
                className="mt-2 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm font-black text-slate-900 outline-none"
              />
            </label>
          )}
        </div>

        {loadingScores && (
          <div className="mt-4 text-sm font-semibold text-slate-400">Loading connected games…</div>
        )}

        {selectedGame && (selectedGame.live || selectedGame.final) && (
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
            This game has already started or finished. You can still use Learn mode, but Sports Zenith will not let you add a new practice bet after kickoff.
          </div>
        )}
      </section>

      <section className="grid gap-5 lg:grid-cols-[1.05fr_.95fr]">
        <div className="rounded-[30px] border border-slate-200 bg-white p-5 shadow-soft md:p-6">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-blue-700">
            <BookOpenCheck size={15} /> What this bet means
          </div>

          {canLearn ? (
            <>
              <div className="mt-4 text-2xl font-black tracking-tight text-slate-950">{betDisplayLabel(preview)}</div>
              <div className="mt-1 text-sm font-black text-slate-600">{formatAmericanOdds(odds)}</div>
              <div className="mt-4">
                <BetMeaning row={preview} />
              </div>
            </>
          ) : (
            <div className="mt-4 rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-5 text-sm font-semibold leading-6 text-slate-500">
              Choose a connected game and complete the line/price to see exactly how the bet wins, loses and pushes.
            </div>
          )}
        </div>

        <div className="rounded-[30px] border border-slate-200 bg-slate-950 p-5 text-white shadow-soft md:p-6">
          <div className="text-xs font-black uppercase tracking-[0.14em] text-emerald-300">
            {mode === 'LEARN' ? 'Learning mode' : 'Practice test'}
          </div>
          <h3 className="mt-2 text-2xl font-black tracking-tight">
            {mode === 'LEARN' ? 'Understand before you risk anything.' : 'See what this decision would do to your bankroll.'}
          </h3>

          {mode === 'LEARN' ? (
            <div className="mt-5 space-y-3 text-sm leading-6 text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <b className="text-white">No wager is being placed.</b> This side of Bet Lab is purely educational.
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                Moneyline means the selected team must win. Spread changes the scoring margin. Total is based on both teams’ combined score.
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                Integer spreads/totals can push. Half-point lines cannot push.
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">Stake</div>
                  <div className="mt-2 text-xl font-black">{money(stakeInput)}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="text-[10px] font-black uppercase tracking-wide text-slate-500">Potential profit</div>
                  <div className="mt-2 text-xl font-black text-emerald-300">
                    {validOdds ? money(americanProfit(stakeInput, odds)) : '—'}
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={placePracticeBet}
                disabled={!canTest}
                className="mt-4 flex min-h-12 w-full items-center justify-center rounded-2xl bg-emerald-400 px-4 text-sm font-black text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                ADD TO PRACTICE BANKROLL
              </button>

              {!canTest && selectedGame && (selectedGame.live || selectedGame.final) && (
                <div className="mt-3 text-xs font-semibold leading-5 text-amber-200">
                  Practice testing closes once the connected game is live or final.
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">My practice bets</p>
            <h2>Bankroll history</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
              Final connected scores grade practice moneylines, spreads and totals automatically. This ledger never enters the official Sports Zenith performance record.
            </p>
          </div>
          <button
            type="button"
            onClick={reset}
            className="flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-slate-600"
          >
            <RotateCcw size={14} /> Reset account
          </button>
        </div>

        {(account.bets || []).length ? (
          <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-soft">
            <table className="min-w-[920px] w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Bet</th>
                  <th className="px-4 py-3">Price</th>
                  <th className="px-4 py-3">Stake</th>
                  <th className="px-4 py-3">P/L</th>
                  <th className="px-4 py-3">Result</th>
                </tr>
              </thead>
              <tbody>
                {(account.bets || []).map(bet => (
                  <tr key={bet.id} className="border-b border-slate-100 align-top">
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-black ${
                        bet.status === 'WIN' ? 'bg-emerald-50 text-emerald-700'
                          : bet.status === 'LOSS' ? 'bg-rose-50 text-rose-700'
                            : bet.status === 'PUSH' ? 'bg-slate-100 text-slate-700'
                              : 'bg-blue-50 text-blue-700'
                      }`}>{bet.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-black text-slate-950">{betDisplayLabel(bet)}</div>
                      <div className="mt-1 text-xs text-slate-400">{bet.sport || 'NFL'} · {bet.away && bet.home ? `${bet.away} @ ${bet.home}` : bet.game_key}</div>
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-700">{formatAmericanOdds(bet.odds) || '—'}</td>
                    <td className="px-4 py-3 font-bold text-slate-700">{money(bet.stake)}</td>
                    <td className={`px-4 py-3 font-black ${Number(bet.profit_loss || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {bet.status === 'PENDING' ? '—' : money(bet.profit_loss)}
                    </td>
                    <td className="px-4 py-3 text-xs font-semibold leading-5 text-slate-500">
                      <div>{bet.result || 'Waiting for final'}</div>
                      {bet.grade_explanation && <div className="mt-1 text-slate-400">{bet.grade_explanation}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
              <Target size={20} />
            </div>
            <div className="mt-4 text-lg font-black text-slate-950">No practice bets yet</div>
            <div className="mt-2 text-sm leading-6 text-slate-500">Build a bet above, switch to Test This Bet, and add it to your fake bankroll.</div>
          </div>
        )}
      </section>

      <div className="flex gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">
        <ShieldCheck size={18} className="mt-0.5 shrink-0" />
        <div>
          <b>Safe learning mode:</b> Bet Lab uses fake funds only. It is designed to teach how markets settle and let you test decision-making without placing a real wager.
        </div>
      </div>
    </div>
  )
}
