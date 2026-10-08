import React from 'react'

// Private Survivor cards come from an authenticated linked entry only.
export default function SurvivorScoreCards({ cards = [], entryName = '' }) {
  if (!Array.isArray(cards) || cards.length === 0) return null
  const mostRecent = Math.max(...cards.map(card => Number(card.week) || 0))
  const tone = state => {
    if (state === 'SURVIVED' || state === 'LIVE_AHEAD') return 'border-emerald-200 bg-emerald-50 text-emerald-800'
    if (state === 'LOST' || state === 'LIVE_BEHIND') return 'border-rose-200 bg-rose-50 text-rose-800'
    return 'border-slate-200 bg-slate-50 text-slate-700'
  }
  const wording = card => {
    if (card.pool_result === 'SURVIVED') return 'SURVIVED'
    if (card.pool_result === 'LOST') return 'LOST'
    const names = {
      LIVE_AHEAD: 'AHEAD', LIVE_BEHIND: 'BEHIND', LIVE_TIED: 'TIED',
      LIVE: 'LIVE', UPCOMING: 'UPCOMING',
      FINAL_UNSETTLED_POOL: 'FINAL · awaiting pool grade',
      SCORE_WAITING: 'SCORE WAITING',
    }
    return names[card.game_state] || 'PENDING'
  }
  return (
    <section aria-label="My Survivor pick score" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft md:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">My pick score</p>
          <h2 className="mt-1 text-xl font-black tracking-tight text-slate-950">Saved team results</h2>
          <p className="mt-1 text-xs text-slate-500">{entryName || 'My entry'} · latest saved weeks, newest first</p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black text-slate-700">WEEK {mostRecent}</span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {cards.map((card, index) => {
          const label = wording(card)
          return (
            <div key={[card.week, card.team, card.pick_number, index].join('-')} className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Week {card.week} · Pick {card.pick_number}</span>
                <span className={'rounded-full border px-2.5 py-1 text-[10px] font-black ' + tone(card.pool_result === 'PENDING' ? card.game_state : card.pool_result)}>{label}</span>
              </div>
              <div className="mt-3 text-base font-black text-slate-950">{card.team}</div>
              {card.opponent && <div className="mt-1 text-xs font-semibold text-slate-500">vs {card.opponent}</div>}
              <div className="mt-3 text-sm font-bold leading-5 text-slate-700">{card.score_line || 'Score will appear when verified'}</div>
              <div className="mt-2 text-xs font-medium text-slate-500">{card.game_clock || 'Saved · not yet scored'}</div>
              {card.pool_result === 'PENDING' && (
                <div className="mt-2 text-[11px] font-semibold text-amber-800">
                  {card.pool_submitted ? 'Submission recorded in pool state' : 'Saved in Sports HULK · not submitted to pool'}
                </div>
              )}
            </div>
          )
        })}
      </div>
      <p className="mt-3 text-[11px] leading-5 text-slate-500">
        Live leads and final scoreboard scores are not automatically official pool results. Each entry is resolved only from its saved Survivor record.
      </p>
    </section>
  )
}
