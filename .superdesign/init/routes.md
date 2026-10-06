# Sports HULK Route / View Map

Sports HULK currently uses React state in `src/App.jsx` instead of React Router. The URL only distinguishes the assistant with `#ask`; all other top-level views share the root shell.

## Top-level navigation
Source: `src/dashboardConfig.js`

- Home → `App.jsx`: Scoreboard, DecisionPanel, SurvivorPanel, LearningPanel
- Ask Sports HULK → `AskSportsHulk.jsx`: full-screen assistant page; URL hash `#ask`
- NFL → `App.jsx`: NflPanel
- MLB → `App.jsx`: MlbPanel
- NBA → reserved placeholder via EmptyPanel
- CFB → reserved placeholder via EmptyPanel
- Props → `App.jsx`: NflPropsPanel
- Parlays → `App.jsx`: NflParlaysPanel
- Survivor → `App.jsx`: SurvivorRoutePanel
- Fantasy → `App.jsx`: FantasyCommandCenter, which can render DFS Lineup Lab
- Practice → `PracticeBetting.jsx`
- Brain Record → `PerformancePanel.jsx`
- Research → reserved placeholder via EmptyPanel

## App shell navigation source
```jsx
export default function App() {
  const initialActive = window.location.hash === '#ask' ? 'Ask Sports HULK' : 'Home'
  const [active, setActive] = useState(initialActive)
  const [assistantOpen, setAssistantOpen] = useState(false)
  const backendLabel = useMemo(() => insforgeConfigured ? 'INSFORGE CONNECTED' : 'SPORTS HULK LIVE DATA', [])
  const isAsk = active === 'Ask Sports HULK'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center justify-between gap-6 px-5 py-4">
          <Brand />
          <div className="hidden items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-extrabold text-slate-600 md:flex">
            <Activity size={15} className="text-emerald-500" />
            {backendLabel}
          </div>
        </div>
      </header>
      <nav className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] gap-2 overflow-x-auto px-5 py-3">
          {navItems.map((item) => (
            <button
              key={item}
              onClick={() => {
                setActive(item)
                setAssistantOpen(false)
                window.history.replaceState(null, '', item === 'Ask Sports HULK' ? '#ask' : '#')
              }}
              className={`whitespace-nowrap rounded-xl px-4 py-2 text-sm font-extrabold transition ${
                active === item
                  ? 'bg-slate-950 text-white'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              {item}
            </button>
          ))}
        </div>
      </nav>

      <main className="mx-auto max-w-[1500px] space-y-8 px-5 py-8">
        {isAsk ? (
          <AskSportsHulkPage />
        ) : (
          <>
        <section className="rounded-[30px] border border-slate-200 bg-white p-7 shadow-soft md:p-9">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div>
              <p className="eyebrow">Command Center</p>
              <h1 className="mt-2 max-w-4xl text-4xl font-black tracking-tight text-slate-950 md:text-5xl">
                Simple answer on top.
                <span className="block text-blue-700">Everything accountable underneath.</span>
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-500">
                Scores, decisions, props, parlays, Survivor and fantasy in one stable product.
                No invented data, no hidden stale feeds and no forced picks.
              </p>
            </div>
            <div className="grid min-w-[260px] grid-cols-2 gap-3">
              <div className="mini-metric"><Brain size={18} /><b>Learning</b><span>Persistent</span></div>
              <div className="mini-metric"><ShieldCheck size={18} /><b>Evidence</b><span>Traceable</span></div>
            </div>
          </div>
        </section>

        <StatusStrip />
        {active === 'Home' && (
          <>
            <Scoreboard />
            <DecisionPanel />
            <SurvivorPanel />
            <LearningPanel />
          </>
        )}

        {active === 'NFL' && <NflPanel />}

        {active === 'MLB' && <MlbPanel />}

        {active === 'Props' && <NflPropsPanel />}

        {active === 'Parlays' && <NflParlaysPanel />}

        {active === 'Survivor' && <SurvivorRoutePanel />}

        {active === 'Fantasy' && <FantasyCommandCenter />}

        {active === 'Practice' && <PracticeBetting />}

        {active === 'Brain Record' && <PerformancePanel />}

        {!['Home', 'NFL', 'MLB', 'Props', 'Parlays', 'Survivor', 'Fantasy', 'Practice', 'Brain Record'].includes(active) && (
          <EmptyPanel
            icon={LayoutDashboard}
            title={active}
            text="This route is reserved in the permanent navigation. The next build will wire its validated data contract without changing the product shell."
          />
        )}
          </>
        )}
      </main>

      {!isAsk && <AssistantLauncher onClick={() => setAssistantOpen(true)} />}
      <AssistantDrawer
        active={assistantOpen && !isAsk}
        onClose={() => setAssistantOpen(false)}
        onOpenFull={() => {
          setActive('Ask Sports HULK')
          setAssistantOpen(false)
          window.history.replaceState(null, '', '#ask')
        }}
      />

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-2 px-5 py-6 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>Sports HULK · Sports Intelligence</span>
          <span>Real data · Unknown stays UNKNOWN · Stale stays STALE</span>
        </div>
      </footer>
    </div>
  )
}
```

## Navigation configuration
```js
export const navItems = [
  'Home', 'Ask Sports HULK', 'NFL', 'MLB', 'NBA', 'CFB',
  'Props', 'Parlays', 'Survivor', 'Fantasy', 'Practice', 'Brain Record', 'Research',
]

export const statusCards = [
  { label: 'Live scores', value: 'WAITING', tone: 'blue' },
  { label: 'Market data', value: 'WAITING', tone: 'amber' },
  { label: 'Survivor', value: 'READY', tone: 'emerald' },
  { label: 'Learning loop', value: 'READY', tone: 'violet' },
]

export const nflSections = [
  'Best Bets', 'Player Props', 'Parlays', 'Matchups',
  'Survivor', 'Weather', 'Results', 'Deep Dive',
]

export const fantasySections = [
  'My Leagues', 'Start / Sit', 'Waivers', 'Trades',
  'Playoff Planner', 'Draft Intel', 'Top 300',
]

```
