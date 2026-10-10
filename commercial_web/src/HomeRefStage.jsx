import React from 'react'

// Reserved, deliberately in-page mobile sideline. The original full-body
// ZenithRefCompanion is portalled here when a visitor reads this section.
// No duplicated mascot, data collector or betting recommendation.
export default function HomeRefStage({zone='signals'}){
 const news=zone==='news'
 return <div data-ref-safe-stage={zone}
  className={'relative isolate mx-0 my-3 min-h-[158px] overflow-visible rounded-[20px] border-2 px-3 py-4 pr-[128px] md:hidden '+(
    news?'border-[#92CFCB] bg-[#E7F6F1] text-[#173E52]':
         'border-[#E5BE81] bg-[#FFF0D8] text-[#173E52]')}>
  <div aria-hidden="true" className={'absolute bottom-0 left-0 top-0 w-[5px] rounded-l-[18px] '+(news?'bg-[#46CDD2]':'bg-[#FF7766]')}/>
  <div className="max-w-[190px]">
   <div className="text-[9px] font-black uppercase tracking-[.15em] text-[#0E7180]">
    The Ref's sideline
   </div>
   <p className="mt-2 text-base font-black leading-[1.13] tracking-tight sm:text-lg">
    {news?'The newsroom has a Ref.':'A call on every play.'}
   </p>
   <p className="mt-2 text-[10px] font-semibold leading-[1.5] text-[#536D77]">
    {news?'Just-for-fun calls as you read.':'Flags, strikeouts and silent whistle moves.'}
   </p>
  </div>
  <div aria-hidden="true" className="absolute bottom-3 left-3 h-[2px] w-12 bg-[#FF7766]"/>
 </div>
}
