import React from 'react'
import { ArrowLeft, Sparkles } from 'lucide-react'

export default function DashboardWorkspaceNav({ active, onNavigate }) {
  return <nav aria-label="Dashboard workspace" className="flex min-w-0 flex-wrap items-center justify-between gap-2 text-xs font-black text-[#276977]">
    <button type="button" onClick={() => onNavigate('Dashboards')} className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-[#D1DDD9] bg-white px-3"><ArrowLeft size={15} /> All dashboards</button>
    <span className="hidden text-[#506B75] sm:block">{active}</span>
    <button type="button" onClick={() => onNavigate('Ask')} className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-[#D1DDD9] bg-white px-3"><Sparkles size={15} /> Ask The Ref</button>
  </nav>
}

export function jumpToDashboardSection(id) {
  const section = document.getElementById(id)
  if (!section) return
  section.scrollIntoView({ block:'start', behavior:'auto' })
  section.focus({ preventScroll:true })
}
