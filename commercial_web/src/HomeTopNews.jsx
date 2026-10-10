import React,{useMemo} from 'react'
import {ArrowRight,Newspaper} from 'lucide-react'
import useSportsNews from './useSportsNews.js'
import NewsStoryCard from './NewsStoryCard.jsx'
import {selectHomeTopStories} from '../news_curation.js'

export default function HomeTopNews({onNavigate}){
 const feed=useSportsNews()
 const top=useMemo(()=>feed.status==='READY'
  ?selectHomeTopStories(feed.stories,Date.now(),4):[],[feed])
 return <section aria-label="Home sports news" className="min-w-0">
   <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
     <div>
       <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[.15em] text-amber-300">
         <Newspaper size={15} aria-hidden="true"/> Newsroom · top stories
       </div>
       <h2 className="mt-1 text-xl font-black tracking-tight text-white md:text-2xl">Top sports news</h2>
       <p className="mt-1 text-xs font-medium text-slate-400">
         What changed that could matter · top headlines from across sports
       </p>
     </div>
     <button type="button" onClick={()=>onNavigate('News & Insights')}
       className="flex min-h-10 items-center gap-1.5 rounded-xl border border-amber-300/25 bg-amber-300/10 px-3 py-2 text-xs font-black text-amber-200 transition hover:bg-amber-300/20">
       All sports news <ArrowRight size={15} aria-hidden="true"/>
     </button>
   </div>
   {top.length>0?
     <div className="flex snap-x snap-mandatory gap-3 overflow-x-auto pb-2 xl:grid xl:grid-cols-4 xl:overflow-visible">
       {top.map(story=><div className="w-[min(82vw,320px)] shrink-0 snap-start xl:w-auto" key={story.id}>
         <NewsStoryCard story={story} theme="dark"/>
       </div>)}
     </div>:
     <div role="status" className="rounded-[22px] border border-[#25415D] bg-[#0E2740] p-5 text-xs font-semibold leading-5 text-slate-300">
       {feed.loading?'Checking original sports headlines…':
        feed.status==='DATA_SOURCE_FAILURE'?'NEWS SOURCE FAILURE — the news feed could not be verified; this is not “no news.”':
        feed.status==='SOURCE_STALE'?'NEWS SOURCE STALE — the latest article collection is too old to headline as current.':
        feed.status==='NO_QUALIFIED_ARTICLES'?'No source-linked news articles qualified in the current feed.':
        'No newly published top headlines in the last 48 hours. Open News for older source-linked stories.'}
     </div>}
   <p className="mt-2 text-[10px] leading-4 text-[#90A6BD]">
     Headlines are attributed reporting, not verified injuries, final lineups or betting-model signals. Select a headline to read the original article.
   </p>
 </section>
}
