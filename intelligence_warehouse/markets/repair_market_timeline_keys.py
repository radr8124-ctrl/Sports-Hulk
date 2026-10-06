#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import shutil
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT/"intelligence_warehouse"/"markets"
P = OUT/"GAME_MARKET_CONSENSUS_TIMELINE.csv"
STAMP = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
BACKUP = OUT/f"timeline_key_backup_fast_{STAMP}.csv"
shutil.copy2(P,BACKUP)

d = pd.read_csv(P,low_memory=False)
d["snapshot_at"] = pd.to_datetime(d.snapshot_at,utc=True,errors="coerce")
d["start"] = pd.to_datetime(d.start,utc=True,errors="coerce")
for c in ["consensus_line","consensus_price_american","raw_quote_count",
          "sportsbook_count","provider_count","start_variant_count"]:
    if c not in d:
        d[c] = 1 if c in {"raw_quote_count","start_variant_count"} else pd.NA
    d[c] = pd.to_numeric(d[c],errors="coerce")

keys=[
    "sport","snapshot_at","event_id",
    "market","market_subtype","selection_key"
]
dup = d.duplicated(keys,keep=False)
singles = d[~dup].copy()
x = d[dup].copy()
if len(x):
    x["_w"] = x.raw_quote_count.fillna(1).clip(lower=1,upper=50).round().astype(int)
    expanded = x.loc[x.index.repeat(x["_w"])].copy()
    med = expanded.groupby(keys,dropna=False).agg(
        consensus_line=("consensus_line","median"),
        consensus_price_american=("consensus_price_american","median"),
    ).reset_index()
    meta = x.sort_values(
        ["raw_quote_count"],ascending=False
    ).drop_duplicates(keys).copy()
    meta = meta[keys+[
        "away_team","home_team","selection"
    ]]
    stats = x.groupby(keys,dropna=False).agg(
        start=("start","min"),
        sportsbook_count=("sportsbook_count","max"),
        provider_count=("provider_count","max"),
        raw_quote_count=("raw_quote_count","sum"),
        source_start_variants=("start","nunique"),
        prior_start_variant_count=("start_variant_count","max"),
    ).reset_index()
    agg = stats.merge(meta,on=keys,how="left").merge(med,on=keys,how="left")
    agg["start_variant_count"] = agg[[
        "source_start_variants","prior_start_variant_count"
    ]].max(axis=1).fillna(1).astype(int)
    agg = agg.drop(columns=["source_start_variants","prior_start_variant_count"])
    agg["hours_to_start"] = (
        agg.start-agg.snapshot_at
    ).dt.total_seconds()/3600
    agg["captured_before_start"] = agg.hours_to_start.ge(0)
    out = pd.concat([singles,agg],ignore_index=True,sort=False)
else:
    out = singles

out = out.drop_duplicates(keys,keep="last")
out = out.sort_values(keys)
out["snapshot_at"] = out.snapshot_at.map(
    lambda x:x.isoformat() if pd.notna(x) else ""
)
out["start"] = out.start.map(
    lambda x:x.isoformat() if pd.notna(x) else ""
)
out.to_csv(P,index=False)

print("ROWS_BEFORE:",len(d))
print("DUP_ROWS_BEFORE:",int(dup.sum()))
print("ROWS_AFTER:",len(out))
print("DUP_KEYS_AFTER:",int(out.duplicated(keys).sum()))
print("START_VARIANT_ROWS:",int((pd.to_numeric(
    out.start_variant_count,errors="coerce"
).fillna(1)>1).sum()))
print("BACKUP:",BACKUP)
print("RESULT: MARKET_TIMELINE_KEYS_REPAIRED")
