import { BookOpenCheck } from 'lucide-react'

const finiteNumber = value => {
  if (value === null || value === undefined || String(value).trim() === '') return null
  const number = Number(value)
  return Number.isFinite(number) ? number : null
}

const signedLine = value => {
  const number = finiteNumber(value)
  if (number == null) return null
  if (number > 0) return `+${number}`
  return String(number)
}

export const formatAmericanOdds = value => {
  const number = finiteNumber(value)
  if (number == null) return null
  return number > 0 ? `+${Math.round(number)}` : String(Math.round(number))
}

const marketText = value => String(value || '')
  .replaceAll('_', ' ')
  .toLowerCase()
  .replace(/\b\w/g, letter => letter.toUpperCase())

const selectionText = row => String(row?.selection || row?.team || row?.player || '').trim()

const sideText = row => {
  const explicit = String(row?.side || '').trim().toUpperCase()
  if (explicit === 'OVER' || explicit === 'UNDER') return explicit

  const selection = String(row?.selection || '').trim().toUpperCase()
  if (selection.startsWith('OVER')) return 'OVER'
  if (selection.startsWith('UNDER')) return 'UNDER'
  return ''
}

const displayMetric = row => {
  const raw = row?.market_subtype || row?.stat_type || row?.prop_type || row?.market || ''
  return marketText(raw)
    .replace(/^Player /i, '')
    .replace(/ Moneyline$/i, '')
}

export function betDisplayLabel(row = {}) {
  const market = String(row.market || '').toUpperCase()
  const selection = selectionText(row)
  const line = finiteNumber(row.line)
  const side = sideText(row)

  if (market === 'MONEYLINE') return selection || 'Moneyline'

  if (market === 'SPREAD') {
    const formatted = signedLine(line)
    return [selection, formatted].filter(Boolean).join(' ')
  }

  if (market === 'TOTAL') {
    return [side ? marketText(side) : selection, line].filter(value => value !== null && value !== '').join(' ')
  }

  if (side && line != null) {
    return [selection, marketText(side), line, displayMetric(row)].filter(Boolean).join(' ')
  }

  return selection || marketText(row.market) || 'Bet'
}

function moneylineMeaning(row) {
  const selection = selectionText(row) || 'Your team'
  return {
    primary: `For this moneyline to win: ${selection} must win the game.`,
    secondary: 'No point spread is involved.',
  }
}

function spreadMeaning(row) {
  const selection = selectionText(row) || 'Your team'
  const line = finiteNumber(row.line)
  if (line == null) {
    return {
      primary: `${selection} is being evaluated against the point spread.`,
      secondary: 'The exact spread is not available in this row, so Sports Zenith will not invent the cover requirement.',
    }
  }

  if (line === 0) {
    return {
      primary: `${selection} needs to win the game.`,
      secondary: 'A tie would push a pick’em spread.',
    }
  }

  const abs = Math.abs(line)
  const whole = Number.isInteger(abs)

  if (line < 0) {
    const mustWinBy = Math.floor(abs) + 1
    return {
      primary: `${selection} must win by ${mustWinBy} or more.`,
      secondary: whole
        ? `A ${abs}-point win would push; winning by ${mustWinBy}+ covers ${signedLine(line)}.`
        : `Winning by ${mustWinBy}+ covers the ${signedLine(line)} spread.`,
    }
  }

  const maxLoss = whole ? Math.max(0, abs - 1) : Math.floor(abs)
  return {
    primary: `${selection} can win outright or lose by ${maxLoss} or fewer.`,
    secondary: whole
      ? `Losing by exactly ${abs} would push the ${signedLine(line)} spread.`
      : `Losing by ${Math.ceil(abs)} or more loses the ${signedLine(line)} spread.`,
  }
}

function totalMeaning(row) {
  const line = finiteNumber(row.line)
  const side = sideText(row)
  if (line == null || !side) {
    return {
      primary: 'This bet is on the combined score of both teams.',
      secondary: 'The exact side or total is not available in this row, so Sports Zenith will not invent the requirement.',
    }
  }

  const whole = Number.isInteger(line)
  if (side === 'OVER') {
    const needed = Math.floor(line) + 1
    return {
      primary: `The teams must combine for ${needed}+ points.`,
      secondary: whole
        ? `Exactly ${line} points would push; ${needed}+ wins the Over.`
        : `${needed}+ total points wins Over ${line}.`,
    }
  }

  const maxTotal = whole ? line - 1 : Math.floor(line)
  return {
    primary: `The teams must combine for ${maxTotal} or fewer points.`,
    secondary: whole
      ? `Exactly ${line} points would push; ${maxTotal} or fewer wins the Under.`
      : `${maxTotal} or fewer total points wins Under ${line}.`,
  }
}

function propMeaning(row) {
  const player = String(row.player || '').trim() || selectionText(row) || 'The player'
  const line = finiteNumber(row.line)
  const side = sideText(row)
  const metric = displayMetric(row).toLowerCase()

  if (line == null || !side) {
    return {
      primary: `This is a player ${metric || 'prop'} bet.`,
      secondary: 'The exact side or line is not available in this row, so Sports Zenith will not invent the requirement.',
    }
  }

  const whole = Number.isInteger(line)
  if (side === 'OVER') {
    const needed = Math.floor(line) + 1
    return {
      primary: `${player} needs ${needed}+ ${metric || 'units'}.`,
      secondary: whole ? `Exactly ${line} would push a sportsbook Over ${line}.` : `Anything below ${needed} loses the Over.`,
    }
  }

  const max = whole ? line - 1 : Math.floor(line)
  return {
    primary: `${player} needs ${max} or fewer ${metric || 'units'}.`,
    secondary: whole ? `Exactly ${line} would push a sportsbook Under ${line}.` : `${Math.ceil(line)}+ loses the Under.`,
  }
}

export function explainBet(row = {}) {
  const market = String(row.market || '').toUpperCase()
  if (market === 'MONEYLINE') return moneylineMeaning(row)
  if (market === 'SPREAD') return spreadMeaning(row)
  if (market === 'TOTAL') return totalMeaning(row)
  return propMeaning(row)
}

export function explainAmericanOdds(value) {
  const odds = finiteNumber(value)
  if (odds == null || odds === 0) return null

  if (odds > 0) {
    return {
      price: formatAmericanOdds(odds),
      text: `At ${formatAmericanOdds(odds)}, a $100 practice stake would profit $${Math.round(odds)} if it wins.`,
    }
  }

  return {
    price: formatAmericanOdds(odds),
    text: `At ${formatAmericanOdds(odds)}, a $${Math.round(Math.abs(odds))} practice stake would profit $100 if it wins.`,
  }
}

export default function BetMeaning({ row, compact = false }) {
  const meaning = explainBet(row)
  const price = explainAmericanOdds(row?.american_odds ?? row?.captured_american_odds)

  return (
    <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/90 to-white p-4">
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-blue-700">
        <BookOpenCheck size={14} /> What this bet means
      </div>
      <div className="mt-2 text-sm font-black leading-6 text-slate-950">{meaning.primary}</div>
      {!compact && meaning.secondary && (
        <div className="mt-1 text-xs font-semibold leading-5 text-slate-500">{meaning.secondary}</div>
      )}
      {price && (
        <div className="mt-3 border-t border-blue-100 pt-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-black text-slate-800 shadow-sm">Price {price.price}</span>
            <span className="text-[10px] font-bold uppercase tracking-[0.1em] text-slate-400">Practice math</span>
          </div>
          {!compact && <div className="mt-2 text-[11px] font-semibold leading-5 text-slate-500">{price.text} Price math is educational, not a recommendation.</div>}
        </div>
      )}
    </div>
  )
}
