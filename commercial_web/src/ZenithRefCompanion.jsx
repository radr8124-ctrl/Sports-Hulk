import React,{useEffect,useRef,useState} from 'react'
import {createPortal} from 'react-dom'
import {ArrowLeftRight,BarChart3,Flag,Hand,MessageCircle,Volume2,X,Minimize2,Maximize2} from 'lucide-react'
import ZenithRefAvatar from './ZenithRefAvatar.jsx'
import {canAutoPerform,nextRefCall,nextRefDelay,REF_MANUAL_PAUSE_MS} from '../ref_motion_presentation.js'
import './ZenithRefCompanion.css'

// The Ref is an original site mascot. These theatrical calls are never
// official game events, injury reports or betting-model recommendations.
const callText={idle:'ASK THE REF',flag:'FLAG ON THE PLAY!',strike:'STRIKE THREE!',whistle:'FWEET! WHISTLE!'}
const REF_AUTO_STORAGE_KEY='zenith-ref-surprise-calls-v1'
function savedAutoPreference(){
 try{return window.localStorage.getItem(REF_AUTO_STORAGE_KEY)!=='off'}catch{return true}
}
const sideline=[
 {key:'welcome',name:'GAME DAY',selector:'[aria-label="Sports Zenith game-day command center"]',bottom:25},
 {key:'scores',name:'SCOREBOARD',selector:'[aria-label="Game Day scores and schedule"]',bottom:34},
 {key:'signals',name:'SIGNAL BOARD',selector:'[aria-label="Home decision overview"]',bottom:21},
 {key:'news',name:'NEWSROOM',selector:'[aria-label="Home sports news"]',bottom:39},
 {key:'picks',name:'SURVIVOR & FANTASY',selector:'[aria-label="Home Fantasy Survivor and Brain Record"]',bottom:27},
 {key:'learning',name:'LEARNING LAB',selector:'[aria-label="Home learning loop"]',bottom:45},
]

function shortWhistle(){
 // A quiet cue, created only inside the user-triggered whistle click.
 try {
  const Audio=window.AudioContext||window.webkitAudioContext
  if(!Audio)return
  const ctx=new Audio(),tone=ctx.createOscillator(),gain=ctx.createGain()
  void ctx.resume().catch(()=>{})
  tone.type='sine'
  tone.frequency.setValueAtTime(740,ctx.currentTime)
  tone.frequency.exponentialRampToValueAtTime(1020,ctx.currentTime+.19)
  gain.gain.setValueAtTime(.0001,ctx.currentTime)
  gain.gain.exponentialRampToValueAtTime(.022,ctx.currentTime+.035)
  gain.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+.25)
  tone.connect(gain);gain.connect(ctx.destination)
  tone.start();tone.stop(ctx.currentTime+.27)
  tone.onended=()=>{void ctx.close().catch(()=>{})}
 }catch{/* Browsers without WebAudio still show the visual whistle call. */}
}

function RefFigure(){
 return (
  <svg className="zenith-ref-figure" viewBox="0 0 180 222" width="100%" height="100%"
   role="img" aria-label="The Ref wearing a striped referee jersey">
   <defs>
    <linearGradient id="ref-coral-signal" x1="0" y1="0" x2="1" y2="1">
     <stop offset="0" stopColor="#FFA291"/><stop offset="1" stopColor="#FF7468"/>
    </linearGradient>
   </defs>
   <ellipse cx="90" cy="211" rx="64" ry="8" fill="#173E52" opacity=".19"/>
   <circle cx="90" cy="100" r="77" fill="url(#ref-coral-signal)" stroke="#173E52" strokeWidth="4"/>
   <path d="M25 87Q65 48 133 79" stroke="#FFE3AA" strokeWidth="6" fill="none" opacity=".65"/>
   <path d="M35 134Q89 177 149 126" stroke="#FFD36A" strokeWidth="5" fill="none" opacity=".72"/>
   <g className="zenith-ref-left-arm">
    <path d="M58 126 Q32 143 22 161" stroke="#173E52" strokeWidth="16" strokeLinecap="round" fill="none"/>
    <path d="M58 126 Q32 143 22 161" stroke="#FFF6E6" strokeWidth="10" strokeLinecap="round" fill="none"/>
    <circle cx="22" cy="162" r="9" fill="#173E52"/>
   </g>
   <g className="zenith-ref-right-arm">
    <path d="M123 128 Q149 148 151 165" stroke="#173E52" strokeWidth="16" strokeLinecap="round" fill="none"/>
    <path d="M123 128 Q149 148 151 165" stroke="#FFF6E6" strokeWidth="10" strokeLinecap="round" fill="none"/>
    <circle cx="152" cy="166" r="9" fill="#173E52"/>
   </g>
   <path d="M66 174L59 202H79L87 181M113 174L123 202H103L95 181" stroke="#173E52"
    strokeWidth="7" strokeLinejoin="round" fill="#0C2234"/>
   <path d="M62 112Q55 125 55 139L58 182Q89 192 124 181L127 139Q128 123 117 112Z"
    fill="#FFF9EC" stroke="#173E52" strokeWidth="5"/>
   <path d="M71 115V183M82 115V187M94 115V187M106 115V183M116 119V178" stroke="#173E52" strokeWidth="6"/>
   <rect x="72" y="152" width="36" height="29" rx="7" fill="#173E52" stroke="#46CDD2" strokeWidth="2"/>
   <text x="90" y="173" fontSize="23" fontWeight="900" textAnchor="middle" fill="#FFD36A">Z</text>
   <g transform="translate(37 10)">
     <ZenithRefAvatar size={106} compact/>
   </g>
   <g className="zenith-ref-flag" aria-hidden="true">
    <path d="M148 138L159 100" stroke="#173E52" strokeWidth="4" strokeLinecap="round"/>
    <path d="M159 100Q170 92 178 102L165 120L153 114Z" fill="#FFD36A" stroke="#173E52" strokeWidth="3"/>
   </g>
   <g className="zenith-ref-sound-burst" aria-hidden="true">
    <rect x="42" y="1" width="97" height="26" rx="11" fill="#FFD36A" stroke="#173E52" strokeWidth="3"/>
    <text x="90" y="19" fontWeight="900" fontSize="12" textAnchor="middle" fill="#173E52">FWEEEET!</text>
   </g>
   <rect x="40" y="194" width="100" height="21" rx="7" fill="#173E52"/>
   <text x="90" y="209" fontSize="12" fontWeight="900" letterSpacing="1.5"
    textAnchor="middle" fill="#FFF5E4">THE REF</text>
  </svg>
 )
}

export default function ZenithRefCompanion({onOpenAsk,onOpenBrain,page='Home'}){
 const [expanded,setExpanded]=useState(false)
 const [minimized,setMinimized]=useState(false)
 const [left,setLeft]=useState(false)
 const [signal,setSignal]=useState({kind:'idle',id:0,origin:'none'})
 const [section,setSection]=useState(page==='News & Insights'?'news':'welcome')
 const [autoEnabled,setAutoEnabled]=useState(savedAutoPreference)
 const [mobileScreen,setMobileScreen]=useState(()=>window.matchMedia?.('(max-width: 767px)').matches||false)
 const [reducedMotion,setReducedMotion]=useState(()=>window.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false)
 const [visible,setVisible]=useState(()=>!document.hidden)
 const [hovered,setHovered]=useState(false)
 const [autoCalls,setAutoCalls]=useState(0)
 const lastAutoKind=useRef('idle')
 const activeSection=useRef(section)
 const pauseAutoUntil=useRef(0)
 const seq=useRef(0)
 useEffect(()=>{
  if(signal.kind==='idle')return undefined
  const timer=window.setTimeout(()=>setSignal(current=>
   current.id===signal.id?{...current,kind:'idle'}:current),2100)
  return()=>window.clearTimeout(timer)
 },[signal])
 useEffect(()=>{
  const screen=window.matchMedia?.('(max-width: 767px)')
  const syncScreen=()=>setMobileScreen(Boolean(screen?.matches))
  syncScreen()
  screen?.addEventListener?.('change',syncScreen)
  return()=>screen?.removeEventListener?.('change',syncScreen)
 },[])
 useEffect(()=>{
  const motion=window.matchMedia?.('(prefers-reduced-motion: reduce)')
  const syncMotion=()=>setReducedMotion(Boolean(motion?.matches))
  const syncVisibility=()=>setVisible(!document.hidden)
  syncMotion()
  syncVisibility()
  motion?.addEventListener?.('change',syncMotion)
  document.addEventListener('visibilitychange',syncVisibility)
  return()=>{
   motion?.removeEventListener?.('change',syncMotion)
   document.removeEventListener('visibilitychange',syncVisibility)
  }
 },[])
 useEffect(()=>{
  try{window.localStorage.setItem(REF_AUTO_STORAGE_KEY,autoEnabled?'on':'off')}catch{}
 },[autoEnabled])
 useEffect(()=>{activeSection.current=section},[section])
 useEffect(()=>{
  if(!canAutoPerform({enabled:autoEnabled,reducedMotion,visible,minimized,expanded,hovered}))return undefined
  if(signal.kind!=='idle')return undefined
  const delay=nextRefDelay({
   hasPerformed:autoCalls>0,manualPauseUntil:pauseAutoUntil.current,now:Date.now(),
  })
  const timer=window.setTimeout(()=>{
   // Visibility and motion can change between timer scheduling and delivery.
   if(document.hidden||window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)return
   const kind=nextRefCall(activeSection.current,lastAutoKind.current)
   lastAutoKind.current=kind
   seq.current+=1
   setSignal({kind,id:seq.current,origin:'auto'})
   setAutoCalls(n=>n+1)
   // No sound. Theatrical whistle cues are visual unless the user clicks.
  },delay)
  return()=>window.clearTimeout(timer)
 },[autoEnabled,reducedMotion,visible,minimized,expanded,hovered,signal.kind,autoCalls])
 useEffect(()=>{
  if(page==='News & Insights'){setSection('news');return undefined}
  let raf=null
  const evaluate=()=>{
   raf=null
   const center=window.innerHeight*.52
   let selected='welcome',distance=Infinity
   for(const entry of sideline){
    const el=document.querySelector(entry.selector)
    if(!el)continue
    const rect=el.getBoundingClientRect()
    // Nearest visible section to a comfortable viewport guide point.
    const gap=rect.top>center?rect.top-center:rect.bottom<center?center-rect.bottom:0
    if(gap<distance){distance=gap;selected=entry.key}
   }
   setSection(current=>current===selected?current:selected)
  }
  const onScroll=()=>{
   if(raf===null)raf=window.requestAnimationFrame(evaluate)
  }
  evaluate()
  window.addEventListener('scroll',onScroll,{passive:true})
  window.addEventListener('resize',onScroll)
  return()=>{
   if(raf!==null)window.cancelAnimationFrame(raf)
   window.removeEventListener('scroll',onScroll)
   window.removeEventListener('resize',onScroll)
  }
 },[page])
 const perform=kind=>{
  pauseAutoUntil.current=Date.now()+REF_MANUAL_PAUSE_MS
  seq.current+=1
  setSignal({kind,id:seq.current,origin:'manual'})
  if(kind==='whistle')shortWhistle()
 }
 const current=sideline.find(x=>x.key===section)||sideline[0]
 // On small phones the mascot belongs to a real editorial sideline, not on
 // top of a news link or betting card. Opening controls restores its fixed
 // placement so the menu remains usable; other routes keep the original Ref.
 const dockTarget=mobileScreen&&page==='Home'&&!expanded&&(section==='signals'||section==='news')
   ?document.querySelector('[data-ref-safe-stage="'+section+'"]'):null
 const refElement=<aside
  aria-label="The Ref sports companion"
  data-ref-companion
  data-mobile-docked={dockTarget?'true':'false'}
  data-signal={signal.kind}
  data-origin={signal.origin}
  data-auto-enabled={autoEnabled&&!reducedMotion?'true':'false'}
  data-side={left?'left':'right'}
  data-section={section}
  data-minimized={minimized?'true':'false'}
  data-expanded={expanded?'true':'false'}
  style={{'--ref-desktop-dock':current.bottom+'vh'}}
  className={`zenith-ref-companion pointer-events-none fixed z-[38] ${left?'left-2 md:left-5':'right-2 md:right-5'} flex max-w-[calc(100vw-16px)] flex-col items-end gap-2`}
 >
  {expanded&&!minimized&&<div role="group" aria-label="The Ref quick calls"
   className="zenith-ref-control-panel pointer-events-auto w-[min(280px,calc(100vw-28px))] overflow-y-auto rounded-2xl border-[2px] border-[#173E52] bg-[#FFF5E4] p-3 text-[#173E52] shadow-[5px_5px_0_#46CDD2]">
   <div className="flex items-center justify-between gap-2">
    <b className="text-sm font-black uppercase tracking-wider">The Ref · Sideline</b>
    <button type="button" aria-label="Close The Ref calls" onClick={()=>setExpanded(false)}
     className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#B6D4CE] bg-white"><X size={17}/></button>
   </div>
   <p className="mt-1 text-[11px] font-semibold leading-5 text-[#526A73]">
    A sports companion who moves through the site. The signals below are just for fun.
   </p>
   <button type="button" role="switch" aria-label="Surprise Ref calls" aria-checked={autoEnabled}
    onClick={()=>{pauseAutoUntil.current=Date.now()+REF_MANUAL_PAUSE_MS;setAutoEnabled(enabled=>!enabled)}}
    className="mt-2 flex min-h-10 w-full items-center justify-between gap-2 rounded-lg border border-[#B3D5D0] bg-white px-3 text-xs font-black text-[#173E52]">
    <span>Surprise calls</span>
    <span className={`rounded-full px-2 py-1 ${autoEnabled?'bg-[#DBF4F0] text-[#276273]':'bg-slate-100 text-slate-600'}`}>{autoEnabled?'ON':'OFF'}</span>
   </button>
   <p className="mt-1 text-[10px] font-semibold text-[#526A73]">Visual fun only · No automatic sound{reducedMotion?' · Paused for reduced motion':''}.</p>
   <div className="mt-2 grid grid-cols-3 gap-1.5">
    <button type="button" aria-label="The Ref throws a flag" onClick={()=>perform('flag')}
     className="min-h-12 rounded-lg border border-[#E2BB75] bg-[#FFF0C6] px-1 text-[11px] font-black"><Flag size={17} className="mx-auto mb-0.5"/>Flag</button>
    <button type="button" aria-label="The Ref signals strike three" onClick={()=>perform('strike')}
     className="min-h-12 rounded-lg border border-[#AED5D1] bg-[#DBF4F0] px-1 text-[11px] font-black"><Hand size={17} className="mx-auto mb-0.5"/>Strikeout</button>
    <button type="button" aria-label="The Ref blows a whistle" onClick={()=>perform('whistle')}
     className="min-h-12 rounded-lg border border-[#E7B7A6] bg-[#FFE4D9] px-1 text-[11px] font-black"><Volume2 size={17} className="mx-auto mb-0.5"/>Whistle</button>
   </div>
   <div className="mt-2 grid grid-cols-2 gap-1.5">
    <button type="button" onClick={onOpenAsk} className="flex min-h-11 items-center justify-center gap-1 rounded-lg bg-[#FF7766] px-2 text-xs font-black"><MessageCircle size={15}/> Ask The Ref</button>
    <button type="button" onClick={onOpenBrain} className="flex min-h-11 items-center justify-center gap-1 rounded-lg border border-[#173E52] bg-white px-2 text-xs font-black"><BarChart3 size={15}/> Brain Record</button>
   </div>
   <div className="mt-1.5 flex gap-1.5">
    <button type="button" aria-label={`Move Ref to the ${left?'right':'left'}`} onClick={()=>{setLeft(!left);setExpanded(false)}} className="flex min-h-10 flex-1 items-center justify-center gap-1 rounded-lg border border-[#B3D5D0] bg-white px-2 text-[11px] font-black text-[#276273]">
     <ArrowLeftRight size={14}/> Move {left?'right':'left'}
    </button>
    <button type="button" onClick={()=>{setMinimized(true);setExpanded(false)}} className="flex min-h-10 flex-1 items-center justify-center gap-1 rounded-lg border border-[#B3D5D0] bg-white px-2 text-[11px] font-black text-[#276273]">
     <Minimize2 size={14}/> Shrink
    </button>
   </div>
  </div>}
  {minimized?(
   <button type="button" aria-label="Expand The Ref mascot" onClick={()=>setMinimized(false)}
    className="pointer-events-auto flex min-h-11 items-center gap-2 rounded-full border-2 border-[#173E52] bg-[#FF7766] px-3 text-xs font-black text-[#173E52] shadow-[3px_3px_0_#173E52]">
    <Maximize2 size={15}/> THE REF
   </button>
  ):(
   <div className="pointer-events-auto flex items-end gap-2">
    <div className="zenith-ref-speech max-w-[118px] rounded-xl border-2 border-[#173E52] bg-[#FFF5E4] px-2.5 py-2 text-center text-[11px] font-black leading-4 text-[#173E52] shadow-[2px_3px_0_#173E5220]">
     <span aria-live={signal.origin==='auto'?'off':'polite'}>{callText[signal.kind]}</span>
     <span className="mt-1 block border-t border-[#E2CDB0] pt-1 text-[9px] font-extrabold tracking-wider text-[#AB5343]">{current.name}</span>
    </div>
    <button type="button" aria-label="Open The Ref animated sports companion" aria-expanded={expanded}
     onClick={()=>{pauseAutoUntil.current=Date.now()+REF_MANUAL_PAUSE_MS;setExpanded(x=>!x)}}
     onPointerEnter={event=>{if(event.pointerType==='mouse')setHovered(true)}}
     onPointerLeave={event=>{if(event.pointerType==='mouse')setHovered(false)}}
     className={`zenith-ref-mascot zenith-ref--${signal.kind} relative block h-[142px] w-[113px] shrink-0 cursor-pointer transition-transform hover:scale-[1.035] md:h-[190px] md:w-[150px] 2xl:h-[213px] 2xl:w-[170px]`}>
     <RefFigure/>
    </button>
   </div>
  )}
 </aside>
 return dockTarget?createPortal(refElement,dockTarget):refElement
}
