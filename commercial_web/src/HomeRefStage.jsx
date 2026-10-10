import React from 'react'

// Dedicated in-page mobile sidelines for the ORIGINAL animated Ref.
// The same component is portalled here when the visitor enters the section.
const editions={
 signals:{
  title:'A call on every play.',
  subtitle:'Flags, strikeouts and silent whistle moves.',
  border:'border-[#E5BE81]',paper:'bg-[#FFF0D8]',stripe:'bg-[#FF7766]',
 },
 news:{
  title:'The newsroom has a Ref.',
  subtitle:'Just-for-fun calls as you read.',
  border:'border-[#92CFCB]',paper:'bg-[#E7F6F1]',stripe:'bg-[#46CDD2]',
 },
 picks:{
  title:'Your picks. Your proof.',
  subtitle:'Pool, fantasy and verified results.',
  border:'border-[#B7C8A6]',paper:'bg-[#F0F5DF]',stripe:'bg-[#9BC7A3]',
 },
 learning:{
  title:'Proof over promises.',
  subtitle:'See what Zenith tracks, grades and learns.',
  border:'border-[#E5C09C]',paper:'bg-[#FFF0DC]',stripe:'bg-[#FFD36A]',
 },
}

export default function HomeRefStage({zone='signals'}){
 const edition=editions[zone]||editions.signals
 return <div data-ref-safe-stage={zone}
  className={'relative isolate mx-0 my-3 min-h-[158px] overflow-visible rounded-[20px] border-2 px-3 py-4 pr-[128px] md:hidden '+edition.border+' '+edition.paper+' text-[#173E52]'}>
  <div aria-hidden="true" className={'absolute bottom-0 left-0 top-0 w-[5px] rounded-l-[18px] '+edition.stripe}/>
  <div className="max-w-[190px]">
   <div className="text-[9px] font-black uppercase tracking-[.15em] text-[#0E7180]">
    The Ref's sideline
   </div>
   <p className="mt-2 text-base font-black leading-[1.13] tracking-tight sm:text-lg">
    {edition.title}
   </p>
   <p className="mt-2 text-[10px] font-semibold leading-[1.5] text-[#536D77]">
    {edition.subtitle}
   </p>
  </div>
  <div aria-hidden="true" className={'absolute bottom-3 left-3 h-[2px] w-12 '+edition.stripe}/>
 </div>
}
