import test from 'node:test'
import assert from 'node:assert/strict'
import {americanToDecimal,decimalToAmerican,oddsConvert,holdVig,evKelly,hedgeScenario,parlayPayout} from './zenith_odds_math.js'

const close=(got,want,tolerance=.01)=>assert.ok(Math.abs(got-want)<tolerance,'Expected '+got+' to approximate '+want)

test('American odds converter shows true break-even, stake profit and total return',()=>{
 const favorite=oddsConvert('-110','american','10')
 close(favorite.decimal,1.9090909,.00001)
 close(favorite.impliedPct,52.38095,.0001)
 assert.equal(favorite.profit,9.09)
 assert.equal(favorite.totalReturn,19.09)
 assert.equal(favorite.american,-110)
 assert.equal(favorite.fractional,'10/11')
 const underdog=oddsConvert('+150','american',25)
 assert.equal(underdog.decimal,2.5)
 assert.equal(underdog.impliedPct,40)
 assert.equal(underdog.profit,37.5)
 assert.equal(underdog.totalReturn,62.5)
})

test('Decimal, fractional, and percentage odds all converge to same price',()=>{
 const frac=oddsConvert('5/2','fractional',100)
 assert.equal(frac.decimal,3.5)
 assert.equal(frac.impliedPct,28.5714)
 assert.equal(frac.american,250)
 const pct=oddsConvert('40','probability',100)
 assert.equal(pct.decimal,2.5)
 assert.equal(pct.american,150)
 const dec=oddsConvert('1.6666666666667','decimal',100)
 close(dec.american,-150,.00001)
})

test('Two-sided hold and no-vig use matched outcome prices without claiming true probabilities',()=>{
 const r=holdVig(-110,-110)
 close(r.bookHoldPct,4.7619,.001)
 assert.equal(r.sideANoVigPct,50)
 assert.equal(r.sideBNoVigPct,50)
 assert.equal(r.fairOddsA,100)
 assert.equal(r.fairOddsB,100)
 assert.equal(r.trueProbabilityProven,false)
 const b=holdVig(-200,170)
 close(b.bookHoldPct,3.7037,.001)
 close(b.sideANoVigPct+b.sideBNoVigPct,100,.0002)
})

test('A negative hold is theoretical only, not guaranteed executable arbitrage',()=>{
 const r=holdVig(110,110)
 assert.ok(r.bookHoldPct<0)
 assert.equal(r.negativeHoldIsNotGuaranteedArbitrage,true)
})

test('EV and quarter Kelly are pure user-entered math, never promoted to a real bet',()=>{
 const r=evKelly(-110,55,1000)
 close(r.breakEvenPct,52.38095,.0001)
 close(r.illustrativeEvPct,5,.00001)
 close(r.fullKellyPct,5.5,.00001)
 close(r.quarterKellyPct,1.375,.00001)
 assert.equal(r.quarterKellyAmount,13.75)
 assert.equal(r.actualRecommendedStake,0)
 assert.equal(r.positiveEvProven,false)
 assert.equal(r.modelCalibrationVerified,false)
})

test('Negative manual EV yields zero Kelly exposure and no recommended stake',()=>{
 const r=evKelly(-110,50,1000)
 assert.ok(r.illustrativeEvPct<0)
 assert.equal(r.quarterKellyAmount,0)
 assert.equal(r.fullKellyPct,0)
 assert.equal(r.actualRecommendedStake,0)
})

test('Hedge example balances the two exclusive outcomes but can still lock in a loss',()=>{
 const profit=hedgeScenario(100,200,-150)
 close(profit.exampleEqualReturnHedge,180,.001)
 close(profit.originalWinsNet,20,.001)
 close(profit.oppositeWinsNet,20,.001)
 assert.equal(profit.outcomeRulesAndBookExecutionVerified,false)
 const loss=hedgeScenario(100,-110,-110)
 close(loss.exampleEqualReturnHedge,100,.001)
 assert.equal(loss.riskOfLossEvenAfterHedging,true)
 assert.ok(loss.originalWinsNet<0)
})

test('Parlay multiplies independent price decimals, estimates payout, never recommends a ticket',()=>{
 const two=parlayPayout(['-110','-110'],10,'american')
 close(two.combinedDecimal,3.644628,.00001)
 assert.equal(two.totalReturn,36.45)
 assert.equal(two.profit,26.45)
 assert.equal(two.sameGameCorrelationModeled,false)
 assert.equal(two.approvedOrSuggestedParlay,false)
 const three=parlayPayout(['-110','-150','+120'],25)
 close(three.combinedDecimal,7,.00001)
 assert.equal(three.totalReturn,175)
 assert.equal(three.profit,150)
 assert.equal(three.payoutOnlyNotExpectedValue,true)
})

test('Mixed parlay price formats convert accurately but remain unapproved',()=>{
 const mixed=parlayPayout([
   {value:'-110',format:'american'},
   {value:'1.91',format:'decimal'},
   {value:'5/2',format:'fractional'},
 ],10)
 close(mixed.combinedDecimal,(1+100/110)*1.91*3.5,.00001)
 assert.equal(mixed.approvedOrSuggestedParlay,false)
 assert.equal(mixed.sameGameCorrelationModeled,false)
})

test('All odds tools reject nonsensical input instead of showing fabricated edge',()=>{
 for(const odds of [-99,99,0,1,undefined,NaN,Infinity]){
   assert.throws(()=>americanToDecimal(odds),RangeError)
 }
 assert.throws(()=>oddsConvert('0/1','fractional'),RangeError)
 assert.throws(()=>oddsConvert('2/0','fractional'),RangeError)
 assert.throws(()=>oddsConvert('foo','fractional'),RangeError)
 assert.throws(()=>oddsConvert('1.0','decimal'),RangeError)
 assert.throws(()=>oddsConvert('100','probability'),RangeError)
 assert.throws(()=>oddsConvert('0','probability'),RangeError)
 assert.throws(()=>oddsConvert('-110','american',-100),RangeError)
 assert.throws(()=>evKelly(-110,100,1000),RangeError)
 assert.throws(()=>evKelly(-110,0,1000),RangeError)
 assert.throws(()=>evKelly(-110,55,0),RangeError)
 assert.throws(()=>hedgeScenario(100,-110,-99),RangeError)
 assert.throws(()=>parlayPayout([-110],10),RangeError)
 assert.throws(()=>parlayPayout(Array.from({length:13},()=>-110),10),RangeError)
 assert.throws(()=>parlayPayout([-110,-100],-10),RangeError)
 assert.throws(()=>decimalToAmerican(1),RangeError)
})
