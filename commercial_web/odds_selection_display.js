// Human-readable settlement requirement for one exact quoted outcome.
// No research claim about its likelihood, goodness or availability.
const n=value=>{
 if(value===null||value===undefined||value==='')return null
 const x=Number(value)
 return Number.isFinite(x)?x:null
}
export function quotedSideMeaning(game,market,side,item){
 const name=side==='AWAY'?game.away:side==='HOME'?game.home:null
 if(market==='MONEYLINE'){
   return name?{label:'Take '+name,requirement:name+' must win the game.'}:null
 }
 if(market==='SPREAD'){
   const line=n(item?.sides?.[side]?.line)
   if(!name||line===null)return null
   const signed=line>0?'+'+line:String(line)
   if(line<0){
     const threshold=Math.floor(Math.abs(line))+1
     return {label:'Take '+name+' '+signed,
       requirement:name+' must win by '+threshold+' or more'+(Number.isInteger(line)?'; exactly '+Math.abs(line)+' points is a push.':'.')}
   }
   if(line>0){
     const maxLoss=Number.isInteger(line)?Math.max(0,line-1):Math.floor(line)
     return {label:'Take '+name+' +'+line,
       requirement:name+' must win or lose by no more than '+maxLoss+(Number.isInteger(line)?' points; losing by '+line+' is a push.':' points.')}
   }
   return {label:'Take '+name+' +0',requirement:name+' must win; tied result can push.'}
 }
 if(market==='TOTAL'){
   const line=n(item?.line)
   if(line===null||!['OVER','UNDER'].includes(side))return null
   const noun=item?.market_subtype==='TOTAL_RUNS'?'runs':
     item?.market_subtype==='TOTAL_GOALS'?'goals':'points'
   const over=side==='OVER'
   const threshold=over?Math.floor(line)+1:(Number.isInteger(line)?line-1:Math.floor(line))
   const requirement=over?'Both teams combined must score '+threshold+' or more '+noun+'.':
     'Both teams combined must score '+threshold+' or fewer '+noun+'.'
   return {label:'Take '+(over?'Over':'Under')+' '+line+' '+noun,requirement}
 }
 return null
}

/** Convert a source-matched no-vig probability to a theoretical FAIR moneyline.
 * This is a market arithmetic benchmark, never a live bookmaker offer or a
 * stand-alone Zenith player/game winning probability. */
export function fairAmericanFromPercent(percent){
 if(percent===null||percent===undefined||percent==='')return null
 const p=Number(percent)
 if(!Number.isFinite(p)||p<=0||p>=100)return null
 const probability=p/100
 return probability>=.5
   ? -Math.round(100*probability/(1-probability))
   : Math.round(100*(1-probability)/probability)
}
