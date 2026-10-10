import React from 'react'
import {
  Activity,ArrowLeftRight,ArrowUpRight,Bandage,ClipboardList,FileText,
  Megaphone,Newspaper,TrendingUp,
} from 'lucide-react'

const categories={
 INJURY:{
  label:'Injury',Icon:Bandage,
  dark:'border-rose-400/25 bg-rose-400/10 text-rose-200',
  light:'border-rose-200 bg-rose-50 text-rose-700',
  accent:'bg-[#FF6878]',
  meaning:'Reported availability could affect a lineup or matchup; confirm official status.',
 },
 RECAP:{
  label:'Recap',Icon:Newspaper,
  dark:'border-amber-400/25 bg-amber-400/10 text-amber-200',
  light:'border-amber-200 bg-amber-50 text-amber-800',
  accent:'bg-[#F7BF59]',
  meaning:'Final-game context for the next matchup; this is not a new model pick.',
 },
 FANTASY:{
  label:'Fantasy',Icon:ClipboardList,
  dark:'border-cyan-300/30 bg-cyan-400/10 text-cyan-200',
  light:'border-cyan-200 bg-cyan-50 text-cyan-900',
  accent:'bg-[#35D5DE]',
  meaning:'Fantasy reporting may inform roster research, not a guaranteed starter decision.',
 },
 LINEUP:{
  label:'Lineup',Icon:FileText,
  dark:'border-emerald-300/25 bg-emerald-400/10 text-emerald-200',
  light:'border-emerald-200 bg-emerald-50 text-emerald-800',
  accent:'bg-[#63D9AA]',
  meaning:'A reported starter or role can change matchup context; verify before use.',
 },
 TRANSACTION:{
  label:'Roster move',Icon:ArrowLeftRight,
  dark:'border-violet-300/25 bg-violet-400/10 text-violet-200',
  light:'border-violet-200 bg-violet-50 text-violet-800',
  accent:'bg-[#B7A0FF]',
  meaning:'Roster movement could change usage or depth; review the actual team status.',
 },
 MARKET:{
  label:'Odds news',Icon:TrendingUp,
  dark:'border-sky-300/25 bg-sky-400/10 text-sky-200',
  light:'border-sky-200 bg-sky-50 text-blue-800',
  accent:'bg-[#54C5FF]',
  meaning:'An article about odds is not an executable current bookmaker quote.',
 },
 NEWS:{
  label:'Headline',Icon:Megaphone,
  dark:'border-blue-300/25 bg-blue-400/10 text-blue-200',
  light:'border-blue-200 bg-blue-50 text-blue-800',
  accent:'bg-[#5596FF]',
  meaning:'Attributed reporting; open the original article for its full context.',
 },
}
const dateET=value=>{
 const d=Date.parse(value||'')
 if(!Number.isFinite(d))return 'Publication time unverified'
 return new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
  timeZone:'America/New_York',timeZoneName:'short',
 }).format(d)
}

export function NewsCategorySign({category='NEWS',dark=false,compact=false}){
 const style=categories[category]||categories.NEWS
 const Icon=style.Icon
 return <span data-category-sign={category}
  className={'inline-flex shrink-0 items-center gap-1.5 rounded-lg border font-black uppercase tracking-[.08em] '+
   (compact?'px-2 py-1 text-[10px] ':'px-2.5 py-1.5 text-[11px] ')+
   (dark?style.dark:style.light)}>
    <Icon size={compact?13:15} aria-hidden="true" strokeWidth={2.5}/>
    <span>{style.label}</span>
 </span>
}

export default function NewsStoryCard({story,theme='light',featured=false}){
 const dark=theme==='dark'
 const style=categories[story.category]||categories.NEWS
 const snippet=story.summary&&story.summary!==story.title?story.summary:null
 return <article data-news-card={story.id} data-news-sport={story.sport}
  data-news-category={story.category}
  className={'group relative h-full min-w-0 overflow-hidden rounded-[21px] border transition hover:-translate-y-0.5 '+
   (dark?'border-[#284967] bg-gradient-to-br from-[#132F4B] to-[#0B2036] text-white hover:border-sky-400/50':
     'border-slate-200 bg-white text-slate-950 shadow-[0_10px_26px_rgba(21,35,55,.05)] hover:border-sky-300 hover:shadow-lg')}>
  <div aria-hidden="true" className={'absolute inset-x-0 top-0 h-[3px] '+style.accent}/>
  <a href={story.url} target="_blank" rel="noopener noreferrer" title={'Read original '+story.source+' article'}
   aria-label={'Read '+story.title+' at '+story.source}
   className="flex h-full min-h-[186px] flex-col p-4 focus-visible:outline-offset-[-3px] md:p-5">
   <div className="flex flex-wrap items-center justify-between gap-2">
    <span className={'rounded-md px-2 py-1 text-[10px] font-black tracking-[.13em] '+
      (dark?'bg-black/30 text-sky-200':'bg-slate-950 text-white')}>{story.sport}</span>
    <NewsCategorySign category={story.category} dark={dark} compact/>
   </div>
   <h3 className={'mt-3 line-clamp-3 font-black leading-6 tracking-tight '+
    (featured?'text-lg md:text-xl':'text-[15px] md:text-base')+
    (dark?' text-white':' text-slate-950')}>
     {story.title}
   </h3>
   {featured&&snippet&&<p className={'mt-2 line-clamp-3 text-xs leading-5 '+(dark?'text-slate-300':'text-slate-600')}>{snippet}</p>}
   {!featured&&dark&&<p className="mt-2 line-clamp-2 text-[11px] font-medium leading-[1.55] text-[#B8D0E5]">{style.meaning}</p>}
   {!featured&&!dark&&snippet&&<p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-600">{snippet}</p>}
   <div className={'mt-auto flex min-w-0 items-center justify-between gap-2 border-t pt-3 text-[10px] font-bold '+
      (dark?'border-white/10 text-slate-400':'border-slate-100 text-slate-500')}>
     <div className="min-w-0">
      <span className="block truncate">{story.source} · {dateET(story.publishedAt)}</span>
      {featured&&<span className="mt-1 block font-semibold">Attributed news, not a confirmed model input</span>}
     </div>
     <ArrowUpRight size={16} className={'shrink-0 transition group-hover:-translate-y-0.5 '+(dark?'text-sky-300':'text-blue-700')} aria-hidden="true"/>
   </div>
  </a>
 </article>
}

export const NEWS_CATEGORY_ICONS=Object.keys(categories)
