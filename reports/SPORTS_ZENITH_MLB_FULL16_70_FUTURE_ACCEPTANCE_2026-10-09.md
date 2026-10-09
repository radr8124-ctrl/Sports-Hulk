# Sports Zenith — MLB Full16 future-only confidence/value experiment

October 9, 2026 UTC. **Research only. No real bets, model promotion, or claimed predictive edge.**

Original MLB Full16 18-player gamePk 849832 is already graded. Original frozen-source SHA-256: `0cea5e38c94451cacbc1ff552276c5df7aa1e341296b127fd0cfa6a2d19c66a8`. The first game produced Full16 Brier 0.215108184 vs raw market Brier 0.216895142, **one independent game only**, not proven edge.

A new immutable preregistration `reports/ZENITH_MLB_FULL16_SELECTIVE_70_FORWARD_PREREG_2026-10-09.json` was saved **06:30:02 UTC**, after the original one-game result but before any newly eligible game. Its scope explicitly excludes old gamePk 849832 and all 18 already graded player predictions. The original model SHA is fixed: `1b825e93dc48729346619d4c61978e1cb939fc16bc6156b11394fb01ee9d8df5`.

New separate research module `intelligence_warehouse/selective_forward/mlb_70_forward_evidence.py` records one original OVER/UNDER 0.5 side per player-game: >=70% original frozen model probability, >=3 percentage point difference over the exact same-book no-vig price, >=3% quoted price hypothetical EV, pregame frozen team/source/player/book/line/MLBAM ID and source quote age <=5 minutes. It records both abstentions and provisional paper qualifiers, with all results labeled non-executable/untested. No grade can be attached except through an existing independently verified MLB official Final hitter result matching exact old model, quote, original lineup source hash, game, player and bookmaker. Never backfill picks after game time.

Manual first post-registration attempt had **18 already settled original player predictions excluded, zero NEW future game predictions, zero qualifiers, zero new official grade results**, and zero real wagers. No original source/model/MLB player history was changed. The governed 15-second safe-run returned **rc=0** and the combined unit tests/wiring tests **13 passed**. This is a readiness success, not a win-rate improvement.

The nonblocking research stage was added after the existing official MLB learning and before official fixture readiness in the existing ten-minute `mlb_live/run_mlb_refresh.sh`. The independent official schedule guard may still hold source-mismatched future games: the study will never retroactively invent valid fixtures or source odds.

The live site is not a research dashboard and has not had new recommendations pushed. The first next normal automatic timer run after this new stage remains to be verified before claiming full automated integration.

Private future paper ledgers and summary are locally excluded from Git via `.git/info/exclude`; research source code, test suite and preregistration can be versioned. Original source and runner files were locally backed up before the change under `.deploy_backups/zenith_mlb_full16_selectivity_before_timer_20261009T063300Z`; independent off-VPS recovery remains **unverified**.
