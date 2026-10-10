import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {refMarketReview,refereeQuickPrompts} from './ref_market_review.js'
import {refereeOddsAnswer} from './ref_odds_answer.js'
import {validateAskOutput} from './ask_output_validation.js'

const read=name=>JSON.parse(readFileSync(new URL('./public/'+name,import.meta.url),'utf8'))
const odds=read('betting_odds_board.json')
const frozen=read('nfl_frozen_game_intelligence.json')
const now=Date.parse('2026-10-10T01:50:00Z')
const source={oddsBoard:odds,nflFrozenForecast:frozen}
const answer=(q,context={page:'Ask'},data=source,t=now)=>
  refereeOddsAnswer(q,data,context,t)

test('verified favorite list uses exact NFL event and date with no odds invented',()=>{
 const a=refMarketReview({odds,frozen,nowMs:now,sport:'NFL'})
 assert.equal(a.length,13)
 assert(a.every(x=>x.context?.surface==='GAME_CENTER'))
 assert(a.every(x=>x.sport==='NFL'&&x.context.event_id))
 assert(a.every(x=>x.provenPositiveEV===false&&x.approvedPlay===false&&x.actualExecutableBookOfferVerified===false))
 assert(!a.some(x=>x.team==='Philadelphia Eagles'&&x.eventId==='401872981'))
})

test('Oct11 Raiders vs Patriots remains true to independently frozen market model',()=>{
 const a=refMarketReview({odds,frozen,nowMs:now,sport:'NFL'})
 const row=a.find(x=>x.eventId==='401872986')
 assert.equal(row.team,'New England Patriots')
 assert.equal(row.bestAmericanPrice,'-194')
 assert.equal(row.bestBook,'pinnacle')
 assert.equal(row.marketFairPct,63.8)
 assert.equal(row.modelResearchPct,65.7)
 assert.equal(row.quoteStatus,'DATED_SNAPSHOT')
 assert.equal(row.originalModelProven,false)
 assert.equal(row.context.away,'Las Vegas Raiders')
})

test('route generic Best Bet to source-backed research cards, not empty V2 response',()=>{
 const r=answer('What is the best NFL bet right now and why?')
 assert.equal(r.intent,'ref_market_research')
 assert.equal(r.status,'RESEARCH_ONLY')
 assert.match(r.take,/13 verified-game-identity NFL moneyline/)
 assert.match(r.take,/no.*independently proven.*EV/i)
 assert(r.cards.length>=2)
 assert.equal(validateAskOutput(r).valid,true)
 assert(r.risk.some(s=>s.includes('quote')))
})

test('selected official game matches price and quote time exactly and remains a PASS',()=>{
 const context={page:'Ask',game_context:{surface:'GAME_CENTER',league:'NFL',event_id:'401872986'}}
 const r=answer('Review Raiders at Patriots moneyline and the fair price',context)
 assert.match(r.take,/New England Patriots.*-194.*Pinnacle/)
 assert(r.why.some(s=>s.includes('Las Vegas Raiders ML +169')))
 assert(r.why.some(s=>s.includes('65.7%')&&s.includes('63.8%')))
 assert(r.why.some(s=>s.includes('65.99%')))
 assert(r.why.some(s=>s.includes('Exact comparable spread')&&s.includes('Patriots -3.5')))
 assert(r.why.some(s=>s.includes('game total')&&s.includes('Over')))
 assert(r.why.some(s=>s.includes('unproven model illustratively produces')&&s.includes('NOT verified profitable edge')))
 assert(r.risk.some(s=>s.includes('PASS / 0 units')))
 assert.equal(validateAskOutput(r).valid,true)
 assert.equal(r.cards[0].decision,'RESEARCH_ONLY')
})

test('future sportsbook quote, missing opposite side, and forged approved flag cannot be presented',()=>{
 const bad=structuredClone(odds)
 bad.games[0].markets.MONEYLINE.sides.HOME.source_updated_at='2030-01-01T00:00:00Z'
 const options=refMarketReview({odds:bad,frozen,nowMs:now,sport:'NFL'})
 assert.equal(options.some(x=>x.eventId===bad.games[0].official_espn_event_id),false)
 const fake=structuredClone(odds)
 fake.no_approved_pick_or_bet_created=false
 assert.equal(refMarketReview({odds:fake,frozen,nowMs:now}).length,0)
 const noOpp=structuredClone(odds)
 delete noOpp.games[0].markets.MONEYLINE.sides.AWAY
 assert.equal(refMarketReview({odds:noOpp,frozen,nowMs:now})
   .some(x=>x.eventId===noOpp.games[0].official_espn_event_id),false)
})

test('expired quote is never sold as a current actionable offer',()=>{
 const future=Date.parse('2026-10-10T20:30:00Z')
 const r=answer('Explain Raiders vs Patriots odds',{page:'Best Bets'},source,future)
 assert.equal(r.status,'RESEARCH_ONLY')
 assert(r.risk[0].includes('EXPIRED'))
 assert(r.risk.some(s=>s.includes('PASS / 0 units')))
})

test('wrong-game and other interests are not hijacked by the odds router',()=>{
 assert.equal(answer('Survivor picks for Week 5'),null)
 assert.equal(answer('Who should I start at flex?'),null)
 assert.equal(answer('Why did the player props pass?'),null)
 assert.equal(answer('Raiders at Patriots moneyline',{page:'Ask',
   game_context:{league:'NHL',event_id:'401872986'}}),null)
 assert.equal(answer('Raiders at Patriots moneyline',{page:'Ask',
   game_context:{league:'NFL',event_id:'00000000'}}),null)
 assert.equal(refereeQuickPrompts('Survivor')[0][0],'Available team')
 assert(refereeQuickPrompts('Props').some(pair=>pair[0]==='Why no PLAY?'))
})

test('source corrupt or old-market-only freeze never promotes model advantage',()=>{
 const bad=structuredClone(frozen)
 bad.wagers_created_or_bets_promoted=true
 const match=refMarketReview({odds,frozen:bad,nowMs:now,sport:'NFL'})
 assert(match.length>0)
 assert(match.every(x=>x.modelResearchPct===null))
 assert.equal(match.find(x=>x.eventId==='401872986').provenPositiveEV,false)
})
