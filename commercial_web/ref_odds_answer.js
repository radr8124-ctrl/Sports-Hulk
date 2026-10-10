// The Ref's odds analysis uses exactly the priced board shown on Sports Zenith.
// Archived snapshots and experimental model probabilities are NOT verified +EV.
import {refMarketReview} from './ref_market_review.js'

const books={pinnacle:'Pinnacle',fanduel:'FanDuel',draftkings:'DraftKings',
  caesars:'Caesars',betmgm:'BetMGM',thescore:'theScore',fanatics:'Fanatics'}
const book=x=>books[String(x||'').toLowerCase()]||String(x||'Unknown book')
const timestamp=x=>{
  const d=Date.parse(x||'')
  return Number.isFinite(d)?d:null
}
const priceString=x=>Number.isInteger(x)&&Math.abs(x)>=100?(x>0?'+'+x:String(x)):'—'
const breakeven=x=>x<0?100*Math.abs(x)/(100+Math.abs(x)):10000/(100+x)
const profit=x=>x<0?100/Math.abs(x):x/100
const rounded=x=>Math.round(x*100)/100
const timeET=x=>{
 const ms=timestamp(x)
 return ms===null?'unverified':new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
  timeZone:'America/New_York',timeZoneName:'short',
 }).format(ms)
}
function cards(games){
  return games.slice(0,4).map(g=>({
    type:'ref_market_research',title:g.team,selection:g.team,
    market:'Moneyline',line:g.bestAmericanPrice,
    market_probability:g.marketFairPct,model_probability:g.modelResearchPct,
    book:g.bestBook,decision:'RESEARCH_ONLY',
  }))
}
function answerCommon(data){
  return {
    intent:'ref_market_research',status:'RESEARCH_ONLY',
    confidence:'MATCHED MARKET RESEARCH · NOT A PLAY',
    updated_at:data.oddsBoard?.generated_at||null,
    sources:[
      {label:'Same-event paired sportsbook research',
        source:'BETTING_ODDS_SOURCE_ARCHIVE',
        updated_at:data.oddsBoard?.generated_at||null},
      {label:'Independent first NFL research freeze',
        source:'NFL_NINE_FEATURE_FROZEN_FORECAST',
        updated_at:data.nflFrozenForecast?.generated_at||null},
    ],
  }
}

export function refereeOddsAnswer(question,data={},context={},nowMs=Date.now()){
  const q=String(question||'').toLowerCase().trim()
  if(!q||!Number.isFinite(nowMs))return null
  if(/\b(survivor|waiver|faab|start.?sit|dfs|lineup|parlay|player props?|prizepicks|injur|news|score|box score)\b/.test(q))return null
 if(/\b(nhl|nba|mlb|cfb|cbb|college football|baseball|hockey|basketball)\b/.test(q))return null
  if(!/\b(odds|bets?|betting|moneyline|spread|totals?|price|positive ev|value|market lean|fair probability|edge)\b/.test(q)
    &&context.page!=='Best Bets')return null
  const games=refMarketReview({
    odds:data.oddsBoard||{},frozen:data.nflFrozenForecast||{},
    nowMs,sport:'NFL',
  })
  if(!games.length)return null
  const id=String(context?.game_context?.event_id||'')
  if(id&&String(context?.game_context?.league||'').toUpperCase()!=='NFL')return null
  let matched=id?games.filter(g=>String(g.eventId)===id):[]
  if(id&&!matched.length)return null
  if(!matched.length){
    matched=games.filter(g=>[g.home,g.away].some(name=>{
      const lower=String(name||'').toLowerCase()
      const nickname=lower.split(' ').at(-1)
      return (lower.length>=4&&q.includes(lower)) ||
        (nickname.length>=4&&q.includes(nickname))
    }))
  }
  const common=answerCommon(data)
  if(matched.length>1&&!id) return {
    ...common,intent:'ref_market_needs_game',status:'NEEDS_EXACT_GAME',
    take:'More than one NFL matchup matches that team. Name the opponent or kickoff date to compare the correct odds.',
    why:['Two different games never share the same price or prediction.'],
    risk:['No game or quote is guessed.'],cards:[],
    followups:['Show NFL odds research','Review Raiders at Patriots moneyline'],
  }
  if(!matched.length){
    const upcoming=games.slice(0,4)
    const summary=upcoming.map(g=>g.away+' at '+g.home+': '+g.team+' '+
      g.bestAmericanPrice+' ('+book(g.bestBook)+', '+g.marketFairPct+'% no-vig)')
    return {...common,
      take:'I found '+games.length+' verified-game-identity NFL moneyline research matchups. None is an independently proven +EV play.',
      why:[
        'These are observed sportsbook market favorites, not Zenith-approved bets.',
        summary.join('; ')+'.',
        'The price can differ between sportsbooks, but shopping odds alone is not a calibrated edge.',
      ],
      risk:['Original quote times and executable book access must be reverified.',
        'Model comparison with the market has not established a profitable advantage.'],
      cards:cards(upcoming),
      followups:['Review Raiders at Patriots moneyline','Why is there no proven NFL PLAY?'],
    }
  }
  const g=matched[0]
  const board=(data.oddsBoard?.games||[]).find(row=>row.sport==='NFL' &&
    String(row.provider_event_id)===g.id.split('|')[1] &&
    String(row.official_espn_event_id)===String(g.eventId))
  if(!board?.markets?.MONEYLINE?.sides)return null
  const sides=board.markets.MONEYLINE.sides
  const offer=sides[g.selectedSide]
  const odds=Number(offer?.best_american_odds)
  if(!Number.isInteger(odds)||Math.abs(odds)<100)return null
  const opposite=sides[g.selectedSide==='HOME'?'AWAY':'HOME']
  if(!opposite)return null
  const otherMarkets=[]
  const spread=board.markets?.SPREAD?.sides
  if(spread?.AWAY&&spread?.HOME){
    const signed=x=>x>0?'+'+x:String(x)
    otherMarkets.push('Exact comparable spread: '+g.away+' '+signed(spread.AWAY.line)+' '+
      priceString(spread.AWAY.best_american_odds)+' at '+book(spread.AWAY.best_sportsbook)+
      '; '+g.home+' '+signed(spread.HOME.line)+' '+priceString(spread.HOME.best_american_odds)+
      ' at '+book(spread.HOME.best_sportsbook)+'. Winning outright does not mean covering.')
  }
  const total=board.markets?.TOTAL
  if(total?.sides?.OVER&&total?.sides?.UNDER){
    otherMarkets.push('Exact comparable game total '+total.line+': Over '+
      priceString(total.sides.OVER.best_american_odds)+' at '+book(total.sides.OVER.best_sportsbook)+
      '; Under '+priceString(total.sides.UNDER.best_american_odds)+' at '+book(total.sides.UNDER.best_sportsbook)+
      '. No calibrated game-total probability is proven.')
  }
  const threshold=rounded(breakeven(odds))
  const hypothetical=g.modelResearchPct===null?null:
    rounded(100*((g.modelResearchPct/100)*profit(odds)-(1-g.modelResearchPct/100)))
  const modelText=g.modelResearchPct===null?
    'No validated Zenith probability exists for this market.':
    'Frozen, market-assisted Zenith estimate for '+g.team+': '+g.modelResearchPct+
    '%, versus no-vig book consensus '+g.marketFairPct+
    '%. It is experimental and was not proven to outperform the sportsbook market.'
  return {...common,
    take:'Market favorite: '+g.team+' ('+g.marketFairPct+'% fair). Best observed '+
      g.bestAmericanPrice+' at '+book(g.bestBook)+'. No proven +EV wager.',
    why:[
      g.sport+' '+g.away+' at '+g.home+' · kickoff '+timeET(g.kickoff)+'.',
      g.away+' ML '+priceString(sides.AWAY.best_american_odds)+' at '+
        book(sides.AWAY.best_sportsbook)+'; '+g.home+' ML '+
        priceString(sides.HOME.best_american_odds)+' at '+book(sides.HOME.best_sportsbook)+'.',
      modelText,
      ...otherMarkets,
      'The '+g.bestAmericanPrice+' quote requires '+threshold+
        '% probability to break even. '+(hypothetical===null?
        'No validated expected value can be computed.':
        'Using the unproven model illustratively produces '+(hypothetical>=0?'+':'')+
        hypothetical+'% EV; this is NOT verified profitable edge.'),
    ],
    risk:[
      'Book quote updated '+timeET(offer.source_updated_at)+'. Source captured '+
        timeET(g.sourceCapturedAt)+' ('+g.priceAgeLabel+' old). '+
        (g.quoteStatus==='ARCHIVED_RECHECK'?'EXPIRED: recheck line.':
         'DATED: not verified executable.'),
      'QB/injury news, limits, available user sportsbooks and true closing line are not verified by this comparison.',
      'Bet status: PASS / 0 units until independently validated edge and a fresh executable price are proven.',
    ],
    cards:cards([g]),
    followups:['Why might the favorite fail to cover the spread?',
      'Why is this moneyline not positive EV?',
      'Which team is worth preserving for Survivor?'],
  }
}
