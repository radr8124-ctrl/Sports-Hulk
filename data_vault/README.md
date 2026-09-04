# SPORTS HULK — NFL Data Vault

Standalone raw-data layer. It does not replace `app.py` and does not touch `.env`.

Included sources:
- players
- nflfastR play-by-play (1999+)
- rosters (1920+)
- weekly rosters (2002+)
- injuries (2009+)
- depth charts (2001+)
- snap counts (2012+)
- Next Gen Stats passing/receiving/rushing (2016+)

The installer makes no network calls. Downloads only happen when `loader.py` is run.

List datasets:
`python3 data_vault/loader.py --list`

Recommended first bootstrap:
`python3 data_vault/loader.py --dataset players`
`python3 data_vault/loader.py --dataset injuries --dataset depth_charts --dataset snap_counts --seasons 2024 2025 2026`
`python3 data_vault/loader.py --dataset ngs_passing --dataset ngs_receiving --dataset ngs_rushing`

Play-by-play is larger:
`python3 data_vault/loader.py --dataset pbp --seasons 2024 2025 2026`

Raw files cache under `data_vault/raw/`. Re-running without `--force` leaves existing files alone.

Next build after we confirm these files:
1. schedules + historical market normalization
2. one-row-per-game master table
3. team efficiency features
4. player usage/matchup features
5. historical comp index
