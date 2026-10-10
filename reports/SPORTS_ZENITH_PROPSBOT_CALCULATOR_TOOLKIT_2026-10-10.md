# Sports Zenith — PropsBot Calculator Toolkit Reference and Implementation
Date reviewed: October 9, 2026 America/New_York (VPS UTC October 10).

## Eight user-supplied reference URLs examined
1. https://propsbot.ai/tools/ — umbrella catalogue; describes eight calculators: implied probability, parlay payout, hold/vig, EV, no-vig, hedge, Kelly and SGP value.
2. https://propsbot.ai/tools/odds-converter/ — American, decimal, fractional, implied probability, profit and return; its own optional embed is third-party code; intentionally **not** imported into Zenith.
3. https://propsbot.ai/tools/parlay-calculator/ — 2–12 manual legs, mixed price formats, theoretical payout; expressly warns correlation/push/settlement not modeled and big payout is not evidence of value.
4. https://propsbot.ai/tools/hedge-calculator/ — original stake, original price, hedge side price, equal-gross-return stake and win/loss on each mutually exclusive outcome; even an apparently locked hedge can lose.
5. https://propsbot.ai/tools/kelly-criterion-calculator/ — mathematical Full/Half/Quarter Kelly as a function of user-supplied *true probability*, not validation of that probability; large downside sensitivity when p is wrong.
6. https://propsbot.ai/tools/hold-vig-calculator/ — two-way bookmaker margin plus proportional no-vig removal; no-vig probability is *market opinion*, not independent true probability.
7. https://propsbot.ai/ai-parlay-generator/ — says single-leg value and same-game correlation should precede a suggested combination; with Zenith's unverified leg-edge/correlation proof, it must **not** automatically generate APPROVED parlays.
8. https://propsbot.ai/ai-betting-bot/ — markets named Confidence + Edge filter, sportsbook comparisons and a claimed public graded track record/large ROI. These are provider promotional claims, **not independently audited here** and absolutely not inherited by Sports Zenith.

## Changes actually made on the existing Zenith website
- New **Tools** subtab under the existing Bets navigation with direct URL https://sportszenith.com/#tools. Original Bets, Props, PrizePicks, Parlays, Bet Lab, Survivor and The Ref are unchanged.
- New small mobile/desktop `commercial_web/src/BetToolsPanel.jsx` (no third-party embeds or paid data). Original calculation inputs remain in ephemeral React state; no wagers, orders, practice-bankroll ledger writes, sportsbook auth or account data capture.
- `commercial_web/zenith_odds_math.js` pure deterministic math with strict input validation for:
  **Odds**: American, decimal, fractional and implied-probability conversion; stake-based profit and return.
  **Hold & no-vig**: two actual opposing prices from one binary sportsbook market and exact line; proportional hold removal, fair no-vig quote examples.
  **EV & Kelly**: break-even implied probability, user manually supplied estimate, hypothetical expected return per $100 and Full/Half/Quarter Kelly calculations. Explicit **0 units recommended**, since the input probability is not an independently proven Zenith model.
  **Hedge**: equal-gross-return opposite-side stake and net after both stakes under exactly two mutually exclusive exhaustive outcomes, including a negative locked-in-loss warning. Voids/pushes/account execution NOT modeled.
  **Parlay payout**: 2–12 manually supplied legs and mixed American/decimal/fractional/probability formats. Multiplied decimal price, total return and profit if all legs win. This does not generate plays, model joint probability, or account for correlation, settlement rules or real sportsbook parlay repricing.
- Added calculator research safeguards/zero false-play flags and a **manual price only** legend so no example output can impersonate a current quoted/available line, calibrated model or guaranteed return.
- No third-party scripts, PropsBot assets, API connectors or browser cookies used. Calculations execute in client JavaScript in the existing site bundle.
- Ref assistant context expanded to recognize the Tools section through the existing page-aware prompts; no Ref model weights, backend, input history or saved private Survivor data modified.

## Where this fits in the larger Zenith roadmap
Immediate product experience: show real game sportsbook prices and comparisons on Bets, explain the difference between market implied probability and experimental Zenith forecasts with The Ref, let users check pricing mathematics transparently in Tools.
Separate next research tasks: better model independence, authenticated executable bookmaker offers and immutable price-to-close quality, public exact-entry results, game-blocked forward learning and correlations for PrizePicks/SGPs. An AI parlay generator or +EV auto-pick engine should remain blocked while independent joint win-probability and source-price validation are absent.

## Evidence and limits
This is a genuine original implementation inspired by public reference descriptions, not copied proprietary content. No real-money betting integrations or validated expected-value recommendations were created. Claims from PropsBot's own site regarding number of sportsbooks, model architecture or ROI were not independently audited.
Pre-edit source backups, byte-readback SHA256: .deploy_backups/zenith_betting_toolkit_before_20261010T0220Z/. Original server.js contained pre-existing unrelated uncommitted Survivor logic; it was **not changed** for this toolkit.

## Acceptance
- Pure-math source and calculation validity checked against known published examples: -110 implies 52.38%, paired -110/-110 hold 4.76%; 55%-vs--110 illustrative EV=+5%, mathematical quarter Kelly 1.375% bankroll, $100 +200 vs -150 hedge example $180 stake/$20 either-side net, two -110 legs $10 combined total return $36.45. Invalid odds/probabilities/negative stakes fail closed.
- Browser checks include iPhone width 390px and desktop width 1280px, all interactive modes, invalid inputs, route navigation and no horizontal overflow.
- **Verified acceptance:** 10 new unit math tests; **221/221** total website JavaScript unit tests; **41/41** existing and new Playwright browser checks (including mobile Ask, Survivor, props, full betting odds, learning board and all five calculator modes). Production Vite build passed. Live iPhone-width 390px and desktop 1280px had **zero horizontal overflow** and Tools opened at scroll Y=0.

**Off-server backup restoration is not verified by this work.** Original saved model outputs, Survivor picks, NFL archived bookmaker source files and historical performance ledgers were neither read for retraining nor modified.
