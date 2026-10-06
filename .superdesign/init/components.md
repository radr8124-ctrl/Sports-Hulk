# Sports HULK Shared UI Components

The frontend has no dedicated component-library directory. Reusable primitives and product patterns are currently defined inline in feature files.

## Brand
- Source: `src/App.jsx`
- Purpose: Sports HULK wordmark and Sports Intelligence sublabel.
```jsx
function Brand() {
  return (
    <div>
      <div className="text-xl font-black tracking-tight text-slate-950">
        SPORTS <span className="text-emerald-600">HULK</span>
      </div>
      <div className="mt-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
        Sports intelligence
      </div>
    </div>
  )
}

```

## StatusStrip
- Source: `src/App.jsx`
- Purpose: Four-card system health/status row under the command-center hero.
```jsx
function StatusStrip() {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {statusCards.map((item) => (
        <div key={item.label} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-soft">
          <div className="text-xs font-bold uppercase tracking-[0.14em] text-slate-400">{item.label}</div>
          <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-extrabold ${toneClass[item.tone]}`}>
            {item.value}
          </div>
        </div>
      ))}
    </div>
  )
}

```

## EmptyPanel
- Source: `src/App.jsx`
- Purpose: Placeholder state for reserved top-level routes.
```jsx
function EmptyPanel({ icon: Icon, title, text, action }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-soft">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-100 text-slate-600">
        <Icon size={21} />
      </div>
      <h3 className="mt-5 text-lg font-black text-slate-950">{title}</h3>
      <p className="mt-2 max-w-xl text-sm leading-6 text-slate-500">{text}</p>
      {action && <button className="mt-5 text-sm font-extrabold text-blue-700">{action} →</button>}
    </div>
  )
}


```

## SectionGrid
- Source: `src/App.jsx`
- Purpose: Reusable grid of feature-entry buttons.
```jsx
function SectionGrid({ title, items }) {
  return (
    <section>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Product area</p>
          <h2>{title}</h2>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <button key={item} className="group flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-soft transition hover:-translate-y-0.5 hover:border-blue-200">
            <span className="font-extrabold text-slate-800">{item}</span>
            <ChevronRight size={18} className="text-slate-300 transition group-hover:text-blue-600" />
          </button>
        ))}
      </div>
    </section>
  )
}

```

## Performance StatusPill
- Source: `src/PerformancePanel.jsx`
- Purpose: Compact status badge used throughout Brain Record.
```jsx
function StatusPill({ value }) {
  const text = String(value || 'WAITING')
  const upper = text.toUpperCase()
  const tone =
    upper.includes('MATUR') || upper.includes('READY') || upper.includes('HOLD')
      ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
      : upper.includes('WAIT') || upper.includes('TINY')
        ? 'border-amber-200 bg-amber-50 text-amber-700'
        : upper.includes('SELECT') || upper.includes('CANDIDATE')
          ? 'border-rose-200 bg-rose-50 text-rose-700'
          : 'border-blue-200 bg-blue-50 text-blue-700'
  return (
    <span className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${tone}`}>
      {pretty(text)}
    </span>
  )
}

```

## BrainMetricCard
- Source: `src/PerformancePanel.jsx`
- Purpose: Summary KPI card used for historical model validation.
```jsx
function BrainMetricCard({ item, icon: Icon }) {
  const decisions = Number(item?.decisions || 0)
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-100 text-slate-700">
          <Icon size={19} />
        </div>
        <StatusPill value={item?.maturity} />
      </div>
      <div className="mt-4 text-xs font-black uppercase tracking-[0.14em] text-slate-400">{item?.label || 'Research'}</div>
      <div className="mt-2 flex items-end gap-3">
        <div className="text-3xl font-black tracking-tight text-slate-950">{pct(item?.hit_rate_pct)}</div>
        <div className="pb-1 text-sm font-extrabold text-slate-500">
          {item?.wins || 0}-{item?.losses || 0}{item?.pushes ? `-${item.pushes}` : ''}
        </div>
      </div>
      <div className="mt-2 text-xs leading-5 text-slate-500">
        {integer(decisions)} qualified settled decisions
        {item?.wilson_low_pct != null && item?.wilson_high_pct != null
          ? ` · 95% range ${pct(item.wilson_low_pct)}–${pct(item.wilson_high_pct)}`
          : ''}
      </div>
      <div className="mt-4 border-t border-slate-100 pt-3 text-[11px] font-semibold text-slate-400">
        Historical validation · not the official public record
      </div>
    </div>
  )
}

```

## AskCard
- Source: `src/AskSportsHulk.jsx`
- Purpose: Rich answer card for the assistant experience.
```jsx
function AskCard({ answer, compact = false }) {
  if (!answer) return null
  return (
    <div className={`rounded-3xl border border-emerald-400/20 bg-slate-950/80 shadow-2xl shadow-emerald-950/20 ${compact ? 'p-4' : 'p-5 md:p-6'}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-emerald-300">
            <Sparkles size={15} /> HULK TAKE
          </div>
          <div className={`mt-2 font-black tracking-tight text-white ${compact ? 'text-lg' : 'text-2xl'}`}>
            {answer.take || 'No current take.'}
          </div>
        </div>
        <span className={`rounded-full border px-3 py-1.5 text-[11px] font-black uppercase tracking-wide ${tone(answer.confidence)}`}>
          {answer.confidence || answer.status || 'RESEARCH'}
        </span>
      </div>

      {!!answer.why?.length && (
        <div className="mt-5">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-emerald-300">
            <Zap size={14} /> Why
          </div>
          <ul className="mt-2 space-y-1.5 text-sm leading-6 text-slate-200">
            {answer.why.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {!!answer.risk?.length && (
        <div className="mt-4 rounded-2xl border border-amber-400/15 bg-amber-400/5 p-3">
          <div className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-amber-300">
            <AlertTriangle size={14} /> Risk
          </div>
          <ul className="mt-2 space-y-1.5 text-sm leading-5 text-slate-300">
            {answer.risk.map((item, i) => <li key={i}>• {item}</li>)}
          </ul>
        </div>
      )}

      {!!answer.cards?.length && !compact && (
        <div className="mt-5 grid gap-2 md:grid-cols-2">
          {answer.cards.slice(0, 6).map((card, i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-white/5 p-3">
              <div className="text-xs font-black uppercase tracking-wide text-slate-500">
                {String(card.type || answer.intent || 'research').replaceAll('_', ' ')}
              </div>
              <div className="mt-1 text-sm font-extrabold text-white">{card.title || card.selection || 'Research'}</div>
              <div className="mt-1 text-xs leading-5 text-slate-400">
                {card.selection ? `${card.market || ''} · ${card.selection} ${card.line ?? ''}` :
                 card.side ? `${card.side} ${card.line ?? ''} · ${card.market || ''}` :
                 card.opponent ? `vs ${card.opponent}` :
                 card.projection != null ? `${card.projection} proj · $${card.salary ?? '—'}` :
                 card.source || ''}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 border-t border-white/10 pt-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] font-semibold text-slate-500">
          {!!answer.sources?.length && (
            <span>Sources: {answer.sources.map(s => s.source || s.label).filter(Boolean).slice(0, 3).join(' · ')}</span>
          )}
          <span>Updated: {relativeTime(answer.updated_at || answer.generated_at)}</span>
        </div>
      </div>
    </div>
  )
}

```

## DfsPlayerRow
- Source: `src/DfsLineupLab.jsx`
- Purpose: DFS optimizer player row with lock/exclude actions.
```jsx
function DfsPlayerRow({ player, locked, excluded, onLock, onExclude }) {
  const status = String(player.availability_status || 'AVAILABLE').toUpperCase()
  const risky = ['QUESTIONABLE', 'DOUBTFUL', 'OUT', 'INACTIVE'].includes(status)

  return (
    <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 sm:grid-cols-[1fr_auto] sm:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-black text-slate-950">{player.player}</span>
          <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-black text-slate-600">
            {player.position}
          </span>
          {risky && (
            <span className="rounded-full bg-amber-50 px-2 py-1 text-[10px] font-black text-amber-700">
              {status}
            </span>
          )}
        </div>
        <div className="mt-1 text-xs font-semibold text-slate-500">
          {player.team || '—'} · {money(player.salary)} · {number(player.projected_fantasy_points)} proj · {number(player.audit_value_per_1000, 2)} pts/$1K
        </div>
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onLock}
          className={`rounded-xl border px-3 py-2 text-xs font-black transition ${locked ? 'border-emerald-300 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-white text-slate-600 hover:border-emerald-200'}`}
        >
          {locked ? 'LOCKED' : 'Lock'}
        </button>
        <button
          type="button"
          onClick={onExclude}
          className={`rounded-xl border px-3 py-2 text-xs font-black transition ${excluded ? 'border-rose-300 bg-rose-50 text-rose-700' : 'border-slate-200 bg-white text-slate-600 hover:border-rose-200'}`}
        >
          {excluded ? 'EXCLUDED' : 'Exclude'}
        </button>
      </div>
    </div>
  )
}

```
