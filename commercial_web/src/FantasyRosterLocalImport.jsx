import React, { useState } from 'react'
import { CheckCircle2, FileText, ShieldCheck, Upload, X } from 'lucide-react'
import { previewFantasyRosterFile } from './fantasyRosterFileParser'

export default function FantasyRosterLocalImport({ onApply, existingCount = 0 }) {
  const [preview,setPreview] = useState(null)
  const [error,setError] = useState('')
  const [busy,setBusy] = useState(false)
  const [applied,setApplied] = useState('')

  const loadFile = async event => {
    const file=event.target.files?.[0]
    event.target.value=''
    if(!file) return
    setPreview(null)
    setError('')
    setApplied('')
    if(file.size > 256*1024) {
      setError('That file is too large. Upload a CSV or TXT roster smaller than 256 KB.')
      return
    }
    setBusy(true)
    try {
      const ext=String(file.name||'').trim().toLowerCase().split('.').pop()
      if(!['csv','txt'].includes(ext)){
        throw new Error('Choose a CSV or TXT roster (you can export Excel as CSV).')
      }
      const result=previewFantasyRosterFile(await file.text(),file.name)
      setPreview({...result,fileName:file.name})
    } catch(err) {
      setError(err instanceof Error ? err.message : 'The roster could not be previewed.')
    } finally {setBusy(false)}
  }

  const apply = () => {
    if(!preview?.names?.length) return
    onApply?.(preview.names)
    setApplied('Added '+preview.count+' players to your roster editor. Review the names, then choose Analyze & save my team to save them.')
    setPreview(null)
  }

  return (
    <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-black text-blue-800">
        <Upload size={16} /> Import roster from CSV or TXT
      </summary>
      <p className="mt-2 text-xs leading-5 text-slate-600">
        Use a CSV export with a Player or Name column, or a plain-text file with one NFL player per line. Works without ESPN, Yahoo or CBS account connection; only your local file is previewed.
      </p>
      <label className="mt-3 flex w-full cursor-pointer flex-wrap items-center justify-center gap-2 rounded-xl border border-dashed border-blue-300 bg-white px-3 py-4 text-sm font-black text-blue-700 hover:border-blue-500">
        <FileText size={17} /> {busy ? 'Reading roster…' : 'Choose a roster file'}
        <input aria-label="Upload fantasy roster CSV or TXT" type="file" accept=".csv,.txt,text/csv,text/plain" onChange={loadFile} disabled={busy} className="sr-only" />
      </label>
      {error && <p role="alert" className="mt-3 rounded-xl border border-rose-100 bg-rose-50 p-3 text-xs font-semibold text-rose-800">{error}</p>}
      {applied && <p role="status" className="mt-3 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-xs font-semibold text-emerald-900"><CheckCircle2 size={14} className="mr-1 inline" />{applied}</p>}
      {preview && (
        <div className="mt-4 rounded-xl border border-blue-200 bg-white p-3" aria-label="Roster import preview">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0 text-sm font-black text-slate-900">{preview.count} players found</div>
            <button type="button" onClick={()=>setPreview(null)} aria-label="Discard roster preview" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X size={16} /></button>
          </div>
          <p className="mt-1 break-words text-[11px] font-medium text-slate-500">{preview.fileName} · {preview.format} · column: {preview.column}</p>
          {!!(preview.skipped || preview.duplicates) &&
            <p className="mt-2 text-xs font-semibold text-amber-800">{preview.duplicates} duplicate rows excluded · {preview.skipped} invalid/empty rows ignored</p>}
          {!!preview.reformatted && <p className="mt-2 text-xs font-semibold text-blue-800">{preview.reformatted} “Last, First” name(s) changed to “First Last”; review them before saving.</p>}
          <ol className="mt-3 max-h-40 list-decimal space-y-1 overflow-y-auto pl-5 text-xs font-semibold text-slate-700">
            {preview.names.map((name,index)=><li key={index}>{name}</li>)}
          </ol>
          <p className="mt-3 text-xs leading-5 text-slate-600">
            {existingCount ? 'This will replace the names currently shown in the roster editor, not the saved team on the server. ' : ''}
            Review player spellings before saving. The file stays on your device.
          </p>
          <button type="button" onClick={apply} className="mt-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-xs font-black text-white">
            <CheckCircle2 size={16} /> Use these {preview.count} players in editor
          </button>
        </div>
      )}
      <div className="mt-3 flex items-start gap-2 text-[11px] leading-5 text-slate-500">
        <ShieldCheck size={15} className="mt-0.5 shrink-0" />
        Preview only: no provider passwords, session cookies, or roster file uploads to our server. The existing manual Analyze & save action remains required.
      </div>
    </details>
  )
}
