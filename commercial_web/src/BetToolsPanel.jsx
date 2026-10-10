import React,{useMemo,useState} from 'react'
import {BarChart3,Calculator,ChevronDown,ShieldAlert,ShieldCheck,SlidersHorizontal} from 'lucide-react'
import {oddsConvert,holdVig,evKelly,hedgeScenario,parlayPayout} from '../zenith_odds_math.js'

const FORMATS=[
  {value:'american',label:'American'},
  {value:'decimal',label:'Decimal'},
  {value:'fractional',label:'Fractional'},
  {value:'probability',label:'Implied probability (%)'},
]
const SECTIONS=[
  {id:'CONVERT',label:'Odds'},
  {id:'HOLD',label:'Hold & no-vig'},
  {id:'EV',label:'EV & Kelly'},
  {id:'HEDGE',label:'Hedge'},
  {id:'PARLAY',label:'Parlay payout'},
]
const cash=n=>Number.isFinite(n)?n.toLocaleString('en-US',{style:'currency',currency:'USD'}):'—'
const percent=(n,d=2)=>Number.isFinite(n)?n.toFixed(d)+'%':'—'
const quote=n=>Number.isFinite(n)?(n>0?'+':'')+Number(n.toFixed(2)):'—'
const fieldClasses='mt-1.5 h-11 w-full min-w-0 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100'

function Field({label,value,onChange,placeholder='',type='text',step='any'}){
 return <label className="block min-w-0">
    <span className="text-[11px] font-black text-slate-700">{label}</span>
    <input aria-label={label} type={type} step={step} value={value}
      onChange={event=>onChange(event.target.value)} placeholder={placeholder}
      className={fieldClasses}/>
  </label>
}
function Stat({label,value,detail}) {
 return <div className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
   <p className="text-[10px] font-black uppercase tracking-wide text-slate-500">{label}</p>
   <p className="mt-1 break-words text-xl font-black tabular-nums text-slate-950">{value}</p>
   {detail&&<p className="mt-1 text-[11px] leading-4 text-slate-500">{detail}</p>}
 </div>
}
function Warning({children}){
 return <p className="mt-3 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs leading-5 text-amber-950">
   <ShieldAlert size={17} className="mt-0.5 shrink-0 text-amber-700"/>{children}
 </p>
}

export default function BetToolsPanel() {
  const [mode,setMode]=useState('CONVERT')
  const [format,setFormat]=useState('american')
  const [odds,setOdds]=useState('-110')
  const [stake,setStake]=useState('10')
  const [side1,setSide1]=useState('-110')
  const [side2,setSide2]=useState('-110')
  const [manualProb,setManualProb]=useState('55')
  const [bankroll,setBankroll]=useState('1000')
  const [originalStake,setOriginalStake]=useState('100')
  const [originalOdds,setOriginalOdds]=useState('+200')
  const [oppositeOdds,setOppositeOdds]=useState('-150')
  const [legs,setLegs]=useState([{value:'-110',format:'american'},{value:'-110',format:'american'}])
  const [parlayStake,setParlayStake]=useState('10')

  const calc=useMemo(()=>{
    try{
      const value=mode==='CONVERT'?oddsConvert(odds,format,stake)
        :mode==='HOLD'?holdVig(side1,side2)
        :mode==='EV'?evKelly(odds,manualProb,bankroll)
        :mode==='HEDGE'?hedgeScenario(originalStake,originalOdds,oppositeOdds)
        :parlayPayout(legs,parlayStake)
      return {ok:true,value}
    }catch(error){return {ok:false,reason:error.message||'Invalid odds input.'}}
  },[mode,format,odds,stake,side1,side2,manualProb,bankroll,originalStake,originalOdds,oppositeOdds,legs,parlayStake])

  const updateLeg=(index,field,value)=>setLegs(prev=>prev.map((x,i)=>i===index?{...x,[field]:value}:x))
  const result=calc.ok?calc.value:null

  return <section aria-label="Zenith betting math tools" className="space-y-4">
    <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-[#071b2d] via-[#0b2b46] to-[#0b3657] p-4 text-white shadow-soft md:p-6">
      <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-sky-300">
        <Calculator size={17}/> Sports Zenith · Tools
      </div>
      <h1 className="mt-2 text-2xl font-black tracking-tight md:text-3xl">Know the price. See the math.</h1>
      <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-300 md:text-sm">
        Convert odds, understand bookmaker margin and work through risk scenarios.
        These tools use your inputs, not a proven Zenith betting forecast.
      </p>
      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-[11px] font-semibold text-slate-300">
        <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-sky-300"/> Local calculations</span>
        <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-sky-300"/> No bets placed</span>
        <span className="flex items-center gap-1"><ShieldCheck size={14} className="text-sky-300"/> No model edge invented</span>
      </div>
    </div>

    <div role="group" aria-label="Choose betting calculation" className="flex gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-soft">
      {SECTIONS.map(item=><button key={item.id} type="button"
        aria-pressed={mode===item.id}
        onClick={()=>setMode(item.id)}
        className={'min-h-11 shrink-0 rounded-xl px-3 py-2 text-xs font-black transition '+
          (mode===item.id?'bg-slate-950 text-white':'text-slate-600 hover:bg-slate-50')}>
        {item.label}
      </button>)}
    </div>

    <div className="grid gap-3 xl:grid-cols-[minmax(0,.9fr)_minmax(0,1.1fr)]">
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft md:p-5">
        <div className="flex items-center gap-2">
          <SlidersHorizontal size={17} className="text-blue-700"/>
          <h2 className="text-base font-black text-slate-950">
            {SECTIONS.find(x=>x.id===mode)?.label} inputs
          </h2>
        </div>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          {mode==='CONVERT'?'Compare formats and see the break-even win probability at this exact price.'
            :mode==='HOLD'?'Use the two opposite sides of one exact market at the same sportsbook and line.'
            :mode==='EV'?'Use an independently justified probability, not the sportsbook market percentage, for a meaningful edge estimate.'
            :mode==='HEDGE'?'Compare outcomes for two opposite, mutually exclusive and exhaustive results.'
            :'Illustrate a potential payout only. This does not construct or recommend a parlay.'}
        </p>

        {mode==='CONVERT'&&<div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="block min-w-0">
            <span className="text-[11px] font-black text-slate-700">Input odds format</span>
            <select aria-label="Input odds format" value={format}
              onChange={e=>{const f=e.target.value;setFormat(f);setOdds(f==='american'?'-110':f==='decimal'?'1.91':f==='fractional'?'10/11':'52.38')}}
              className={fieldClasses}>
              {FORMATS.map(f=><option key={f.value} value={f.value}>{f.label}</option>)}
            </select>
          </label>
          <Field label="Quoted odds" value={odds} onChange={setOdds}/>
          <Field label="Example stake ($)" value={stake} onChange={setStake} type="number"/>
        </div>}

        {mode==='HOLD'&&<div className="mt-4 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Side A American odds" value={side1} onChange={setSide1}/>
            <Field label="Side B American odds" value={side2} onChange={setSide2}/>
          </div>
          <div className="flex flex-wrap gap-2">
            {[['-110','-110'],['-200','+170'],['-105','-105']].map(pair=><button
              type="button" key={pair.join('/')} onClick={()=>{setSide1(pair[0]);setSide2(pair[1])}}
              className="min-h-9 rounded-lg border border-slate-200 bg-slate-50 px-3 text-[11px] font-bold text-slate-700">
              {pair.join(' / ')}
            </button>)}
          </div>
        </div>}

        {mode==='EV'&&<div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Field label="Offered American odds" value={odds} onChange={setOdds}/>
          <Field label="Your independent probability (%)" value={manualProb} onChange={setManualProb} type="number"/>
          <Field label="Illustrative bankroll ($)" value={bankroll} onChange={setBankroll} type="number"/>
        </div>}

        {mode==='HEDGE'&&<div className="mt-4 grid gap-3 sm:grid-cols-2">
          <Field label="Original stake ($)" value={originalStake} onChange={setOriginalStake} type="number"/>
          <Field label="Original American odds" value={originalOdds} onChange={setOriginalOdds}/>
          <Field label="Opposing American odds" value={oppositeOdds} onChange={setOppositeOdds}/>
        </div>}

        {mode==='PARLAY'&&<div className="mt-4 space-y-3">
          <Field label="Example parlay stake ($)" value={parlayStake} onChange={setParlayStake} type="number"/>
          <div className="grid gap-2 sm:grid-cols-2">
            {legs.map((leg,index)=><label key={index} className="block min-w-0">
              <span className="flex items-center justify-between gap-1 text-[11px] font-black text-slate-700">
                <span>Leg {index+1} American odds</span>
                {legs.length>2&&<button type="button" aria-label={'Remove leg '+(index+1)}
                  onClick={()=>setLegs(prev=>prev.filter((_,i)=>i!==index))}
                  className="text-blue-700 underline">Remove</button>}
              </span>
              <div className="mt-1.5 flex min-w-0 gap-2">
                <input aria-label={'Leg '+(index+1)+' odds'} value={leg.value}
                  onChange={event=>updateLeg(index,'value',event.target.value)}
                  className="h-11 min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-900"/>
                <select aria-label={'Leg '+(index+1)+' format'} value={leg.format}
                  onChange={event=>{const format=event.target.value;setLegs(prev=>prev.map((x,i)=>i===index?{value:format==='american'?'-110':format==='decimal'?'1.91':format==='fractional'?'10/11':'52.38',format}:x))}}
                  className="h-11 w-28 min-w-0 rounded-xl border border-slate-200 bg-white px-2 text-[11px] font-bold text-slate-800">
                  {FORMATS.map(option=><option key={option.value} value={option.value}>{option.label}</option>)}
                </select>
              </div>
            </label>)}
          </div>
          <button type="button" disabled={legs.length>=12}
            onClick={()=>setLegs(prev=>[...prev,{value:'-110',format:'american'}])}
            className="min-h-10 rounded-xl border border-blue-200 bg-white px-3 text-xs font-black text-blue-700 disabled:opacity-30">
            Add another example leg
          </button>
        </div>}
      </section>

      <section aria-label="Calculation result" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft md:p-5">
        <div className="flex items-center justify-between gap-2">
          <h2 className="flex items-center gap-2 text-base font-black text-slate-950">
            <BarChart3 size={17} className="text-blue-700"/>Calculation
          </h2>
          <span className="text-[10px] font-bold text-slate-500">Illustration · not a live quote</span>
        </div>
        {!result? <div role="alert" className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold text-amber-900">{calc.reason}</div>
        :mode==='CONVERT'?<>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat label="American" value={quote(result.american)}/>
            <Stat label="Decimal" value={result.decimal.toFixed(4)}/>
            <Stat label="Fractional (approx.)" value={result.fractional}/>
            <Stat label="Break-even probability" value={percent(result.impliedPct,2)}/>
            <Stat label="Example profit" value={cash(result.profit)}/>
            <Stat label="Example total return" value={cash(result.totalReturn)}/>
          </div>
          <Warning>Implied probability is the break-even rate at an offered price, not the probability a team or player will win.</Warning>
        </>:mode==='HOLD'?<>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat label="Bookmaker hold / vig" value={percent(result.bookHoldPct,2)}/>
            <Stat label="No-vig A" value={percent(result.sideANoVigPct,2)}
              detail={'Fair odds '+quote(result.fairOddsA)}/>
            <Stat label="No-vig B" value={percent(result.sideBNoVigPct,2)}
              detail={'Fair odds '+quote(result.fairOddsB)}/>
            <Stat label="Combined implied" value={percent(result.sideAImpliedPct+result.sideBImpliedPct,2)}/>
          </div>
          <Warning>{result.negativeHoldIsNotGuaranteedArbitrage?'Negative hold on manual inputs does not prove an executable arbitrage.':'No-vig percentages remove the two-way book margin proportionally; they are still market estimates, not proven true probabilities.'}</Warning>
        </>:mode==='EV'?<>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat label="Price break-even" value={percent(result.breakEvenPct,2)}/>
            <Stat label="Manual probability" value={percent(result.manualProbabilityPct,2)}/>
            <Stat label="Hypothetical EV" value={percent(result.illustrativeEvPct,2)}/>
            <Stat label="Probability gap" value={percent(result.arithmeticEdgePp,2)}/>
            <Stat label="Full Kelly (math)" value={percent(result.fullKellyPct,2)}/>
            <Stat label="Quarter Kelly (math)" value={cash(result.quarterKellyAmount)}
              detail={percent(result.quarterKellyPct,2)+' of illustrated bankroll'}/>
          </div>
          <Warning>No verified independent model probability was supplied by Zenith. This is arithmetic on your estimate. Actual recommended exposure remains 0 units until the prediction and executable quote pass the proof gates.</Warning>
        </>:mode==='HEDGE'?<>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat label="Equal-gross-return hedge" value={cash(result.exampleEqualReturnHedge)}/>
            <Stat label="Total cash at risk" value={cash(result.totalAtRisk)}/>
            <Stat label="Original side wins · net" value={cash(result.originalWinsNet)}/>
            <Stat label="Opposite side wins · net" value={cash(result.oppositeWinsNet)}/>
          </div>
          <Warning>{result.riskOfLossEvenAfterHedging?'Both outcomes can still produce a locked-in loss at these odds. ':'This arithmetic assumes two outcomes cover every possible settlement. '}Prices, voids, pushes, limits, and the ability to execute both sides are unverified. No hedge has been placed.</Warning>
        </>:<>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <Stat label="Example legs" value={String(result.legs)}/>
            <Stat label="Combined decimal" value={result.combinedDecimal.toFixed(3)}/>
            <Stat label="Combined American" value={quote(result.combinedAmerican)}/>
            <Stat label="Price-implied win rate" value={percent(result.combinedImpliedPct,3)}/>
            <Stat label="Example profit" value={cash(result.profit)}/>
            <Stat label="Example total return" value={cash(result.totalReturn)}/>
          </div>
          <Warning>This is only a theoretical all-legs-win payout. Same-game correlations, changes in price, pushes, and sportsbook settlement rules are not modeled. No parlay is recommended or generated.</Warning>
        </>}
        <details className="mt-3 rounded-xl border border-slate-200 bg-white p-3">
          <summary className="flex min-h-10 cursor-pointer items-center justify-between gap-2 text-xs font-black text-blue-700">
            What this result does and doesn't tell you
            <ChevronDown size={16} className="shrink-0"/>
          </summary>
          <p className="pt-2 text-xs leading-5 text-slate-600">
            These formulas are deterministic and operate only on entered numbers. They do not check sportsbook logins,
            live prices, model calibration, injury news, account limits, taxation, jurisdiction, or game settlement.
            Use Sports Zenith's separate odds board and Brain Record for actual timestamped research and model accountability.
          </p>
        </details>
      </section>
    </div>
  </section>
}
