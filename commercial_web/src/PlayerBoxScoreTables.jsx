import React from 'react'
import { ChevronDown, ShieldCheck } from 'lucide-react'

export default function PlayerBoxScoreTables({ data }) {
  const teams = Array.isArray(data?.player_tables) ? data.player_tables : []
  const officialState = String(data?.official_game_state || 'UNKNOWN')
  const sourceStatus = String(data?.player_source_status || 'UNKNOWN')
  const verifiedCount = Number(data?.player_stat_rows) || 0
  const dnpCount = Number(data?.player_dnp_count) || 0
  const omitted = Number(data?.player_rows_omitted) || 0
  if (!teams.length || sourceStatus !== 'VERIFIED_PLAYER_STATS') {
    return (
      <section aria-label="Official player box scores" className="rounded-2xl border border-slate-200 bg-white p-4 text-sm font-semibold leading-6 text-slate-600">
        <h3 className="font-black text-slate-900">Player-by-player box score</h3>
        <p className="mt-1">
          {sourceStatus === 'PREGAME_NO_PLAYER_STATS'
            ? 'This game has not started. Official recorded player statistics will appear once available.'
            : 'No verified player-by-player statistics are available from the game source yet.'}
        </p>
      </section>
    )
  }
  return (
    <section aria-label="Official player box scores" className="min-w-0 rounded-3xl border border-blue-200 bg-[#F7FAFE] p-3 shadow-soft md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[0.12em] text-blue-700">Real official stats · ESPN {officialState}</p>
          <h3 className="mt-1 text-lg font-black text-slate-950">Player-by-player box score</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">
            {verifiedCount} source-matched player-stat lines across {teams.length} teams.
            {' '}Swipe the tables sideways for more stats.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-[10px] font-black text-blue-800">
          <ShieldCheck size={13} className="mr-1 inline" />
          {officialState === 'FINAL' ? 'OFFICIAL FINAL' : 'LIVE SOURCE'}
        </span>
      </div>
      {(dnpCount > 0 || omitted > 0) && (
        <p className="mt-2 text-[11px] font-semibold leading-5 text-slate-600">
          {dnpCount > 0 ? `${dnpCount} did-not-play roster rows excluded. ` : ''}
          {omitted > 0 ? `${omitted} incomplete or conflicting player-stat rows excluded.` : ''}
          No missing result is changed into a zero.
        </p>
      )}
      <div className="mt-3 space-y-3">
        {teams.map((side,index) => (
          <details key={side.team_id || side.team} className="min-w-0 overflow-hidden rounded-2xl border border-slate-200 bg-white" open={index === 0 ? true : undefined}>
            <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-black text-slate-900">
              <span>{side.team || side.abbreviation} · {side.groups?.reduce((sum,group)=>sum+(group.players?.length || 0),0)} stat lines</span>
              <ChevronDown size={16} className="shrink-0 text-blue-600" aria-hidden="true" />
            </summary>
            <div className="space-y-4 border-t border-slate-100 px-2 py-3 sm:px-3">
              {(side.groups || []).map((group,groupIndex) => (
                <div key={`${group.category}-${groupIndex}`} className="min-w-0">
                  <h4 className="px-2 pb-2 text-[11px] font-black uppercase tracking-wide text-blue-700">{group.category || 'Player stats'}</h4>
                  <div className="max-w-full overflow-x-auto overscroll-x-contain rounded-xl border border-slate-200" tabIndex={0} role="region" aria-label={`${side.team || side.abbreviation} ${group.category || 'players'} statistics`}>
                    <table className="w-full min-w-max border-collapse text-xs">
                      <thead className="bg-slate-100 text-slate-600">
                        <tr>
                          <th scope="col" className="sticky left-0 z-10 min-w-32 border-r border-slate-200 bg-slate-100 px-3 py-2 text-left font-black">Player</th>
                          {(group.labels || []).map((label,colIndex) => (
                            <th scope="col" key={`${label}-${colIndex}`} className="px-3 py-2 text-right font-black">{label}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(group.players || []).map((player,rowIndex) => (
                          <tr key={`${player.id}-${rowIndex}`} className="border-t border-slate-100">
                            <th scope="row" className="sticky left-0 z-10 border-r border-slate-200 bg-white px-3 py-2 text-left font-bold text-slate-900">
                              <span className="block max-w-36 whitespace-normal">{player.name}</span>
                              {player.position && <span className="block text-[10px] font-medium text-slate-400">{player.position}</span>}
                            </th>
                            {(player.stats || []).map((value,colIndex) => (
                              <td key={colIndex} className="px-3 py-2 text-right font-semibold tabular-nums text-slate-600">{value === '' ? '—' : value}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </details>
        ))}
      </div>
      <p className="mt-3 text-[11px] leading-5 text-slate-500">
        ESPN game identity, participating teams and final/live status were checked before displaying these figures.
        A player may appear in multiple college stat categories; these are stat lines, not unique player counts.
      </p>
    </section>
  )
}
