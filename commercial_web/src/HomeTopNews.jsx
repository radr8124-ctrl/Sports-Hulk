import React,{useMemo} from 'react'
import {ArrowRight,Newspaper} from 'lucide-react'
import useSportsNews from './useSportsNews.js'
import NewsStoryCard from './NewsStoryCard.jsx'
import HomeRefStage from './HomeRefStage.jsx'
import {selectHomeTopStories} from '../news_curation.js'

// One featured, source-attributed article and three compact briefs.
// These are editorial headlines, NEVER verified injuries or model picks.
export default function HomeTopNews({onNavigate}){
 const feed=useSportsNews()
 const top=useMemo(()=>feed.status==='READY'
  ?selectHomeTopStories(feed.stories,Date.now(),4):[],[feed])
 return <section aria-label="Home sports news" data-home-news-desk
  className="min-w-0 overflow-hidden rounded-[24px] border-2 border-[#173E52] bg-[#FFF8ED] shadow-[5px_5px_0_#173E521C]">
   <div data-news-desk-masthead
    className="relative overflow-hidden bg-[#173E52] px-4 pb-4 pt-6 text-[#FFF5E4] sm:px-6 sm:pb-5 sm:pt-7">
    <div aria-hidden="true" className="absolute inset-x-0 top-0 h-[6px] bg-[linear-gradient(90deg,#FF7766_0%,#FF7766_35%,#FFD36A_35%,#FFD36A_63%,#46CDD2_63%,#46CDD2_100%)]"/>
    <div aria-hidden="true" className="pointer-events-none absolute -right-11 -top-20 h-52 w-52 rounded-full border-[25px] border-[#46CDD2]/10"/>
    <div className="relative flex flex-wrap items-start justify-between gap-3 md:flex-nowrap md:items-end">
     <div className="min-w-0">
      <div className="inline-flex items-center gap-2 text-[10px] font-black uppercase tracking-[.18em] text-[#7DE4E1]">
       <Newspaper size={17} aria-hidden="true" strokeWidth={2.5}/>
       <span>ZENITH NEWS DESK</span>
       <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-[#FF7766]"/>
       <span className="text-[#FFD36A]">THE BRIEFING</span>
      </div>
      <h2 className="mt-1.5 text-[clamp(1.8rem,4.4vw,2.75rem)] font-black leading-[1.08] tracking-[-.045em] text-[#FFF5E4]">
       Top sports news<span className="text-[#FF7766]" aria-hidden="true">.</span>
      </h2>
      <p className="mt-2 max-w-[570px] text-[11px] font-semibold leading-5 text-[#D5E8EC] sm:text-[13px]">
       The stories behind game day. Real sources, clear context, no forced picks.
      </p>
     </div>
     <button type="button" onClick={()=>onNavigate('News & Insights')}
      className="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl border-2 border-[#FFD36A] bg-[#FFD36A] px-3.5 py-2 text-xs font-black text-[#173E52] shadow-[3px_3px_0_#071E2E] transition hover:bg-[#FFE59E]">
      All sports news <ArrowRight size={15} aria-hidden="true"/>
     </button>
    </div>
    <div className="relative mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[#94C3C0]/30 pt-2.5 text-[9px] font-black uppercase tracking-[.14em] text-[#AECBD2] sm:text-[10px]">
     <span>{top.length ? `Lead headline${top.length>1?` + ${top.length-1} quick read${top.length===2?'':'s'}`:''}` : 'Newsroom source status'}</span>
     <span className="text-[#FFD36A]">Source-attributed reporting · Six sports</span>
    </div>
   </div>
   <div className="mx-3 sm:mx-4 md:mx-0"><HomeRefStage zone="news"/></div>
   {top.length>0?
     <div data-news-desk-grid className="grid min-w-0 gap-3 p-3 sm:p-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] lg:gap-4">
      <div data-news-desk-lead className="flex min-w-0 flex-col rounded-[22px] border border-[#E4BC78] bg-[#FFF0CE] p-2 sm:p-3">
       <div className="flex items-center justify-between gap-2 px-1 pb-2.5 text-[10px] font-black uppercase tracking-[.12em] text-[#914A3A]">
        <span>Lead story · 01</span>
        <span className="text-[#71572E]">Front page</span>
       </div>
       <div className="min-h-0 min-w-0 flex-1">
        <NewsStoryCard story={top[0]} theme="light" featured/>
       </div>
      </div>
      {top.length>1&&<div className="min-w-0">
       <div className="flex items-center justify-between gap-2 px-1 pb-2 text-[10px] font-black uppercase tracking-[.12em] text-[#0B6976]">
        <span>Around the leagues</span>
        <span className="lg:hidden">Swipe to read <ArrowRight size={12} className="inline-block" aria-hidden="true"/></span>
       </div>
       <div data-news-desk-supporting role="group" aria-label="More sports news"
        className="flex min-w-0 snap-x snap-mandatory gap-3 overflow-x-auto pb-2 lg:flex-col lg:overflow-visible lg:pb-0">
        {top.slice(1).map(story=>
         <div className="w-[min(76vw,288px)] shrink-0 snap-start lg:w-full" key={story.id}>
          <NewsStoryCard story={story} theme="light" compact/>
         </div>)}
       </div>
      </div>}
     </div>:
     <div role="status" className="m-3 rounded-[18px] border border-[#E1D3BF] bg-white p-5 text-xs font-semibold leading-5 text-[#536B73] sm:m-4">
      {feed.loading?'Checking original sports headlines…':
       feed.status==='DATA_SOURCE_FAILURE'?'NEWS SOURCE FAILURE — the news feed could not be verified; this is not “no news.”':
       feed.status==='SOURCE_STALE'?'NEWS SOURCE STALE — the latest article collection is too old to headline as current.':
       feed.status==='NO_QUALIFIED_ARTICLES'?'No source-linked news articles qualified in the current feed.':
       'No newly published top headlines in the last 48 hours. Open News for older source-linked stories.'}
     </div>}
   <p className="border-t border-[#E7D6C0] px-3 py-3 text-[10px] font-medium leading-4 text-[#536D77] sm:px-4">
    Headlines are attributed reporting, not verified injuries, final lineups or betting-model signals. Open an article to read the original source.
   </p>
 </section>
}
