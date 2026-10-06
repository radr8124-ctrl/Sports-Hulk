#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "intelligence_warehouse" / "fantasy_decisions"
PUBLIC_OUT = ROOT / "commercial_web" / "public" / "fantasy_decisions.json"
DIST_OUT = ROOT / "commercial_web" / "dist" / "fantasy_decisions.json"

FILES = {
    "weekly": SRC / "FANTASY_WEEKLY_DECISIONS_CURRENT.csv",
    "faab": SRC / "FANTASY_FAAB_RESEARCH_CURRENT.csv",
    "ir_stash": SRC / "FANTASY_IR_STASH_CURRENT.csv",
    "defense_streaming": SRC / "FANTASY_DEFENSE_STREAMING_CURRENT.csv",
    "idp": SRC / "FANTASY_IDP_OPPORTUNITY_CURRENT.csv",
}

KEEP = {
    "weekly": [
        "generated_at","sport","player","team","position","opponent","role_signal","snap_pct",
        "availability_status","future_schedule_signal","weekly_research_score","weekly_tier",
        "ros_research_score","ros_tier","research_reasons","score_is_probability",
        "personal_roster_context_used","fantasy_points_projection_used",
    ],
    "faab": [
        "generated_at","sport","player","team","position","availability_status","market_activity_signal",
        "adds_24h","net_adds_24h","role_signal","waiver_research_score","waiver_priority",
        "suggested_faab_low_pct","suggested_faab_high_pct","faab_is_market_prediction","score_is_probability",
    ],
    "ir_stash": [
        "generated_at","sport","player","team","position","status","injury_type","return_date","return_window",
        "source_count","source_disagreement","role_signal","stash_research_score","stash_tier",
        "return_date_is_guarantee","score_is_probability",
    ],
    "defense_streaming": [
        "generated_at","sport","team","dst_player","next_opponent","next_side","rest_days",
        "future_schedule_signal","market_data_available","market_activity_signal","weekly_stream_score",
        "weekly_stream_tier","multiweek_hold_score","multiweek_hold_tier","score_is_probability",
    ],
    "idp": [
        "generated_at","sport","player","team","position","idp_group","snap_pct","snap_pct_change",
        "role_signal","availability_status","injury_type","next_opponent","idp_usage_score","idp_usage_tier",
        "fantasy_points_projection_available","waiver_market_coverage_available","score_is_probability",
    ],
}

SORT = {
    "weekly": "weekly_research_score",
    "faab": "waiver_research_score",
    "ir_stash": "stash_research_score",
    "defense_streaming": "weekly_stream_score",
    "idp": "idp_usage_score",
}

LIMIT = 60

def clean_records(frame: pd.DataFrame) -> list[dict]:
    safe = frame.astype(object).where(pd.notna(frame), None)
    return safe.to_dict(orient="records")

payload = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "status": "READY",
    "personalization": {
        "league_connected": False,
        "roster_connected": False,
        "scoring_connected": False,
        "status": "GENERIC_RESEARCH_ONLY",
        "note": "Personal league, roster and scoring context are not connected to this commercial session yet.",
    },
    "lanes": {},
}

for lane, path in FILES.items():
    if not path.exists():
        payload["lanes"][lane] = {"status": "MISSING", "rows": [], "source_rows": 0}
        continue

    df = pd.read_csv(path, low_memory=False)
    source_rows = len(df)
    sort_col = SORT[lane]
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=False, na_position="last")
    cols = [c for c in KEEP[lane] if c in df.columns]
    df = df[cols].head(LIMIT)

    payload["lanes"][lane] = {
        "status": "READY",
        "source_rows": source_rows,
        "rows": clean_records(df),
    }

rendered = json.dumps(payload, indent=2, allow_nan=False)
for out in (PUBLIC_OUT, DIST_OUT):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(rendered)
    tmp.replace(out)

print(json.dumps({
    "status": "READY",
    "outputs": [str(PUBLIC_OUT), str(DIST_OUT)],
    "counts": {lane: block["source_rows"] for lane, block in payload["lanes"].items()},
}, indent=2))
