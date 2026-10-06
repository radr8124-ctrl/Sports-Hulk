# Sports HULK Page / View Dependency Trees

## Home
Entry: `src/App.jsx`
Dependencies:
- `src/App.jsx`
  - Brand
  - StatusStrip
  - Scoreboard
  - DecisionPanel
  - SurvivorPanel
  - LearningPanel
  - AssistantLauncher / AssistantDrawer → `src/AskSportsHulk.jsx`
  - `src/dashboardConfig.js`
  - `src/styles.css`

## Ask Sports HULK
Entry: `src/App.jsx` → `src/AskSportsHulk.jsx`
Dependencies:
- `src/AskSportsHulk.jsx`
  - AskCard
  - LiveRail
  - AskSportsHulkPage
  - AssistantDrawer
  - AssistantLauncher
- `src/styles.css`

## NFL
Entry: `src/App.jsx`
Dependencies:
- NflPanel
  - NflGamesPanel
  - NflPropsPanel
  - NflParlaysPanel
  - SectionGrid
- `src/dashboardConfig.js`
- `src/styles.css`

## MLB
Entry: `src/App.jsx`
Dependencies:
- MlbPanel
  - MlbBoxScore
  - MlbStatTable
- `src/styles.css`

## Props
Entry: `src/App.jsx`
Dependencies:
- NflPropsPanel
- shared App shell
- `src/styles.css`

## Parlays
Entry: `src/App.jsx`
Dependencies:
- NflParlaysPanel
- shared App shell
- `src/styles.css`

## Survivor
Entry: `src/App.jsx`
Dependencies:
- SurvivorRoutePanel
- shared App shell
- `src/styles.css`

## Fantasy
Entry: `src/App.jsx`
Dependencies:
- FantasyCommandCenter
  - FantasyNewsPanel
  - SectionGrid
  - `src/DfsLineupLab.jsx`
- `src/dashboardConfig.js`
- `src/styles.css`

## Practice
Entry: `src/App.jsx` → `src/PracticeBetting.jsx`
Dependencies:
- `src/PracticeBetting.jsx`
- shared App shell
- `src/styles.css`

## Brain Record
Entry: `src/App.jsx` → `src/PerformancePanel.jsx`
Dependencies:
- OfficialRecord
- BrainMetricCard
- ExperimentRegistryPanel
- BettingV2Panel
- AllMarketsV2Panel
- PropV2Panel
- ParlayV2Panel
- SurvivorV2Panel
- FantasyV2Panel
- DfsAccountability
- ThresholdLab
- ScoreCalibrationAudit
- SelectivityWatch
- ResearchTable
- shared App shell
- `src/styles.css`
