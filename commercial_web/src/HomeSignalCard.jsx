import React from 'react'
import {Gauge,ShieldCheck,Target,Trophy,Zap,ArrowUpRight} from 'lucide-react'

// Visual treatment only: status and counts come unchanged from the existing
// source-governed HomeDecisionPanel, not fabricated design metrics.
const visual={
 'Best Bets':{Icon:Target,accent:'#FA796B',paper:'#FFF0E8',label:'GAME LINES'},
 Props:{Icon:Gauge,accent:'#44CACD',paper:'#E8F7F2',label:'PLAYER RESEARCH'},
 PrizePicks:{Icon:Zap,accent:'#EFC65A',paper:'#FFF5D9',label:'PICK-EM'},
 Parlays:{Icon:Trophy,accent:'#B99BE0',paper:'#F3EDFA',label:'MULTI-LEG'},
 Survivor:{Icon:ShieldCheck,accent:'#9BCD9F',paper:'#EAF5E5',label:'POOL STRATEGY'},
}
export default function HomeSignalCard({card,index,onNavigate}){
 const profile=visual[card.label]||visual.Props
 const Icon=profile.Icon
 return (
  <button type="button" data-intelligence-card={card.label}
   onClick={()=>onNavigate(card.route)}
   style={{'--signal-ink':'#173E52','--signal-accent':profile.accent,'--signal-paper':profile.paper}}
   className="zenith-home-signal-card group relative flex min-w-[270px] snap-start flex-col overflow-hidden rounded-[18px] border-2 border-[#D8CBBE] p-4 text-left text-[#173E52] transition hover:-translate-y-1 hover:border-[#173E52] xl:min-w-0">
   <div className="zenith-home-signal-topline" aria-hidden="true"/>
   <div className="flex items-start justify-between gap-2">
    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#173E52] text-[#173E52] shadow-[2px_2px_0_#173E52]" style={{backgroundColor:profile.accent}}>
     <Icon size={21} strokeWidth={2.4} aria-hidden="true"/>
    </span>
    <span className="max-w-[145px] rounded-md border border-[#D8C3AE] bg-[#FFFDF7] px-2 py-1 text-right text-[9px] font-black uppercase tracking-[.05em] text-[#425764]">{card.status}</span>
   </div>
   <div className="mt-3 flex items-baseline gap-2">
    <span className="text-[10px] font-black uppercase tracking-[.14em] text-[#78665B]">{profile.label}</span>
    <span className="ml-auto text-[10px] font-black tracking-[.1em] text-[#A99382]">/ 0{index+1}</span>
   </div>
   {card.metric!==null&&card.metric!==undefined&&(
    <div className="mt-2 flex items-baseline gap-2">
     <span className="zenith-home-signal-metric text-[clamp(1.65rem,2vw,2.4rem)] font-black leading-none tabular-nums text-[#173E52]">{card.metric}</span>
     <span className="max-w-[132px] text-[10px] font-bold leading-[1.2] text-[#526A73]">{card.metricLabel}</span>
    </div>
   )}
   <h3 className="mt-2 text-[15px] font-black leading-5 tracking-[-.012em] text-[#173E52]">{card.title}</h3>
   <p className="mt-2 text-xs font-semibold leading-[1.45] text-[#536B73]">{card.detail}</p>
   <div className="mt-auto flex items-center justify-between gap-3 border-t border-[#DFD2C5] pt-3 text-[11px] font-black uppercase tracking-[.08em] text-[#173E52]">
    <span>Open {card.label}</span>
    <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#173E52] bg-[#173E52] text-[#FFF5E4] transition group-hover:bg-[#FF7766] group-hover:text-[#173E52]">
     <ArrowUpRight size={16}/>
    </span>
   </div>
  </button>
 )
}
