#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import shutil
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT/"intelligence_warehouse"/"markets"
LEDGER = OUT/"MARKET_SNAPSHOT_LEDGER.csv"
TIMELINE = OUT/"GAME_MARKET_CONSENSUS_TIMELINE.csv"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
BACKUP = OUT/f"repair_backup_{STAMP}"
BACKUP.mkdir(parents=True,exist_ok=True)

for path in [LEDGER,TIMELINE]:
    if path.exists():
        shutil.copy2(path,BACKUP/path.name)

ledger = pd.read_csv(LEDGER,low_memory=False)
ledger["snapshot_at"] = pd.to_datetime(
    ledger.snapshot_at,utc=True,errors="coerce"
)
hourly = ledger[ledger.sampling_cadence.eq("hourly_backfill")].copy()
latest = ledger[ledger.sampling_cadence.eq("latest_per_refresh")].copy()
other = ledger[
    ~ledger.sampling_cadence.isin(["hourly_backfill","latest_per_refresh"])
].copy()

hourly["bucket"] = hourly.snapshot_at.dt.floor("1h")
hourly = hourly.sort_values(
    ["sport","bucket","snapshot_at"]
).groupby(["sport","bucket"],as_index=False).tail(1)
hourly = hourly.drop(columns=["bucket"])

latest["processed_at_dt"] = pd.to_datetime(
    latest.processed_at,utc=True,errors="coerce"
)
latest = latest.sort_values(["sport","processed_at_dt","snapshot_at"])
latest_kept = []
for sport,g in latest.groupby("sport",sort=False):
    high = pd.NaT
    for idx,row in g.iterrows():
        snap = row.snapshot_at
        if pd.isna(snap):
            continue
        if pd.isna(high) or snap > high:
            latest_kept.append(idx)
            high = snap
latest = latest.loc[latest_kept].drop(columns=["processed_at_dt"])

kept = pd.concat([other,hourly,latest],ignore_index=True)
kept = kept.sort_values(["sport","snapshot_at","sampling_cadence"])
kept["snapshot_at"] = kept.snapshot_at.map(
    lambda x:x.isoformat() if pd.notna(x) else ""
)
kept.to_csv(LEDGER,index=False)

allowed = set(
    zip(
        kept.sport.astype(str),
        pd.to_datetime(kept.snapshot_at,utc=True,errors="coerce")
    )
)
timeline = pd.read_csv(TIMELINE,low_memory=False)
timeline["snapshot_at"] = pd.to_datetime(
    timeline.snapshot_at,utc=True,errors="coerce"
)
mask = [
    (sport,snap) in allowed
    for sport,snap in zip(timeline.sport.astype(str),timeline.snapshot_at)
]
timeline = timeline[mask].copy()
keys = [
    "sport","snapshot_at","event_id","market",
    "market_subtype","selection_key"
]
timeline = timeline.drop_duplicates(keys,keep="last")
timeline["snapshot_at"] = timeline.snapshot_at.map(
    lambda x:x.isoformat() if pd.notna(x) else ""
)
timeline.to_csv(TIMELINE,index=False)

print("LEDGER_ROWS_BEFORE:",len(ledger))
print("LEDGER_ROWS_AFTER:",len(kept))
print("HOURLY_ROWS_AFTER:",len(hourly))
print("TIMELINE_ROWS_AFTER:",len(timeline))
print("BACKUP:",BACKUP)
print("RESULT: MARKET_SAMPLING_REPAIRED")
