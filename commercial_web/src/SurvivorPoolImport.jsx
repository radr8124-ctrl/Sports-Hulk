import React, { useEffect, useRef, useState } from 'react'
import {FileUp,ChevronDown,ShieldCheck,AlertTriangle} from 'lucide-react'

async function encodeFile(file) {
  if (!file || file.size <= 0 || file.size > 5_000_000) {
    throw new Error('Choose a PDF, XLSX or CSV file smaller than 5 MB.')
  }
  const buffer = new Uint8Array(await file.arrayBuffer())
  let raw = ''
  for (let i = 0; i < buffer.length; i += 8192) {
    raw += String.fromCharCode(...buffer.subarray(i, i + 8192))
  }
  return btoa(raw)
}

export default function SurvivorPoolImport({ getAccessToken, onImported }) {
  const [allowed, setAllowed] = useState(false)
  const [file, setFile] = useState(null)
  const [encoded, setEncoded] = useState(null)
  const [preview, setPreview] = useState(null)
  const [confirmed, setConfirmed] = useState(false)
  const [working, setWorking] = useState(false)
  const [message, setMessage] = useState('')
  const fileRef = useRef(null)
  const detailsRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    const check = async () => {
      try {
        const token = await getAccessToken()
        if (!token) return
        const r = await fetch('/api/survivor/pool-manager', {
          cache: 'no-store', headers: { Authorization: 'Bearer ' + token },
        })
        const body = await r.json()
        if (!cancelled) setAllowed(Boolean(r.ok && body.can_manage))
      } catch { if (!cancelled) setAllowed(false) }
    }
    check()
    return () => { cancelled = true }
  }, [getAccessToken])

  if (!allowed) return null

  const request = async (target, body) => {
    const token = await getAccessToken()
    if (!token) throw new Error('Sign in as the pool manager.')
    const response = await fetch('/api/survivor/pool/' + target, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: 'Bearer ' + token,
      },
      body: JSON.stringify(body),
    })
    const result = await response.json()
    if (!response.ok) throw new Error(result.message || 'The pool file could not be accepted.')
    return result
  }

  const makePreview = async () => {
    if (!file || working) return
    setWorking(true)
    setMessage('')
    setPreview(null)
    setConfirmed(false)
    try {
      const base64 = await encodeFile(file)
      const result = await request('preview', { filename: file.name, base64 })
      setEncoded(base64)
      setPreview(result)
      setMessage('Preview ready. Review the ticket count and weekly selections before replacing the whole-pool sheet.')
    } catch (err) {
      setEncoded(null)
      setMessage(err instanceof Error ? err.message : 'Preview unavailable.')
    } finally { setWorking(false) }
  }

  const commit = async () => {
    if (!preview || !encoded || !confirmed || working) return
    setWorking(true)
    setMessage('')
    try {
      const result = await request('confirm', {
        preview_token: preview.preview_token, base64: encoded,
      })
      setMessage(result.status === 'ALREADY_IMPORTED'
        ? 'This exact official pool file was already imported.'
        : 'Imported ' + result.entry_count + ' pool entries and ' +
          result.weekly_pick_rows + ' weekly picks. Your existing personal entry history was preserved.')
      setPreview(null)
      setEncoded(null)
      setConfirmed(false)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
      onImported?.()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not commit pool import.')
      setPreview(null)
      setEncoded(null)
      setConfirmed(false)
    } finally { setWorking(false) }
  }

  return (
    <section id="knockout-pdf-upload" aria-label="Import full Survivor pool" data-knockout-pdf-manager
      className="scroll-mt-24 min-w-0 overflow-hidden rounded-[22px] border-2 border-[#B9D2D1] bg-[#FFF8ED] p-3 text-[#173E52] sm:p-4">
      <details ref={detailsRef} className="group" data-knockout-pdf-disclosure>
        <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 rounded-xl focus-visible:outline-2 focus-visible:outline-[#FF7766]">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#173E52] text-[#84D8D6]"><FileUp size={21}/></span>
          <span className="min-w-0 flex-1">
            <span className="block text-[10px] font-black uppercase tracking-[.13em] text-[#0E7280]">KNOCKOUT POOL · OFFICIAL FILES</span>
            <span className="mt-0.5 block text-sm font-black">Upload weekly PDF <span className="text-[10px] font-semibold text-[#55717A]">(also CSV/XLSX)</span></span>
          </span>
          <span className="rounded-lg border border-[#D5D9C7] bg-white px-2 py-1 text-[9px] font-black uppercase text-[#5C6F77]">Manager</span>
          <ChevronDown size={17} className="shrink-0 transition group-open:rotate-180"/>
        </summary>
        <div className="mt-3 border-t border-[#DBE4DC] pt-3">
          <p className="flex items-start gap-1.5 text-[11px] font-semibold leading-5 text-[#526D77]">
            <ShieldCheck size={15} className="mt-0.5 shrink-0 text-[#0E7280]"/>
            Choose the organizer’s full weekly knockout-pool PDF from Files. Preview first; nothing is imported or changed until you confirm. Same-name tickets stay separate.
          </p>
          <p className="mt-1 text-[10px] font-medium leading-4 text-[#637984]">Text-searchable PDFs up to 5 MB. Scanned/image-only PDFs may require an original digital copy. A reported loss list is not a complete official pool sheet.</p>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input ref={fileRef} aria-label="Choose official pool file" type="file"
          accept=".pdf,application/pdf,.xlsx,.csv" className="min-w-0 flex-1 text-xs text-[#173E52]"
          onChange={event => {
            const next=event.target.files?.[0] || null
            setFile(next)
            setPreview(null)
            setEncoded(null)
            setConfirmed(false)
            setMessage(next && !/\.(pdf|xlsx|csv)$/i.test(next.name)
              ? 'Choose an official PDF, XLSX, or CSV file.'
              : next && next.size > 5_000_000
                ? 'File exceeds 5 MB. Request the original smaller organizer PDF.' : '')
          }} />
        <button type="button" disabled={!file || working || file.size>5_000_000 || !/\.(pdf|xlsx|csv)$/i.test(file.name)} onClick={makePreview}
          className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white disabled:opacity-40">
          {working ? 'Checking…' : 'Preview pool file'}
        </button>
      </div>

      {file && (
        <p data-knockout-selected-pdf className="mt-2 break-all text-[11px] font-bold text-[#49616D]">Selected: {file.name} · {Math.ceil(file.size/1024).toLocaleString('en-US')} KB</p>
      )}
      {preview && (
        <div data-knockout-preview className="mt-4 rounded-2xl border border-[#C2DED9] bg-[#EFF9F4] p-3 sm:p-4">
          <div className="grid grid-cols-2 gap-2 text-center text-xs sm:grid-cols-4">
            {[
              ['Entries', preview.entry_count],
              ['Weekly picks', preview.pick_rows],
              ['Pool week', preview.max_week],
              ['Duplicate tickets', preview.duplicate_ticket_instances],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-white p-3">
                <div className="text-[10px] font-bold uppercase text-slate-500">{label}</div>
                <div className="mt-1 text-xl font-black text-slate-900">{value ?? '—'}</div>
              </div>
            ))}
          </div>
          {Array.isArray(preview.linked_entry_preview) && preview.linked_entry_preview.length>0 && (
            <div className="mt-3 space-y-2" aria-label="My entries in this uploaded PDF">
              {preview.linked_entry_preview.map(entry => (
                <div key={entry.entry_name} className={`rounded-xl border px-3 py-2.5 text-xs ${entry.exact_match?'border-[#B9D4CD] bg-white text-[#173E52]':'border-[#E7C68D] bg-[#FFF5DF] text-[#805A24]'}`}>
                  <p className="font-black">{entry.exact_match ? 'Found your entry: ' : 'Needs manual review: '}{entry.entry_name}</p>
                  {entry.exact_match ? (
                    <>
                      <p className="mt-1 font-semibold">{Array.isArray(entry.current_week_picks)&&entry.current_week_picks.length
                        ? `Week ${preview.max_week}: ${entry.current_week_picks.join(' + ')}`
                        : `No Week ${preview.max_week} team appears for this exact entry in the uploaded file.`}</p>
                      {!!entry.additional_same_name_tickets_review &&
                        <p className="mt-1 font-bold text-amber-800">{entry.additional_same_name_tickets_review} more same-name ticket(s) exist in this PDF and must be reviewed separately.</p>}
                    </>
                  ) : (
                    <p className="mt-1 flex items-start gap-1 font-semibold"><AlertTriangle size={13} className="shrink-0"/>
                      This exact numbered entry was not matched in the uploaded PDF. Check the organizer’s sheet before confirming.
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
          {!!preview.examples?.length && (
            <div className="mt-3 text-xs leading-6 text-slate-700">
              <b>Sample entries:</b> {preview.examples.map(entry => entry.entry_name).join(' · ')}
            </div>
          )}
          {!!preview.warnings?.length && <p className="mt-2 text-xs font-bold text-amber-800">{preview.warnings.join(' · ')}</p>}
          <label className="mt-4 flex items-start gap-2 text-xs font-semibold leading-5 text-slate-800">
            <input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)}
              className="mt-1" />
            I reviewed the preview and authorize replacing the current whole-pool snapshot. My personal picks must remain preserved.
          </label>
          <button type="button" disabled={!confirmed || working} onClick={commit}
            className="mt-3 rounded-xl bg-blue-700 px-4 py-2.5 text-xs font-black text-white disabled:opacity-40">
            Confirm pool import
          </button>
        </div>
      )}

      {message && <p role="status" className="mt-3 text-xs font-bold leading-5 text-blue-900">{message}</p>}
        </div>
      </details>
    </section>
  )
}
