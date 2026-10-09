import test from 'node:test'
import assert from 'node:assert/strict'
import {quotedSideMeaning} from './odds_selection_display.js'

const game={away:'Philadelphia Eagles',home:'Jacksonville Jaguars'}
const ml={sides:{AWAY:{line:null},HOME:{line:null}}}
const spread={sides:{AWAY:{line:7.5},HOME:{line:-7.5}}}

test('moneyline identifies EXACT selected team, not just odds or both teams',()=>{
 const a=quotedSideMeaning(game,'MONEYLINE','AWAY',ml)
 const h=quotedSideMeaning(game,'MONEYLINE','HOME',ml)
 assert.equal(a.label,'BET ON Philadelphia Eagles')
 assert.match(a.requirement,/Philadelphia Eagles must win/)
 assert.equal(h.label,'BET ON Jacksonville Jaguars')
 assert.match(h.requirement,/Jacksonville Jaguars must win/)
 assert.notEqual(h.requirement,a.requirement)
})

test('spread settlement interprets sign and decimal correctly',()=>{
 const away=quotedSideMeaning(game,'SPREAD','AWAY',spread)
 const home=quotedSideMeaning(game,'SPREAD','HOME',spread)
 assert.equal(away.label,'BET ON Philadelphia Eagles +7.5')
 assert.match(away.requirement,/lose by no more than 7 points/)
 assert.equal(home.label,'BET ON Jacksonville Jaguars -7.5')
 assert.match(home.requirement,/win by 8 or more/)
})

test('whole-number spreads disclose push correctly',()=>{
 const point={sides:{AWAY:{line:3},HOME:{line:-3}}}
 assert.match(quotedSideMeaning(game,'SPREAD','AWAY',point).requirement,/losing by 3 is a push/)
 assert.match(quotedSideMeaning(game,'SPREAD','HOME',point).requirement,/exactly 3 points is a push/)
})

test('game total keeps exact scoring unit, not player metric',()=>{
 for(const [subtype,unit] of [['TOTAL_POINTS','points'],['TOTAL_GOALS','goals'],['TOTAL_RUNS','runs']]){
  const total={line:42.5,market_subtype:subtype}
  const over=quotedSideMeaning(game,'TOTAL','OVER',total)
  const under=quotedSideMeaning(game,'TOTAL','UNDER',total)
  assert.equal(over.label,'BET OVER 42.5 '+unit)
  assert.match(over.requirement,new RegExp('43 or more '+unit))
  assert.match(under.requirement,new RegExp('42 or fewer '+unit))
 }
})

test('unverified or unknown missing line does not produce invented requirements',()=>{
 assert.equal(quotedSideMeaning(game,'SPREAD','AWAY',{sides:{}}),null)
 assert.equal(quotedSideMeaning(game,'TOTAL','OVER',{line:null}),null)
 assert.equal(quotedSideMeaning(game,'HOMERUNS','OVER',{}),null)
})
