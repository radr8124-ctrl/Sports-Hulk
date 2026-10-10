import React,{useEffect,useRef,useState} from 'react'
import {ArrowLeftRight,Flag,Hand,MessageCircle,Volume2,X,BarChart3} from 'lucide-react'
import ZenithRefAvatar from './ZenithRefAvatar.jsx'

// Decorative sports calls, not claims of real-game penalties or betting signals.
const words={idle:'THE REF IS IN',flag:'FLAG ON THE PLAY!',strike:'STRIKE THREE!',whistle:'FWEET! WHISTLE!'}
function shortWhistle(){
 try{
  const Sound=window.AudioContext||window.webkitAudioContext
  if(!Sound)return
  const ctx=new Sound(),osc=ctx.createOscillator(),volume=ctx.createGain()
  void ctx.resume().catch(()=>{}) // helps explicit-tap iOS Safari audio unlock
  osc.type='sine'
  osc.frequency.setValueAtTime(790,ctx.currentTime)
  osc.frequency.exponentialRampToValueAtTime(1050,ctx.currentTime+.18)
  volume.gain.setValueAtTime(.0001,ctx.currentTime)
  volume.gain.exponentialRampToValueAtTime(.018,ctx.currentTime+.03)
  volume.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+.24)
  osc.connect(volume);volume.connect(ctx.destination)
  osc.start();osc.stop(ctx.currentTime+.26)
  osc.onended=()=>{void ctx.close().catch(()=>{})}
 }catch{/* No audio supported: visual signal still works. */}
}
export default function ZenithRefCompanion({onOpenAsk,onOpenBrain}){
 const [expanded,setExpanded]=useState(false)
 const [left,setLeft]=useState(false)
 const [signal,setSignal]=useState({kind:'idle',id:0})
 const number=useRef(0)
 useEffect(()=>{
  if(signal.kind==='idle')return
  const handle=window.setTimeout(()=>setSignal(now=>now.id===signal.id?{kind:'idle',id:now.id}:now),1750)
  return()=>window.clearTimeout(handle)
 },[signal])
 const call=kind=>{
  number.current+=1
  setSignal({kind,id:number.current})
  if(kind==='whistle')shortWhistle() // user action only, never autoplay
 }
 return <aside aria-label="The Ref sports companion" data-ref-companion data-signal={signal.kind} data-side={left?'left':'right'}
  className={`pointer-events-none fixed z-[38] bottom-[calc(6.5rem+env(safe-area-inset-bottom))] ${left?'left-3':'right-3'} flex max-w-[calc(100vw-24px)] flex-col items-end gap-2 lg:bottom-6`}>
  {expanded&&<div role="group" aria-label="The Ref quick calls"
   className="pointer-events-auto w-[min(264px,calc(100vw-30px))] rounded-2xl border-2 border-[#173E52] bg-[#FFF5E4] p-3 text-[#173E52] shadow-[4px_4px_0_#46CDD2]">
   <div className="flex items-center justify-between gap-2">
    <b className="text-xs uppercase tracking-wider">The Ref · Game calls</b>
    <button type="button" aria-label="Close The Ref calls" onClick={()=>setExpanded(false)}
     className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#B6D4CE] bg-white"><X size={16}/></button>
   </div>
   <p className="mt-1 text-[11px] font-semibold text-[#526A73]">Tap a move or ask a sports question.</p>
   <div className="mt-2 grid grid-cols-3 gap-1.5">
    <button type="button" onClick={()=>call('flag')} aria-label="The Ref throws a flag"
     className="min-h-11 rounded-lg border border-[#E2BB75] bg-[#FFF0C6] px-1 text-[11px] font-black"><Flag size={15} className="mx-auto mb-0.5"/>Flag</button>
    <button type="button" onClick={()=>call('strike')} aria-label="The Ref signals strike three"
     className="min-h-11 rounded-lg border border-[#AED5D1] bg-[#DBF4F0] px-1 text-[11px] font-black"><Hand size={15} className="mx-auto mb-0.5"/>Strikeout</button>
    <button type="button" onClick={()=>call('whistle')} aria-label="The Ref blows a whistle"
     className="min-h-11 rounded-lg border border-[#E7B7A6] bg-[#FFE4D9] px-1 text-[11px] font-black"><Volume2 size={15} className="mx-auto mb-0.5"/>Whistle</button>
   </div>
   <div className="mt-2 grid grid-cols-2 gap-1.5">
    <button type="button" onClick={onOpenAsk} className="flex min-h-10 items-center justify-center gap-1 rounded-lg bg-[#FF7766] px-2 text-xs font-black"><MessageCircle size={14}/> Ask The Ref</button>
    <button type="button" onClick={onOpenBrain} className="flex min-h-10 items-center justify-center gap-1 rounded-lg border border-[#173E52] bg-white px-2 text-xs font-black"><BarChart3 size={14}/> Brain Record</button>
   </div>
   <button type="button" onClick={()=>{setLeft(!left);setExpanded(false)}} className="mt-2 flex min-h-9 w-full items-center justify-center gap-1 text-[11px] font-black text-[#276273]"><ArrowLeftRight size={14}/> Move Ref to the {left?'right':'left'}</button>
  </div>}
  <div className="pointer-events-auto relative flex items-center gap-2">
   <div aria-live="polite" className={`max-w-[134px] rounded-xl border border-[#173E52] bg-[#FFF5E4] px-2 py-1.5 text-center text-[10px] font-black leading-4 text-[#173E52] shadow-sm ${expanded||signal.kind!=='idle'?'':'hidden sm:block'}`}>{words[signal.kind]}</div>
   <button type="button" aria-label="Open The Ref animated sports companion" aria-expanded={expanded}
    onClick={()=>setExpanded(value=>!value)}
    className={`zenith-ref-mascot relative flex h-[70px] w-[70px] items-center justify-center rounded-full border-[3px] border-[#173E52] bg-[#173E52] shadow-[3px_4px_0_#FF7766] transition hover:scale-105 zenith-ref--${signal.kind}`}>
    <span className="zenith-ref-idle" aria-hidden="true"><ZenithRefAvatar size={62} compact/></span>
    <span className="zenith-ref-signal-arm absolute -right-1 top-4 h-8 w-2 origin-bottom-left rotate-[-35deg] rounded-full border border-[#173E52] bg-[#FFF5E4]" aria-hidden="true"/>
    <span className="zenith-ref-flag absolute -top-4 right-2" aria-hidden="true"><Flag size={30} fill="#FFD36A" stroke="#173E52" strokeWidth={2}/></span>
    <span className="zenith-ref-whistle-burst absolute -top-6 left-1/2 -translate-x-1/2 rounded-md border border-[#173E52] bg-[#FFD36A] px-1.5 py-0.5 text-[9px] font-black" aria-hidden="true">FWEET!</span>
    <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 rounded-sm bg-[#46CDD2] px-1 text-[8px] font-black leading-3 text-[#173E52]" aria-hidden="true">REF</span>
   </button>
  </div>
 </aside>
}
