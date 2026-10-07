# NBA Competition Regime — Production Deployment

Date: 2026-10-07
Branch: main
Source commit: 838695c Attach official NBA competition types to decision proof
GitHub: main synchronized; read-only GitHub Actions CI run 37682541787 completed successfully
Backup: .deploy_backups/nba_regime_20261007T202815Z
Recovery branch: backup/pre-nba-regime-20261007T202815Z

## Verified source changes
- Source matching uses ESPN official event season.type only; no calendar or sportsbook inference.
- Production NBA_GAME_DECISIONS.csv enrichment: 776/776 rows verified, covering 16 unique NBA games.
- All 776 current future betting-market decision rows were explicitly REGULAR.
- Five ESPN daily endpoint lookups succeeded without source errors.
- Every existing nonmetadata decision field was byte-for-byte equivalent as a parsed CSV value before/after enrichment.
- NBA Core's prior missing season_type was corrected by reading an explicit ESPN event seasonType reference.
- The subsequent scheduled NBA core refresh produced 52 NBA game records labeled PRESEASON with explicit source value 1.
- No Betting V2 model promotion authorized; no current qualified NBA Bet V2 pick. Ask API correctly responds WAITING for current NBA best game bet.

## Acceptance
- 59 NBA and regime proof tests PASS
- 8 GitHub deployment-safety tests PASS
- 66 commercial web Node tests PASS
- Vite production build PASS
- GitHub remote CI PASS, read-only, no auto deploy
- Regenerated all-markets current, all-markets forward, CLV tracker and Brain Performance: all PASS
- Both all-markets forward and price ledgers preserved original byte prefixes:
  - forward: 620111 -> 622659 bytes
  - price: 1047483 -> 1050700 bytes
- Commercial API /api/health HTTP 200
- Survivor streamlit /_stcore/health HTTP 200
- No frontend deployment/restart required.
- Existing in-progress commercial_web/src/App.jsx and nba_live/build_nba_markets.py changes were preserved.

## Ongoing verification
- Next NBA refresh pipeline auto-runs the enrichment step after successful decision brain generation.
- Historical NBA training evidence remains isolated; no unproven mixing/promotion.

## Scheduled end-to-end refresh verification
- NBA service timer launched 2026-10-07 20:32 UTC and completed with `NBA REFRESH COMPLETE`.
- The scheduled NBA core stage regenerated 52 preseason rows with explicit `season_type=1`.
- The scheduled decision-brain pipeline independently ran the new ESPN exact-game verifier at 20:33 UTC.
- Its receipt is `READY`, 5/5 ESPN date requests succeeded, 776/776 decision rows were VERIFIED and 16/16 distinct future games labeled REGULAR.
- No qualified NBA bet was promoted and Ask Game Scout continues to return WAITING.
- Commercial and Survivor HTTP health checks remain 200 after scheduled refresh.
