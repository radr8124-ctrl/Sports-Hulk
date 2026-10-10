// The Ref: vetted market snapshots, NOT an independent prediction engine.
import {showFrozenNFLResearch} from './nfl_frozen_forecast_presentation.js'

const asTime=x=>{
  const n=Date.parse(x||'')
  return Number.isFinite(n)?n:null
}
const asNum=x=>x===null||x===undefined||x===''?null:
  Number.isFinite(Number(x))?Number(x):null
const money=odds=>Number.isInteger(odds)&&Math.abs(odds)>=100
  ?odds>0?'+'+odds:''+odds:null
const one=n=>Math.round(n*10)/10

export function refMarketReview({odds={},frozen={},nowMs=Date.now(),sport='NFL'}={}) {
  if(!Number.isFinite(nowMs) || odds?.status!=='RESEARCH_ONLY' ||
    odds?.verified_positive_expected_value_bets!==0 ||
    odds?.all_prices_observed_not_executable!==true ||
    odds?.no_approved_pick_or_bet_created!==true ||
    !Array.isArray(odds?.games))return []
  const checked=showFrozenNFLResearch(frozen,nowMs)
  const forecasts=checked.status==='FROZEN_RESEARCH'?
    new Map(checked.rows.map(row=>[String(row.event_id),row])):new Map()
  const results=[]
  for(const game of odds.games) {
    if(sport!=='ALL' && game.sport!==sport)continue
    if(game.independent_model_value_proven!==false ||
       game.book_price_is_not_live_or_executable!==true)continue
    const kickoff=asTime(game.start)
    if(kickoff===null||kickoff<=nowMs || kickoff>nowMs+30*86400000)continue
    if(!game.away||!game.home||!game.provider_event_id)continue
    if(game.sport==='NFL'&&
      (game.event_identity_status!=='EXACT_ESPN_TEAMS_KICKOFF_UNIQUE_EVENT'||
       !game.official_espn_event_id))continue
    const sides=game.markets?.MONEYLINE?.sides
    const paired=game.markets?.MONEYLINE?.paired_book_count
    if(!sides || !Number.isInteger(paired)||paired<2)continue
    const away=asNum(sides.AWAY?.market_consensus_no_vig_probability_pct)
    const home=asNum(sides.HOME?.market_consensus_no_vig_probability_pct)
    if(away===null||home===null||away<=0||home<=0||
       Math.abs(away+home-100)>1.5)continue
    const isHome=home>away
    const chosen=isHome?sides.HOME:sides.AWAY
    const team=isHome?game.home:game.away
    if(!Number.isInteger(chosen?.best_american_odds) ||
      Math.abs(chosen.best_american_odds)<100 ||
      chosen?.proven_positive_expected_value!==false ||
      chosen?.book_accessibility_or_executability_verified!==false ||
      !chosen?.source_updated_at || !chosen?.best_sportsbook)continue
    const quote=asTime(chosen.source_updated_at)
    const capture=asTime(game.source_capture_at)
    if(quote===null||capture===null||quote>nowMs||
      capture>nowMs||quote>=kickoff||capture>=kickoff)continue
    const ageHours=(nowMs-capture)/3.6e6
    const deadlineHours=(kickoff-nowMs)/3.6e6
    const outdated=ageHours>(deadlineHours<=24?6:24)
    const projected=game.sport==='NFL'?
      forecasts.get(String(game.official_espn_event_id)):null
    // Model must match official ESPN ID and actual game kickoff.
    // The validator independently checks frozen ledger/model/source contracts.
    const teamsFromOfficialKey=String(game.game_key||'').split('@')
    const model=projected&&Math.abs(asTime(projected.kickoff_utc)-kickoff)<=180000
      &&teamsFromOfficialKey.length===2
      &&teamsFromOfficialKey[0]===String(projected.away||'')
      &&teamsFromOfficialKey[1]===String(projected.home||'')
      ?projected:null
    const modelHome=model?asNum(model.forecast_home_pct):null
    const modelAway=model?asNum(model.forecast_away_pct):null
    const modelProb=isHome?modelHome:modelAway
    const marketProb=one(isHome?home:away)
    const refOdd=money(chosen.best_american_odds)
    const typical=money(chosen.median_book_american_odds)
    if(!refOdd)continue
    const ageText=ageHours<1
      ?String(Math.max(1,Math.floor(ageHours*60)))+' min'
      :String(one(ageHours))+'h'
    results.push({
      id:String(game.sport)+'|'+String(game.provider_event_id),
      eventId:game.official_espn_event_id||null,
      sport:game.sport,away:game.away,home:game.home,
      gameKey:game.game_key||'',kickoff:game.start,
      team,selectedSide:isHome?'HOME':'AWAY',
      bestAmericanPrice:refOdd,bestBook:chosen.best_sportsbook,
      typicalAmericanPrice:typical,marketFairPct:marketProb,
      modelResearchPct:modelProb===null?null:one(modelProb),
      modelMarketInput:model?.model_uses_market_input===true,
      originalModelProven:model?.model_beats_market_out_of_sample_proven===true,
      sourceUpdatedAt:chosen.source_updated_at,
      sourceCapturedAt:game.source_capture_at,
      priceAgeHours:one(ageHours),priceAgeLabel:ageText,
      quoteStatus:outdated?'ARCHIVED_RECHECK':'DATED_SNAPSHOT',
      method:'MARKET_MONEYLINE_NO_VIG_CONSENSUS_NOT_ZENITH_EDGE',
      actualExecutableBookOfferVerified:false,
      provenPositiveEV:false,approvedPlay:false,
      context:game.sport==='NFL'?{
        surface:'GAME_CENTER',league:'NFL',
        event_id:String(game.official_espn_event_id),
        away:game.away,home:game.home,
      }:null,
      question:'Review NFL '+game.away+' at '+game.home+' moneyline betting. Explain why the market favors '+team+', how Zenith compares with the sportsbook, and what independent proof is missing.',
    })
  }
  results.sort((a,b)=>Date.parse(a.kickoff)-Date.parse(b.kickoff)||a.id.localeCompare(b.id))
  return results
}

export function refereeQuickPrompts(page='Ask',game=null) {
  if(game?.surface==='GAME_CENTER'&&game?.event_id) return [
    ['This game',"Review this game's sportsbook bets and explain the market lean"],
    ['Player props','What exact-game player props have evidence?'],
    ['Injuries','What verified injury news affects this matchup?'],
  ]
  if(page==='Survivor')return [
    ['Available team','What Survivor team should I use based on my saved pool rules?'],
    ['Save for later','Which unused Survivor team should I preserve for later weeks?'],
    ['Pool status','How many entries are left in my survivor pool?'],
  ]
  if(page==='Props'||page==='PrizePicks')return [
    ['Explain lines',page==='PrizePicks'
       ?'Review NFL PrizePicks lines and explain why no entry is approved.'
       :'Review NFL player props and explain the price and model proof.'],
    ['Best research','Show the best NFL prop research opportunities and their risks.'],
    ['Why no PLAY?','Why are player props still research and not verified positive EV bets?'],
  ]
  if(['Best Bets','Parlays','Bet Lab','Tools'].includes(page))return [
    ['Review prices','What is the best NFL bet right now and why?'],
    ['Why no PLAY?','Why have NFL bets not cleared independent model proof?'],
    ['Spread vs winner','Explain why an NFL moneyline favorite might not cover a spread.'],
  ]
  return [
    ['Review odds','What is the best NFL bet right now and why?'],
    ['Survivor','What Survivor team should I use based on my saved pool rules?'],
    ['Player props','Which NFL player props have evidence and what is missing?'],
    ['Live scores','What are the live NFL scores?'],
    ['Fantasy','Who should I start this week?'],
    ['Waiver Adds','Who are the top waiver adds?'],
  ]
}
