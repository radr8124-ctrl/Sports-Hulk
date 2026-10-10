import React,{useMemo,useState} from 'react'
import {
 ArrowRight,CalendarClock,ChevronDown,ChevronRight,Newspaper,Search,ShieldCheck,
 Sparkles,
} from 'lucide-react'
import useSportsNews from './useSportsNews.js'
import NewsStoryCard,{NewsCategorySign} from './NewsStoryCard.jsx'
import {
 NEWS_SPORTS,NEWS_SPORT_NAMES,NEWS_CATEGORIES,
 selectHomeTopStories,filterSportsNews,groupSportsNews,
} from '../news_curation.js'

const accents={
 NFL:'bg-[#3B83EA]',NHL:'bg-[#39CBDD]',NBA:'bg-[#FF8077]',
 MLB:'bg-[#E9B95E]',CFB:'bg-[#5EB8AC]',CBB:'bg-[#AF91F6]',
}
const displayET=value=>{
 const ms=Date.parse(value||'')
 return Number.isFinite(ms)?new Intl.DateTimeFormat('en-US',{
  month:'short',day:'numeric',hour:'numeric',minute:'2-digit',
  timeZone:'America/New_York',timeZoneName:'short',
 }).format(ms):'Publication time unavailable'
}

export default function SportsNewsHub(){
 const feed=useSportsNews()
 const [sport,setSport]=useState('ALL')
 const [category,setCategory]=useState('ALL')
 const [sort,setSort]=useState('TOP')
 const [search,setSearch]=useState('')
 const [more,setMore]=useState(12)
 const changeSport=x=>{setSport(x);setMore(12)}
 const changeCategory=x=>{setCategory(x);setMore(12)}
 const changeSearch=x=>{setSearch(x);setMore(12)}
 const visible=useMemo(()=>filterSportsNews(feed.stories,{sport,category,search,sort}),
  [feed.stories,sport,category,search,sort])
 const spotlight=useMemo(()=>{
  if(feed.status!=='READY'||sport!=='ALL'||category!=='ALL'||search.trim()||sort!=='TOP')return []
  return selectHomeTopStories(feed.stories,Date.now(),3)
 },[feed,sport,category,search,sort])
 const spotlightIds=new Set(spotlight.map(s=>s.id))
 const grouped=groupSportsNews(visible.filter(x=>!spotlightIds.has(x.id)))
 const allSportView=sport==='ALL'
 const status=feed.status==='DATA_SOURCE_FAILURE'?'DATA SOURCE FAILURE':
  feed.status==='SOURCE_STALE'?'SOURCE STALE':
  feed.status==='NO_QUALIFIED_ARTICLES'?'NO QUALIFIED ARTICLES':feed.status
 return <div aria-label="Sports Zenith full news hub" className="min-w-0 space-y-5 md:space-y-7">
   <header className="relative overflow-hidden rounded-[26px] border border-[#E6DACA] bg-[#FBF7EF] px-4 py-4 shadow-[0_16px_35px_rgba(13,29,48,.07)] md:px-7 md:py-8">
     <div aria-hidden="true" className="pointer-events-none absolute -right-8 -top-12 h-48 w-48 rounded-full bg-[#42C8EF]/15 blur-2xl"/>
     <div className="relative flex items-start justify-between gap-3">
       <div className="min-w-0">
         <div className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[.18em] text-[#246C9B]">
           <Newspaper size={16} aria-hidden="true"/> The Zenith Newsroom
         </div>
         <h1 className="mt-2 text-[27px] font-black leading-[1.1] tracking-[-.04em] text-[#081F36] md:text-4xl">
           Sports news. <span className="text-[#187AB1]">Made simple.</span>
         </h1>
         <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-600 md:text-sm md:leading-6">
           Top NFL, NHL, NBA, MLB and college articles, organized by sport and topic.
           Tap a story to read its original source.
         </p>
       </div>
       <span aria-hidden="true" className="hidden rounded-2xl border border-[#B8DAEB] bg-[#EAF8FB] p-4 text-[#087CC1] sm:block">
         <Newspaper size={30} strokeWidth={1.7}/>
       </span>
     </div>
     <div className="relative mt-3 flex flex-wrap gap-x-3 gap-y-1.5 border-t border-[#DDDDD4] pt-2.5 text-[11px] font-bold text-[#557087]">
       <span className="inline-flex items-center gap-1.5"><ShieldCheck size={14} className="text-[#168D91]"/> Attributed ESPN reporting</span>
       <span>{feed.loading?'Checking articles…':feed.status==='READY'
          ?feed.stories.length+' source-linked stories':'Source status: '+status}</span>
       {feed.generatedAt&&<span className="inline-flex items-center gap-1.5">
         <CalendarClock size={14}/> Updated {displayET(feed.generatedAt)}
       </span>}
     </div>
   </header>

   <section aria-label="Newsroom filters" className="rounded-[22px] border border-slate-200 bg-white p-3 shadow-[0_5px_20px_rgba(13,29,48,.04)] md:p-4">
     <div className="flex flex-wrap items-center justify-between gap-2">
       <div className="text-xs font-black uppercase tracking-[.11em] text-slate-700">Choose your sport</div>
       <label className="relative block w-full sm:w-[280px]">
         <Search aria-hidden="true" size={16} className="pointer-events-none absolute left-3 top-3.5 text-slate-400"/>
         <input aria-label="Search sports news" type="search" value={search}
           onChange={e=>changeSearch(e.target.value)} placeholder="Team, player, or story"
           className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm font-semibold text-slate-900 outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-100"/>
       </label>
     </div>
     <div role="group" aria-label="Filter news by sport" className="mt-2 flex snap-x gap-2 overflow-x-auto pb-1">
       {[['ALL','All sports'],...NEWS_SPORTS.map(s=>[s,NEWS_SPORT_NAMES[s]])].map(([id,label])=>{
         const count=id==='ALL'?feed.stories.length:feed.stories.filter(x=>x.sport===id).length
         return <button key={id} type="button" aria-pressed={sport===id} onClick={()=>changeSport(id)}
           className={'min-h-9 shrink-0 rounded-xl px-3 text-xs font-black transition '+
            (sport===id?'bg-[#091E32] text-white':'border border-slate-200 bg-slate-50 text-slate-600 hover:border-[#7DC6E8]')}>
           {label} <span className={'ml-1 text-[10px] '+(sport===id?'text-sky-300':'text-slate-400')}>{count}</span>
         </button>
       })}
     </div>
     <div role="group" aria-label="Filter news by story type" className="mt-2 flex snap-x gap-1.5 overflow-x-auto pb-1">
       {NEWS_CATEGORIES.map(c=><button key={c.id} type="button" aria-pressed={category===c.id}
         onClick={()=>changeCategory(c.id)}
         className={'min-h-9 shrink-0 rounded-xl border px-2.5 py-1 text-xs font-black transition '+
          (category===c.id?'border-blue-500 bg-blue-50 text-blue-800':'border-transparent bg-white text-slate-600 hover:bg-slate-50')}>
         {c.id==='ALL'?<span>All stories</span>:<NewsCategorySign category={c.id} compact/>}
       </button>)}
     </div>
     <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2">
       <p className="text-xs font-semibold text-slate-600">
         {feed.status==='READY'?<><b>{visible.length}</b> stor{visible.length===1?'y':'ies'} found</>:
          'News source verification in progress'}
       </p>
       <div role="group" aria-label="Sort sports articles" className="flex items-center gap-1 rounded-xl border border-slate-200 p-1">
         {[['TOP','Top stories'],['LATEST','Newest first']].map(([id,label])=>
           <button key={id} type="button" aria-pressed={sort===id} onClick={()=>{setSort(id);setMore(12)}}
             className={'min-h-8 rounded-lg px-2.5 text-[11px] font-black '+(sort===id?'bg-[#0C2742] text-white':'text-slate-500 hover:bg-slate-50')}>
             {label}
           </button>)}
       </div>
     </div>
   </section>

   {feed.status!=='READY'?
     <section role="status" className="rounded-[22px] border border-amber-200 bg-amber-50 p-5">
       <h2 className="text-sm font-black text-amber-950">{feed.loading?'Loading verified article sources…':status}</h2>
       <p className="mt-2 text-sm leading-6 text-amber-900">
         {feed.status==='DATA_SOURCE_FAILURE'?'The source collection could not be verified. This is a feed problem, not proof that nothing happened.':
          feed.status==='SOURCE_STALE'?'The stored article feed is more than six hours old. Stories are hidden until an updated source arrives.':
          'No properly linked news articles are available in this source collection.'}
       </p>
     </section>:
     <>
       {!!spotlight.length&&<section aria-label="Newsroom top headlines">
         <div className="mb-3 flex items-center gap-2">
           <span className="h-5 w-1 rounded-full bg-[#FC745F]"/>
           <h2 className="text-lg font-black tracking-tight text-slate-950">Top across sports</h2>
           <span className="ml-auto text-[10px] font-bold text-slate-500">From the latest reports</span>
         </div>
         <div className="grid gap-3 md:grid-cols-3">
           {spotlight.map(story=><NewsStoryCard key={story.id} story={story} featured/>)}
         </div>
       </section>}

       <section aria-label="News articles organized by sport">
         <div className="mb-4 flex items-center justify-between gap-2">
           <div>
             <h2 className="text-xl font-black tracking-tight text-slate-950">All sports headlines</h2>
             <p className="mt-1 text-xs font-semibold text-slate-500">
               Grouped by league, with original source links. Videos and promotional items are excluded.
             </p>
           </div>
           <Sparkles size={22} className="shrink-0 text-[#258FB5]" aria-hidden="true"/>
         </div>
         {grouped.length? <div className="space-y-6">
           {grouped.map(group=>{
             const shown=group.stories.slice(0,allSportView?3:more)
             const remaining=group.stories.length-shown.length
             return <section key={group.sport} data-sport-news-section={group.sport}
               aria-label={group.label+' news'} className="rounded-[22px] border border-slate-200 bg-[#FAFCFF] p-3 md:p-4">
               <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                 <div className="flex items-center gap-2.5">
                   <span className={'h-10 w-1.5 rounded-full '+accents[group.sport]}/>
                   <div>
                     <h3 className="text-base font-black text-slate-950">{group.label}</h3>
                     <p className="text-[11px] font-semibold text-slate-500">
                       {group.stories.length} article{group.stories.length===1?'':'s'} in this view
                     </p>
                   </div>
                 </div>
                 {allSportView&&remaining>0&&<button type="button" onClick={()=>changeSport(group.sport)}
                   className="flex min-h-10 items-center gap-1 rounded-xl border border-blue-200 bg-white px-3 text-xs font-black text-blue-700 hover:bg-blue-50">
                   All {group.label} news <ChevronRight size={15}/>
                 </button>}
               </div>
               <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                 {shown.map(story=><NewsStoryCard story={story} key={story.id}/>)}
               </div>
               {!allSportView&&remaining>0&&<div className="mt-3 text-center">
                 <button type="button" onClick={()=>setMore(current=>current+12)}
                   className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-[#88CAE6] bg-white px-4 text-xs font-black text-blue-700 hover:bg-blue-50">
                   Show more {group.label} stories ({remaining} left) <ChevronDown size={15}/>
                 </button>
               </div>}
             </section>
           })}
         </div>:
           <div className="rounded-[22px] border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600">
             No articles match those filters. Try another league, category, or search term.
           </div>}
       </section>
     </>
   }
   <p className="text-xs leading-5 text-slate-500">
     Zenith links to the original reporting rather than reproducing full copyrighted articles.
     News categories organize what was reported; they do not verify player availability, sportsbook prices or a model edge.
   </p>
 </div>
}
