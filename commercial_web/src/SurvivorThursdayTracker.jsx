import React, {useEffect,useState} from 'react'
import {ChevronRight,ShieldAlert,Users} from 'lucide-react'

const human = code => String(code||'').replaceAll('_',' ').toLowerCase().replace(/\b\w/g,x=>x.toUpperCase())

export default function SurvivorThursdayTracker({getAccessToken}) {
  const [summary,setSummary]=useState(null)
  const [refresh,setRefresh]=useState(0)
  const [sourceName,setSourceName]=useState('')
  const [rawList,setRawList]=useState('')
  const [attested,setAttested]=useState(false)
  const [confirmed,setConfirmed]=useState(false)
  const [preview,setPreview]=useState(null)
  const [busy,setBusy]=useState(false)
  const [message,setMessage]=useState('')
  const [error,setError]=useState('')

  useEffect(()=>{
    let cancelled=false
    const load=async()=>{
      try{
        const token=await getAccessToken()
        if(!token){if(!cancelled)setSummary(null);return}
        const res=await fetch('/api/survivor/thursday/summary?ts='+Date.now(),{
          cache:'no-store',headers:{Authorization:`Bearer ${token}`},
        })
        const data=await res.json()
        if(!cancelled){
          if(res.status===401||res.status===403){setSummary(null);return}
          setSummary(data)
        }
      }catch{if(!cancelled)setSummary({status:'SOURCE_UNAVAILABLE',can_manage:false})}
    }
    load()
    return()=>{cancelled=true}
  },[getAccessToken,refresh])

  const post=async(route,body)=>{
    const token=await getAccessToken()
    if(!token)throw Error('Sign in before reviewing this private pool list.')
    const response=await fetch('/api/survivor/thursday/'+route,{
      method:'POST',headers:{'content-type':'application/json',Authorization:`Bearer ${token}`},
      body:JSON.stringify(body),
    })
    const result=await response.json()
    if(!response.ok)throw Error(result.message||'The reported entry list could not be processed.')
    return result
  }

  const review=async()=>{
    if(busy||!sourceName.trim()||!rawList.trim()||!attested)return
    setBusy(true);setError('');setMessage('');setPreview(null);setConfirmed(false)
    try{
      const result=await post('preview',{
        source_name:sourceName.trim(),reported_text:rawList,attested_dallas_only:true,
      })
      setPreview(result)
      setMessage('Preview only — the official pool has not been updated.')
    }catch(e){setError(e.message||'Preview failed.')}
    finally{setBusy(false)}
  }

  const save=async()=>{
    if(busy||!preview?.preview_token||!confirmed)return
    setBusy(true);setError('');setMessage('')
    try{
      const result=await post('confirm',{
        preview_token:preview.preview_token,attested_reported_only:true,
      })
      setMessage(result.status==='ALREADY_SAVED'
        ? 'This reported list was already saved. Official entries have not changed.'
        : 'Reported list saved separately with a source checksum. Official entries and your pick have not changed.')
      setPreview(null);setConfirmed(false);setRawList('');setAttested(false)
      setRefresh(n=>n+1)
    }catch(e){setError(e.message||'Evidence save could not be verified.');setPreview(null);setConfirmed(false)}
    finally{setBusy(false)}
  }

  if(!summary)return null
  const available=Number(summary.list_imported_count||0)
  const saved=available>0
  return (
    <section aria-label="Thursday Dallas Survivor elimination tracker"
      className="overflow-hidden rounded-[24px] border border-[#D9C7B7] bg-[#FFF8ED] p-4 shadow-soft md:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] font-black uppercase tracking-[.16em] text-[#B65A4A]">POOL WATCH · THURSDAY RESULT</p>
          <h2 className="mt-1 text-lg font-black tracking-tight text-[#173E52] md:text-xl">Dallas elimination tracker</h2>
          <p className="mt-1 text-[11px] font-semibold leading-5 text-[#60717A]">Tampa Bay 24 · Dallas 16 · Reported losses, not certified standings.</p>
        </div>
        <span className="rounded-lg border border-[#ECD3A0] bg-white px-2.5 py-1.5 text-[10px] font-black text-[#945A28]">
          {saved?'LIST RECEIVED · UNOFFICIAL':'AWAITING REPORTED LIST'}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-1.5 rounded-xl bg-[#173E52] p-1.5 text-center text-white">
        {[
          ['147','Reported losses'],
          [available||'0','Rows saved'],
          [summary.official_remaining_count??'—','Official left'],
        ].map(([value,label])=>(
          <div key={label} className="min-w-0 rounded-lg bg-[#254B5D] p-2">
            <div className="text-xl font-black tabular-nums text-[#FFF5E4]">{value}</div>
            <div className="mt-0.5 text-[9px] font-bold leading-tight text-[#CFE7E7]">{label}</div>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[11px] font-semibold leading-[1.55] text-slate-700">
        <ShieldAlert size={13} className="mr-1 inline text-amber-700" />
        {saved
          ? `${summary.prior_week_matched??'—'} exact prior-week matches · ${summary.prior_week_needs_review??'—'} needing name review · official sheet Week ${summary.official_week??'—'}.`
          : `The 147 figure is from your earlier report, not a recovered 147-row source. Latest official sheet: Week ${summary.official_week??'—'}.`}
        {' '}No Week 5 entries are certified eliminated here and no remaining-pool count is inferred.
      </p>
      {summary.status==='REPORTED_EVIDENCE_REVIEW_REQUIRED' &&
        <p className="mt-2 text-xs font-semibold text-red-700">Private reported-list evidence needs repair; original pool data was not modified.</p>}
      {summary.can_manage && (
        <details className="mt-3 rounded-xl border border-[#E1D3C5] bg-white p-3">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 text-xs font-black text-[#173E52]">
            <span><Users size={14} className="mr-1 inline"/>Review the reported Dallas entry list (manager only)</span>
            <ChevronRight size={16} className="shrink-0" />
          </summary>
          <p className="mt-3 text-[11px] font-medium leading-5 text-slate-600">
            Paste the separate numbered tickets, one per line (e.g. JANE SMITH 01 COWBOYS). This saves reported evidence only. Use the separate official pool importer for the organizer's Week 5 sheet.
          </p>
          <label className="mt-3 block text-[11px] font-black text-slate-700">
            Evidence source
            <input aria-label="Dallas list source" value={sourceName}
              onChange={e=>{setSourceName(e.target.value);setPreview(null);setConfirmed(false)}}
              placeholder="e.g. Organizer message Oct 10"
              className="mt-1 block w-full min-w-0 rounded-lg border border-slate-300 px-3 py-2 text-xs font-medium" />
          </label>
          <label className="mt-3 block text-[11px] font-black text-slate-700">
            Numbered Dallas entries (not official standings)
            <textarea aria-label="Reported Dallas entry list" rows={5} value={rawList}
              onChange={e=>{setRawList(e.target.value);setPreview(null);setConfirmed(false)}}
              placeholder={'JANE SMITH 01 COWBOYS\nJANE SMITH 02 DAL'}
              className="mt-1 block w-full min-w-0 resize-y rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs font-medium" />
          </label>
          <label className="mt-3 flex items-start gap-2 text-[11px] font-semibold leading-5 text-slate-700">
            <input type="checkbox" className="mt-1" checked={attested}
              onChange={e=>{setAttested(e.target.checked);setPreview(null);setConfirmed(false)}}/>
            Each ticket above was reported as a Dallas Week 5 pick; this is not an official pool document.
          </label>
          <button type="button" onClick={review} disabled={busy||!attested||!rawList.trim()||!sourceName.trim()}
            className="mt-3 rounded-lg bg-[#173E52] px-4 py-2 text-xs font-black text-white disabled:opacity-40">
            {busy?'Checking…':'Preview reported list'}
          </button>
          {preview && (
            <div className="mt-3 rounded-xl border border-[#EADCB9] bg-[#FFF8ED] p-3 text-xs text-slate-800">
              <div className="font-black">{preview.counts?.uploaded} separate tickets · {preview.counts?.prior_active_exact} exact prior matches · {preview.counts?.prior_manual_review} review · {preview.counts?.not_found} unmatched</div>
              {!preview.count_matches_claim && <p className="mt-1 font-semibold text-amber-800">Uploaded ticket count does not equal the reported 147. Saving it will not make the original claim verified.</p>}
              {!!preview.review_rows?.length && <div className="mt-2 max-h-36 overflow-y-auto border-t border-slate-200 pt-2">
                {preview.review_rows.map((item,i)=><p key={item.entry_name+':'+i} className="py-1">
                  <b>{item.entry_name}</b> — {human(item.match_status)}{item.possible_prior_name?` (possible source text: ${item.possible_prior_name})`:''}
                </p>)}
              </div>}
              <label className="mt-3 flex items-start gap-2 font-semibold leading-5">
                <input type="checkbox" className="mt-1" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)} />
                Save this as unverified Thursday evidence only, not as certified eliminations or an official pool import.
              </label>
              <button type="button" onClick={save} disabled={busy||!confirmed}
                className="mt-3 rounded-lg bg-[#173E52] px-4 py-2 font-black text-white disabled:opacity-40">
                {busy?'Saving…':'Save reported evidence'}
              </button>
            </div>
          )}
          {error&&<p role="alert" className="mt-2 text-xs font-bold text-red-700">{error}</p>}
          {message&&<p role="status" className="mt-2 text-xs font-bold text-blue-800">{message}</p>}
        </details>
      )}
    </section>
  )
}
