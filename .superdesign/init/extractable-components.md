# Sports HULK Extractable Components

## AppShell
- Source: `src/App.jsx`
- Category: layout
- Description: Shared page shell with brand header, top nav, hero, assistant launcher/drawer and footer.
- Extractable props: activeView, backendLabel, assistantOpen
- Hardcoded: Sports HULK wordmark, nav labels, hero copy, footer copy, Lucide icon choices.

## BrandHeader
- Source: `src/App.jsx`
- Category: layout
- Description: Sticky top brand row with wordmark and backend health chip.
- Extractable props: backendLabel
- Hardcoded: Sports HULK / Sports Intelligence text treatment.

## TopNav
- Source: `src/App.jsx`
- Category: layout
- Description: Horizontally scrolling top-level navigation with active-state pill.
- Extractable props: activeItem
- Hardcoded: labels sourced from `dashboardConfig.js`, slate active/inactive styles.

## StatusStrip
- Source: `src/App.jsx`
- Category: basic
- Description: Four status cards for live scores, market data, Survivor and learning loop.
- Extractable props: status values
- Hardcoded: card structure and tone mapping.

## SectionGrid
- Source: `src/App.jsx`
- Category: basic
- Description: Feature-entry card grid used for NFL/Fantasy tool discovery.
- Extractable props: title, items
- Hardcoded: ChevronRight icon and hover treatment.

## AssistantLauncher
- Source: `src/AskSportsHulk.jsx`
- Category: layout
- Description: Floating persistent sports-assistant launcher.
- Extractable props: onClick
- Hardcoded: Sports HULK visual label/icon treatment.

## BrainMetricCard
- Source: `src/PerformancePanel.jsx`
- Category: basic
- Description: Brain Record metric card for historical performance summaries.
- Extractable props: item, icon
- Hardcoded: card layout, typography and state styling.

## PerformanceStatusPill
- Source: `src/PerformancePanel.jsx`
- Category: basic
- Description: Compact status chip used throughout diagnostics.
- Extractable props: value
- Hardcoded: status color logic.

## AskCard
- Source: `src/AskSportsHulk.jsx`
- Category: basic
- Description: Assistant answer card with confidence/timing/source presentation.
- Extractable props: answer, compact
- Hardcoded: dark assistant visual system.

## DfsPlayerRow
- Source: `src/DfsLineupLab.jsx`
- Category: basic
- Description: DFS lineup player row with lock/exclude actions and projection information.
- Extractable props: player, locked, excluded
- Hardcoded: layout and Lucide iconography.
