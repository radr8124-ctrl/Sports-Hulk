# Sports Zenith — Week 5 Survivor Friday Acceptance (October 9, 2026 UTC)

**Scope:** Existing Survivor pool review, official 2026 rules, source-verified odds context, personal used-team eligibility, Saturday deadline and preserved data. No site redesign, no paid bet, no pick submission, no manual change to saved picks.

## Findings and repairs

- The saved active private pool entry is Week 5, ALIVE; original used-team history is preserved. Five past teams remain recorded, Week 5 current saved picks count **0**. Original season rules confirm **one** pick this week and **two** unused teams in Week 6. Deadline: Saturday October 10, 6:00 PM America/New_York, subject to separate early-game exceptions.
- Found a genuine false-positive gate: Survivor V2 called a `WAIT_FOR_FRESH_PRICES` candidate `SHADOW_RECOMMENDATION_READY` when the primary market quote was about a week old, the real market survival probability was null and the strategy index was null. `build_survivor_v2.py` now requires independently timestamped primary-book freshness, finite verified market probability and strategy score, and a permitted action/tier before a shadow selection. Live private result is `WAIT_FOR_FRESH_VERIFIED_MARKET_QUOTES`, **zero** new shadow recommendations; no historical forward entry changed.
- Created separate market-only Survivor review within the **existing** Survivor page, using the already preserved original SportWizzard source and original ESPN fixture ID/start. Pairs same-book HOME/AWAY prices, removes proportional vig, displays original book and capture time, risk flags and later schedule matchup value. This does not prove an independent Zenith win probability, an executable book offer or a qualified pool pick.
- Explicitly excludes each linked entry's previously used teams; never replaces a burned favorite with its underdog as a recommended option. The anonymous public view never includes saved entry identifiers, picks, ownership or used teams.
- The original public NFL primary odds stay correctly quarantined as stale. Historical sportsbook reference data from Friday showed **13 of 15** official upcoming NFL games with genuinely source-matched paired moneyline, spread and total research quotes. User-specific linked selection at that snapshot yields **12** favorite-only market research options, because one of the market favorites was already burned. This is not a list of approved bets/picks.
- Friday source-only no-vig research: Jaguars and Texans each about 76.5%, Bengals about 73.3%, Lions about 67.3%. These percentages are timestamped market observations, not Zenith independent forecasts. The Jaguars have a source-schedule Week 6 home matchup with Houston, important because Week 6 requires two selections; Houston has a separate weak recent-form flag.
- Independent ESPN/DraftKings scoreboard read returned 13 matching two-sided event moneylines; the average absolute difference from archived FanDuel no-vig home probabilities was roughly **0.98 percentage points**, maximum about **1.73**. ESPN did NOT supply trustworthy per-bookmaker quote freshness timestamps; this is a **cross-source consistency diagnostic only**, not confirmation of an up-to-the-second betting offer.
- Overnight source-only hourly regeneration formerly could empty the public odds JSON when the Friday quotes became more than 24 hours old. The builder now stores a separately typed **`ARCHIVED_SOURCE_ONLY_NOT_CURRENT`** payload with the original archive SHA, provider timestamps and source-time-valid paired observations while correctly keeping `fixtures=[]` for expired current prices. The Survivor UI replays archived data **only** under the original capture clock, rechecks the original SHA and excludes games that have started at the actual viewing time. It prominently labels all such data **ARCHIVED / NOT LIVE**.
- Other site work is preserved: the existing Props V2 panel extraction in the uncommitted production App, independent original Survivor-week rules and pick editor, and the separate betting-odds research tab.

## Acceptance

- Survivor Python source/2026-pool-rules tests: **42 passed**.
- Original NFL Survivor source freshness + NFL archive controls: **20 passed** (including next-day zero-fresh archive retention).
- Entire existing website Node test suite: **193 passed**. Two old Brain Record tests had hard-coded daily-changing counts and paper ROI, now assert settled W+L+push accounting, live paper-ROI formatting, no real-money claims and malicious-win falsification.
- Production Vite build: **PASS**.
- Headless browser acceptance: **8 passed** (NFL archived odds, iPhone responsive view, Friday current, simulated Saturday with expired quotes, hourly zero-current output, corrupted archive SHA, no started-game resurrection).
- Actual HTTPS browser at both **390px iPhone** and **1280px desktop** after loading asynchronous data: **13 source-matched options**, later Jacksonville Week 6 schedule displayed, no private entry leak, zero horizontal overflow.
- Live site `/api/health` HTTP **200**; anonymous `/api/survivor/state` HTTP **401**, as designed. Actual authenticated user UI cannot be tested without signing in as the user.
- Original private entries and resolved results unchanged except routine observation/rollover timestamps, verified against original pre-edit backup. The previous Survivor forward prediction ledger is **byte-for-byte SHA identical**. Pre-change scripts and private state were locally SHA-backup-verified under `.deploy_backups/survivor_week5_market_proof_before_20261009T2158Z`.
- Source-only cron runs at **:52** each hour without new paid sportsbook calls. Separate governed NFL refresh timer is observed hourly around **:42**; its 18-hour-before-kickoff window is expected to open Saturday afternoon before the 6 PM ET pool deadline, but **a fresh Saturday provider capture and qualified pick have NOT been verified**.

## Unresolved pre-deadline checks

1. Verify a truly new, unconflicted original primary sportsbook market capture during the Saturday governed window, with source timestamps and official fixture. A new verified quote does not automatically establish independent model edge.
2. Check updated starting-QB availability, injuries and weather before selecting a team. The free injury feed contains statuses but absence from the feed does **not** verify a player's clearance or starting role.
3. The latest official pool-owned/pick sheet is still Week **4**; Week 5 field/ownership remains unverified. This does not change the confirmed Week 5 one-pick requirement.
4. No Week 5 real pool submission has occurred and no private pick was saved. The user must choose and submit any actual selection separately before their pool deadline; saving in Zenith does **not** submit externally.
5. Full independent **off-VPS** raw-data disaster recovery is not verified. Local SHA backups and Git checkpoints are not a substitute.
