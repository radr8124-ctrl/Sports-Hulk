import React, { useEffect, useMemo, useState } from 'react'
import { RotateCcw, ShieldCheck, Target, WalletCards } from 'lucide-react'

const STORAGE_KEY = 'sports-hulk-practice-account-v1'
const STARTING_BANKROLL = 1000

const money = value => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toLocaleString(undefined, { style: 'currency', currency: 'USD' }) : '—'
}

const pct = value => {
  const n = Number(value)
  return Number.isFinite(n) ? n.toFixed(1) + '%' : '—'
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

function scoreGameKey(game) {
  const away = String(game.away_abbr || '').toUpperCase()
  const home = String(game.home_abbr || '').toUpperCase()
  return away && home ? `${away}@${home}` : ''
}

function settleAccount(account, scores) {
  let balance = Number(account.balance || 0)
  let changed = false

  const bets = (account.bets || []).map(bet => {
    if (bet.status !== 'PENDING') return bet
    const game = (scores || []).find(item => scoreGameKey(item) === bet.game_key)
    if (!game || !game.final) return bet

    const awayScore = Number(game.away_score)
    const homeScore = Number(game.home_score)
    if (!Number.isFinite(awayScore) || !Number.isFinite(homeScore)) return bet

    let grade = 'PUSH'
    if (awayScore !== homeScore) {
      const winner = awayScore > homeScore ? String(game.away || '') : String(game.home || '')
      grade = winner.trim().toLowerCase() === String(bet.selection || '').trim().toLowerCase() ? 'WIN' : 'LOSS'
    }

    const stake = Number(bet.stake || 0)
    const profit = americanProfit(stake, bet.odds)
    if (grade === 'WIN') balance += stake + profit
    if (grade === 'PUSH') balance += stake
    changed = true

    return {
      ...bet,
      status: grade,
      result: `${game.away_abbr} ${game.away_score} - ${game.home_score} ${game.home_abbr}`,
      profit_loss: grade === 'WIN' ? Number(profit.toFixed(2)) : grade === 'LOSS' ? -stake : 0,
      settled_at: new Date().toISOString(),
    }
  })

  return changed ? { ...account, balance: Number(balance.toFixed(2)), bets } : account
}

export default function PracticeBetting() {
  const [account, setAccount] = useState(loadAccount)
  const [decisions, setDecisions] = useState({ games: [] })
  const [scores, setScores] = useState({ games: [] })
  const [stakeByKey, setStakeByKey] = useState({})
  const [message, setMessage] = useState('')

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(account))
  }, [account])

  useEffect(() => {
    let cancelled = false

    const load = async () => {
      try {
        const [decisionResponse, scoreResponse] = await Promise.all([
          fetch(`/nfl_decisions.json?ts=${Date.now()}`, { cache: 'no-store' }),
          fetch(`/nfl_scores.json?ts=${Date.now()}`, { cache: 'no-store' }),
        ])
        const [decisionPayload, scorePayload] = await Promise.all([
          decisionResponse.ok ? decisionResponse.json() : { games: [] },
          scoreResponse.ok ? scoreResponse.json() : { games: [] },
        ])
        if (!cancelled) {
          setDecisions(decisionPayload)
          setScores(scorePayload)
          setAccount(current => settleAccount(current, scorePayload.games || []))
        }
      } catch {}
    }

    load()
    const timer = window.setInterval(load, 30000)
    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [])

  const available = useMemo(() => {
    return (decisions.games || []).filter(row => {
      const odds = Number(row.line)
      const score = (scores.games || []).find(game => scoreGameKey(game) === row.game_key)
      const startMs = Date.parse(row.start || '')
      const safelyPregame = score
        ? !score.live && !score.final
        : Number.isFinite(startMs) && startMs > Date.now()

      return (
        String(row.market || '').toUpperCase() === 'MONEYLINE' &&
        String(row.decision || '').toUpperCase() === 'QUALIFIED_RESEARCH' &&
        Number.isFinite(odds) &&
        Math.abs(odds) >= 100 &&
        safelyPregame
      )
    })
  }, [decisions, scores])

  const settled = (account.bets || []).filter(bet => ['WIN', 'LOSS', 'PUSH'].includes(bet.status))
  const wins = settled.filter(bet => bet.status === 'WIN').length
  const losses = settled.filter(bet => bet.status === 'LOSS').length
  const pushes = settled.filter(bet => bet.status === 'PUSH').length
  const pending = (account.bets || []).filter(bet => bet.status === 'PENDING')
  const risked = pending.reduce((sum, bet) => sum + Number(bet.stake || 0), 0)
  const pnl = Number(account.balance || 0) + risked - Number(account.starting_bankroll || STARTING_BANKROLL)
  const roi = Number(account.starting_bankroll) > 0 ? (pnl / Number(account.starting_bankroll)) * 100 : 0

  const placeBet = pick => {
    const key = `${pick.game_key}|${pick.selection}|${pick.line}`
    const stake = Number(stakeByKey[key] ?? 25)
    if (!Number.isFinite(stake) || stake <= 0) {
      setMessage('Enter a valid practice stake.')
      return
    }
    if (stake > Number(account.balance)) {
      setMessage('That practice stake is larger than your available bankroll.')
      return
    }

    const duplicatePending = (account.bets || []).some(
      bet => bet.status === 'PENDING' && bet.bet_key === key
    )
    if (duplicatePending) {
      setMessage('That exact practice bet is already pending.')
      return
    }

    const newBet = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      bet_key: key,
      sport: 'NFL',
      game_key: pick.game_key,
      market: 'MONEYLINE',
      selection: pick.selection,
      odds: Number(pick.line),
      stake: Number(stake.toFixed(2)),
      potential_profit: Number(americanProfit(stake, pick.line).toFixed(2)),
      hulk_score: pick.hulk_market_score,
      status: 'PENDING',
      placed_at: new Date().toISOString(),
      practice_only: true,
    }

    setAccount(current => ({
      ...current,
      balance: Number((Number(current.balance) - stake).toFixed(2)),
      bets: [newBet, ...(current.bets || [])],
    }))
    setMessage(`Practice bet placed: ${pick.selection} ML ${pick.line}.`)
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
              <WalletCards size={16} /> Practice Account
            </div>
            <h2 className="mt-2 text-3xl font-black tracking-tight md:text-4xl">
              Build a bankroll without risking real money.
            </h2>
            <p className="mt-3 text-sm leading-6 text-slate-300">
              Start with $1,000 in fake funds, place practice bets using captured market prices,
              and let final scores settle the account automatically.
            </p>
          </div>
          <span className="inline-flex rounded-full border border-emerald-300/25 bg-emerald-300/10 px-3 py-1.5 text-xs font-black text-emerald-200">
            PRACTICE ONLY · $0 REAL MONEY
          </span>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">Available</div>
            <div className="mt-2 text-2xl font-black">{money(account.balance)}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">Pending risk</div>
            <div className="mt-2 text-2xl font-black">{money(risked)}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">P/L</div>
            <div className={`mt-2 text-2xl font-black ${pnl >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{money(pnl)}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">Record</div>
            <div className="mt-2 text-2xl font-black">{wins}-{losses}-{pushes}</div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-[11px] font-black uppercase tracking-wide text-slate-500">Practice ROI</div>
            <div className={`mt-2 text-2xl font-black ${roi >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>{pct(roi)}</div>
          </div>
        </div>
      </section>

      {message && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-950">
          {message}
        </div>
      )}

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">Practice board</p>
            <h2>Current bets with a captured price</h2>
          </div>
          <span className="health-pill emerald">{available.length} AVAILABLE</span>
        </div>

        <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 text-sm leading-6 text-slate-600">
          The first version accepts <b>NFL moneyline practice bets only</b> because those cards currently carry a usable American price.
          Props and parlays will join when their publish-time price/payout can be stored honestly.
        </div>

        {available.length ? (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {available.map(pick => {
              const key = `${pick.game_key}|${pick.selection}|${pick.line}`
              const stake = Number(stakeByKey[key] ?? 25)
              const profit = americanProfit(stake, pick.line)
              return (
                <div key={key} className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-black uppercase tracking-[0.14em] text-slate-400">{pick.game_key}</div>
                      <div className="mt-2 text-xl font-black text-slate-950">{pick.selection}</div>
                    </div>
                    <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">
                      ML {pick.line > 0 ? '+' : ''}{pick.line}
                    </span>
                  </div>

                  <div className="mt-4 grid grid-cols-2 gap-2 text-center text-xs">
                    <div className="rounded-xl bg-slate-50 p-3">
                      <div className="font-black text-slate-950">{pick.hulk_market_score ?? '—'}</div>
                      <div className="mt-1 text-slate-400">Evidence score</div>
                    </div>
                    <div className="rounded-xl bg-slate-50 p-3">
                      <div className="font-black text-slate-950">{pick.sw_books ?? '—'}</div>
                      <div className="mt-1 text-slate-400">Books</div>
                    </div>
                  </div>

                  <div className="mt-5">
                    <label className="text-xs font-black uppercase tracking-wide text-slate-400">Practice stake</label>
                    <input
                      type="number"
                      min="1"
                      step="1"
                      value={stakeByKey[key] ?? 25}
                      onChange={event => setStakeByKey(current => ({ ...current, [key]: event.target.value }))}
                      className="mt-2 w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-base font-black text-slate-950 outline-none focus:border-blue-300 focus:bg-white"
                    />
                    <div className="mt-3 flex gap-2">
                      {[10, 25, 50, 100].map(amount => (
                        <button
                          key={amount}
                          type="button"
                          onClick={() => setStakeByKey(current => ({ ...current, [key]: amount }))}
                          className="rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-black text-slate-600"
                        >
                          ${amount}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 rounded-2xl bg-blue-50 p-3 text-sm text-blue-950">
                    Win profit <b>{money(profit)}</b> · Return <b>{money(stake + profit)}</b>
                  </div>

                  <button
                    type="button"
                    onClick={() => placeBet(pick)}
                    className="mt-4 w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white transition hover:bg-slate-800"
                  >
                    PLACE PRACTICE BET
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-soft">
            No qualified NFL moneyline with a captured American price is available right now.
          </div>
        )}
      </section>

      <section>
        <div className="section-heading">
          <div>
            <p className="eyebrow">My practice bets</p>
            <h2>Bankroll history</h2>
          </div>
          <button
            type="button"
            onClick={reset}
            className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-600"
          >
            <RotateCcw size={14} /> Reset account
          </button>
        </div>

        {(account.bets || []).length ? (
          <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-soft">
            <table className="min-w-[850px] w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Bet</th>
                  <th className="px-4 py-3">Odds</th>
                  <th className="px-4 py-3">Stake</th>
                  <th className="px-4 py-3">P/L</th>
                  <th className="px-4 py-3">Result</th>
                </tr>
              </thead>
              <tbody>
                {(account.bets || []).map(bet => (
                  <tr key={bet.id} className="border-b border-slate-100">
                    <td className="px-4 py-3">
                      <span className={`rounded-full px-2.5 py-1 text-[11px] font-black ${
                        bet.status === 'WIN' ? 'bg-emerald-50 text-emerald-700' :
                        bet.status === 'LOSS' ? 'bg-rose-50 text-rose-700' :
                        bet.status === 'PUSH' ? 'bg-slate-100 text-slate-700' :
                        'bg-blue-50 text-blue-700'
                      }`}>{bet.status}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-black text-slate-950">{bet.selection} ML</div>
                      <div className="mt-1 text-xs text-slate-400">{bet.game_key}</div>
                    </td>
                    <td className="px-4 py-3 font-bold text-slate-700">{bet.odds > 0 ? '+' : ''}{bet.odds}</td>
                    <td className="px-4 py-3 font-bold text-slate-700">{money(bet.stake)}</td>
                    <td className={`px-4 py-3 font-black ${Number(bet.profit_loss || 0) >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                      {bet.status === 'PENDING' ? '—' : money(bet.profit_loss)}
                    </td>
                    <td className="px-4 py-3 text-xs font-semibold text-slate-500">{bet.result || 'Waiting for final'}</td>
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
            <div className="mt-2 text-sm leading-6 text-slate-500">Your first practice bet will appear here and settle automatically after the final score.</div>
          </div>
        )}
      </section>

      <div className="flex gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">
        <ShieldCheck size={18} className="mt-0.5 shrink-0" />
        <div><b>Learning mode:</b> this account uses fake funds only. It is meant to test decisions and bankroll discipline without placing a real wager.</div>
      </div>
    </div>
  )
}
