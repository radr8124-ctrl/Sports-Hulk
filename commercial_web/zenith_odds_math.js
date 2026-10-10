// Sports Zenith — educational sportsbook math, independent of any betting model.
// Pure/offline calculations. No source enrichment, orders, or recommendations.
// Inputs never justify an assumption that a user probability is calibrated.

function amount(value, label, allowZero=false) {
  if (typeof value==='string' && value.trim()==='')throw new RangeError(label+' is required.')
  const n=Number(value)
  if (!Number.isFinite(n) || n < 0 || (n===0&&!allowZero) || n>1e9)
    throw new RangeError(label+' must be a finite, reasonable positive number.')
  return n
}
const round=(value,digits=6)=>Number(value.toFixed(digits))
function gcd(a,b){while(b){const t=b;b=a%b;a=t}return a}

export function americanToDecimal(american) {
  const n=Number(american)
  if (!Number.isInteger(n) || Math.abs(n)<100 || Math.abs(n)>1000000)
    throw new RangeError('American odds must be a whole price like -110 or +150 (absolute value at least 100).')
  return n>0?1+n/100:1+100/Math.abs(n)
}

export function decimalToAmerican(decimal){
  const d=amount(decimal,'Decimal odds')
  if (d<=1 || d>100000)throw new RangeError('Decimal odds must exceed 1.00.')
  const value=d>=2?(d-1)*100:-100/(d-1)
  return round(value,2)
}

function oddsDecimal(value,format){
  if (format==='american')return americanToDecimal(value)
  if (format==='decimal'){
    const d=amount(value,'Decimal odds')
    if (d<=1 || d>100000)throw new RangeError('Decimal odds must exceed 1.00.')
    return d
  }
  if (format==='fractional'){
    const match=String(value).trim().match(/^(\d+(?:\.\d+)?)\s*\/\s*(\d+(?:\.\d+)?)$/)
    if (!match)throw new RangeError('Enter fractional odds as numerator/denominator (example 5/2).')
    const numerator=amount(match[1],'Fraction numerator')
    const denominator=amount(match[2],'Fraction denominator')
    const d=1+numerator/denominator
    if (d>100000)throw new RangeError('Fractional odds are too large.')
    return d
  }
  if (format==='probability'){
    const pct=amount(value,'Probability')
    if(pct>=100)throw new RangeError('Implied probability must be above 0% and below 100%.')
    return 100/pct
  }
  throw new RangeError('Select American, decimal, fractional or implied percentage odds.')
}

function fractionApprox(value){
  const profit=value-1
  let closestNumerator=0,closestDenominator=1,difference=Infinity
  for(let denominator=1;denominator<=1000;denominator++){
    const numerator=Math.round(profit*denominator)
    const gap=Math.abs(profit-numerator/denominator)
    if(gap<difference){
      closestNumerator=numerator;closestDenominator=denominator;difference=gap
    }
    if(gap<1e-8)break
  }
  const div=gcd(closestNumerator,closestDenominator)
  return String(closestNumerator/div)+'/'+String(closestDenominator/div)
}

export function oddsConvert(value,format='american',stake=10){
  const d=oddsDecimal(value,format)
  const money=amount(stake,'Stake')
  return {
    decimal:round(d),
    american:decimalToAmerican(d),
    fractional:fractionApprox(d),
    impliedPct:round(100/d,4),
    profit:round(money*(d-1),2),
    totalReturn:round(money*d,2),
    stake:money,
    origin:'USER_ENTERED_MATH_ONLY',
    isVerifiedBookQuote:false,
  }
}

export function holdVig(first,second){
  const pa=1/americanToDecimal(first)
  const pb=1/americanToDecimal(second)
  const sum=pa+pb
  // Compare exactly one two-outcome market with no pushes/ties.
  const a=pa/sum,b=pb/sum
  return {
    bookHoldPct:round((sum-1)*100,4),
    sideAImpliedPct:round(pa*100,4),
    sideBImpliedPct:round(pb*100,4),
    sideANoVigPct:round(a*100,4),
    sideBNoVigPct:round(b*100,4),
    fairOddsA:decimalToAmerican(1/a),
    fairOddsB:decimalToAmerican(1/b),
    negativeHoldIsNotGuaranteedArbitrage:sum<1,
    noVigMethod:'TWO_SIDED_PROPORTIONAL_REMOVAL',
    trueProbabilityProven:false,
  }
}

export function evKelly(american,estimatePct,bankroll=1000){
  const d=americanToDecimal(american)
  const p=amount(estimatePct,'Estimated win probability')/100
  if(p>=1)throw new RangeError('Estimated win probability must be below 100%.')
  const funds=amount(bankroll,'Bankroll')
  const breakEven=1/d
  const edge=(p-breakEven)*100
  const returnPerUnit=p*(d-1)-(1-p)
  const full=Math.max(0,returnPerUnit/(d-1))
  return {
    breakEvenPct:round(breakEven*100,4),
    manualProbabilityPct:round(p*100,4),
    arithmeticEdgePp:round(edge,4),
    illustrativeEvPct:round(returnPerUnit*100,4),
    illustrativeEvPer100:round(returnPerUnit*100,2),
    fullKellyPct:round(full*100,4),
    halfKellyPct:round(full*50,4),
    quarterKellyPct:round(full*25,4),
    quarterKellyAmount:round(funds*full*.25,2),
    actualRecommendedStake:0,
    modelCalibrationVerified:false,
    positiveEvProven:false,
    assumptions:'USER_ESTIMATE_UNVERIFIED_NOT_A_BET_RECOMMENDATION',
  }
}

export function hedgeScenario(originalStake,originalOdds,otherOdds){
  const s=amount(originalStake,'Original stake')
  const first=americanToDecimal(originalOdds)
  const opposite=americanToDecimal(otherOdds)
  const hedge=s*first/opposite
  if(hedge>1e9)throw new RangeError('Hedge amount exceeds calculation limits.')
  const gross=s*first
  const originalWins=gross-s-hedge
  const otherWins=hedge*opposite-s-hedge
  return {
    originalStake:s,
    originalOdds:Number(originalOdds),
    oppositeOdds:Number(otherOdds),
    exampleEqualReturnHedge:round(hedge,2),
    totalAtRisk:round(s+hedge,2),
    originalWinsNet:round(originalWins,2),
    oppositeWinsNet:round(otherWins,2),
    originalReturn:round(gross,2),
    // Strictly a two-way mathematical illustration, not execution guarantee.
    outcomeRulesAndBookExecutionVerified:false,
    riskOfLossEvenAfterHedging:originalWins<0 || otherWins<0,
  }
}

export function parlayPayout(legs,stake=10,format='american'){
  if(!Array.isArray(legs)||legs.length<2||legs.length>12)
    throw new RangeError('Enter 2 to 12 odds for an illustration.')
  const s=amount(stake,'Stake')
  const decimals=legs.map(x=>x&&typeof x==='object' && !Array.isArray(x)
    ?oddsDecimal(x.value,x.format)
    :oddsDecimal(x,format))
  const combined=decimals.reduce((a,b)=>a*b,1)
  if(!Number.isFinite(combined)||combined>1e11)throw new RangeError('Combined decimal price exceeds calculation limits.')
  return {
    legs:legs.length,
    combinedDecimal:round(combined,6),
    combinedAmerican:decimalToAmerican(combined),
    combinedImpliedPct:round(100/combined,5),
    totalReturn:round(s*combined,2),
    profit:round(s*(combined-1),2),
    assumesIndependentLegs:true,
    sameGameCorrelationModeled:false,
    ticketPriceVerified:false,
    approvedOrSuggestedParlay:false,
    payoutOnlyNotExpectedValue:true,
  }
}
