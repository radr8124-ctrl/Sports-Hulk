import React, { useEffect, useRef, useState } from 'react'

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
    <section aria-label="Import full Survivor pool" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.14em] text-blue-700">Pool manager</p>
          <h2 className="mt-1 text-xl font-black text-slate-950">Import full Survivor pool</h2>
          <p className="mt-2 max-w-2xl text-xs leading-5 text-slate-600">
            Upload the official PDF, XLSX or CSV sheet. Preview before confirming. Repeated names can represent separate tickets.
            Only newer or current-week sheets may replace the verified pool snapshot.
          </p>
        </div>
        <span className="rounded-xl bg-slate-100 px-3 py-2 text-[10px] font-black uppercase text-slate-700">
          Manager only
        </span>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <input ref={fileRef} aria-label="Choose official pool file" type="file"
          accept=".pdf,.xlsx,.csv" className="min-w-0 flex-1 text-xs text-slate-700"
          onChange={event => {
            setFile(event.target.files?.[0] || null)
            setPreview(null)
            setEncoded(null)
            setConfirmed(false)
            setMessage('')
          }} />
        <button type="button" disabled={!file || working} onClick={makePreview}
          className="rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white disabled:opacity-40">
          {working ? 'Checking…' : 'Preview pool file'}
        </button>
      </div>

      {preview && (
        <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4">
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
    </section>
  )
}
