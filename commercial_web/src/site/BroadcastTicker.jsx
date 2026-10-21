import React, { useState } from 'react'
import './broadcastTicker.css'

function TickerGame({ game }) {
  return (
    <span className="zenith-ticker-game">
      <span className="zenith-ticker-league">{game.league}</span>
      <span className="zenith-ticker-matchup">{game.away} <span className="zenith-ticker-at">@</span> {game.home}</span>
      {game.score ? <span className="zenith-ticker-score">{game.score}</span> : null}
      <span className={`zenith-ticker-status ${game.status === 'LIVE' ? 'is-live' : ''}`}>{game.status === 'LIVE' ? '● LIVE' : game.status}</span>
    </span>
  )
}

export default function BroadcastTicker({ games, onNavigate }) {
  const [paused, setPaused] = useState(false)
  const hasGames = games.length > 0
  return (
    <section className="zenith-broadcast" aria-label="Sports scores ticker" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false) }} onTouchStart={() => setPaused(true)}>
      <div className="zenith-broadcast-label"><span className="zenith-broadcast-pulse" /> ZENITH <span className="zenith-broadcast-label-muted">SCORES</span></div>
      <div className="zenith-broadcast-window">
        {hasGames ? (
          <div className={`zenith-broadcast-track ${paused ? 'is-paused' : ''}`}>
            <div className="zenith-broadcast-sequence">{games.map((game, index) => <TickerGame key={`${game.id}-${index}`} game={game} />)}</div>
            <div className="zenith-broadcast-sequence" aria-hidden="true">{games.map((game, index) => <TickerGame key={`repeat-${game.id}-${index}`} game={game} />)}</div>
          </div>
        ) : <div className="zenith-broadcast-empty">No current matchups in the score feeds. Check the full scores board.</div>}
      </div>
      <button className="zenith-broadcast-view" onClick={() => onNavigate('Scores')} type="button">ALL SCORES <span aria-hidden="true">↗</span></button>
    </section>
  )
}
