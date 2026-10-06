#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import math
import re
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "markets"
TIMELINE = OUT / "GAME_MARKET_CONSENSUS_TIMELINE.csv"
MOVEMENT = OUT / "GAME_MARKET_MOVEMENT_CURRENT.csv"
CLOSES = OUT / "GAME_MARKET_CLOSES.csv"
LEDGER = OUT / "MARKET_SNAPSHOT_LEDGER.csv"
CATALOG = OUT / "MARKET_SOURCE_CATALOG.csv"
RECEIPT = OUT / "MARKET_LIFECYCLE_RECEIPT.json"
NOW_TS = pd.Timestamp.now(tz="UTC")
NOW = datetime.now(timezone.utc).isoformat()

SPORT_PATHS = {
    "NFL": ("nfl_live/game_fusion/history", "NFL_GAME_SPORTWIZZARD_*.csv"),
    "NBA": ("nba_live/markets/history", "NBA_GAME_MARKET_*.csv"),
    "NHL": ("nhl_live/markets/history", "NHL_GAME_MARKET_*.csv"),
    "MLB": ("mlb_live/markets/history", "MLB_GAME_MARKET_*.csv"),
    "CFB": ("cfb_live/markets/history", "CFB_GAME_MARKET_*.csv"),
    "CBB": ("cbb_live/markets/history", "CBB_GAME_MARKET_*.csv"),
}

BASE_COLS = [
    "provider","sportsbook","event_id","start","away_team","home_team",
    "market","market_subtype","selection","side","line","price_american",
]

def read(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

def read_market(path):
    try:
        return pd.read_csv(
            path, usecols=lambda c: c in BASE_COLS, low_memory=False
        )
    except Exception:
        return pd.DataFrame()

def clean(v):
    if v is None or (isinstance(v,float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+"," ",str(v).strip())

def num(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def parse_stamp(path):
    m = re.search(r"(20\d{6}T\d{6}Z)", path.name)
    if not m:
        return pd.NaT
    return pd.to_datetime(m.group(1), format="%Y%m%dT%H%M%SZ", utc=True)

def american_prob(v):
    p = num(v)
    if p is None or p == 0:
        return None
    if p < 0:
        return (-p)/((-p)+100)
    return 100/(p+100)

def most_common(series):
    s = series.dropna().astype(str)
    if s.empty:
        return ""
    return s.value_counts().index[0]

def discover():
    rows = []
    for sport,(rel,pattern) in SPORT_PATHS.items():
        folder = ROOT/rel
        for path in sorted(folder.glob(pattern)):
            rows.append({
                "sport":sport,
                "path":str(path.relative_to(ROOT)),
                "snapshot_at":parse_stamp(path),
                "bytes":path.stat().st_size,
            })
    return pd.DataFrame(rows)

def processed_paths():
    if not LEDGER.exists():
        return set()
    d = read(LEDGER)
    if d.empty or "path" not in d:
        return set()
    return set(d.path.astype(str))

def normalize_snapshot(meta):
    path = ROOT/meta["path"]
    d = read_market(path)
    if d.empty:
        return pd.DataFrame(), 0
    for c in BASE_COLS:
        if c not in d:
            d[c] = pd.NA
    d = d[BASE_COLS].copy()
    d["sport"] = meta["sport"]
    d["snapshot_at"] = meta["snapshot_at"]
    d["start"] = pd.to_datetime(d["start"],utc=True,errors="coerce")
    d["line"] = pd.to_numeric(d["line"],errors="coerce")
    d["price_american"] = pd.to_numeric(d["price_american"],errors="coerce")
    for c in ["provider","sportsbook","event_id","away_team","home_team",
              "market","market_subtype","selection","side"]:
        d[c] = d[c].fillna("").astype(str).str.strip()
    d = d[d.event_id.ne("") & d.market.ne("")]
    if d.empty:
        return pd.DataFrame(), 0
    d["selection_key"] = d["side"].where(d["side"].ne(""),d["selection"])
    keys = [
        "sport","snapshot_at","event_id",
        "market","market_subtype","selection_key",
    ]
    g = d.groupby(keys,dropna=False,as_index=False).agg(
        start=("start","min"),
        away_team=("away_team",most_common),
        home_team=("home_team",most_common),
        selection=("selection",most_common),
        consensus_line=("line","median"),
        consensus_price_american=("price_american","median"),
        sportsbook_count=("sportsbook",lambda x:x[x.ne("")].nunique()),
        provider_count=("provider",lambda x:x[x.ne("")].nunique()),
        raw_quote_count=("event_id","size"),
        start_variant_count=("start","nunique"),
    )
    g["hours_to_start"] = (
        (g["start"]-g["snapshot_at"]).dt.total_seconds()/3600
    )
    g["captured_before_start"] = g["hours_to_start"].ge(0)
    return g, len(d)

def append_csv(path, d):
    if d.empty:
        return
    exists = path.exists() and path.stat().st_size > 0
    d.to_csv(path,index=False,mode="a" if exists else "w",header=not exists)

def choose_files(discovered, backfill):
    seen = processed_paths()
    d = discovered[discovered.snapshot_at.notna()].copy()
    d = d.sort_values(["sport","snapshot_at"])
    if d.empty:
        return d
    if not backfill:
        latest = d.groupby("sport",as_index=False).tail(1)
        return latest[~latest.path.isin(seen)].copy()
    if backfill:
        d["bucket"] = d.snapshot_at.dt.floor("1h")
        covered = set()
        if LEDGER.exists():
            old = read(LEDGER)
            if not old.empty and {"sport","snapshot_at","sampling_cadence"}.issubset(old.columns):
                old = old[old.sampling_cadence.eq("hourly_backfill")].copy()
                old["snapshot_at"] = pd.to_datetime(old.snapshot_at,utc=True,errors="coerce")
                old["bucket"] = old.snapshot_at.dt.floor("1h")
                covered = set(zip(old.sport.astype(str),old.bucket))
        if covered:
            mask = [
                (sport,bucket) not in covered
                for sport,bucket in zip(d.sport.astype(str),d.bucket)
            ]
            d = d[mask]
        if d.empty:
            return d
        return d.groupby(
            ["sport","bucket"],as_index=False
        ).tail(1)
    return d.groupby(
        "sport",as_index=False
    ).tail(1)

def process_files(chosen, backfill):
    ledger_rows = []
    for _, meta in chosen.iterrows():
        g, raw_rows = normalize_snapshot(meta)
        if not g.empty:
            append_csv(TIMELINE,g)
        row = {
            "sport":meta.sport,
            "path":meta.path,
            "snapshot_at":meta.snapshot_at.isoformat(),
            "bytes":int(meta.bytes),
            "raw_rows":int(raw_rows),
            "consensus_rows":int(len(g)),
            "processed_at":NOW,
            "sampling_cadence":(
                "hourly_backfill" if backfill else "latest_per_refresh"
            ),
        }
        append_csv(LEDGER,pd.DataFrame([row]))
        ledger_rows.append(row)
    return ledger_rows

def load_timeline():
    d = read(TIMELINE)
    if d.empty:
        return d
    d["snapshot_at"] = pd.to_datetime(
        d["snapshot_at"],utc=True,errors="coerce"
    )
    d["start"] = pd.to_datetime(
        d["start"],utc=True,errors="coerce"
    )
    d["consensus_line"] = pd.to_numeric(
        d["consensus_line"],errors="coerce"
    )
    d["consensus_price_american"] = pd.to_numeric(
        d["consensus_price_american"],errors="coerce"
    )
    d = d.drop_duplicates([
        "sport","snapshot_at","event_id","market",
        "market_subtype","selection_key"
    ],keep="last")
    return d

def move_signal(obs, line_delta, prob_delta):
    if obs < 2:
        return "LIMITED_SAMPLE"
    lm = abs(line_delta) if line_delta is not None else 0
    pm = abs(prob_delta) if prob_delta is not None else 0
    if lm >= 1 or pm >= 4:
        return "MATERIAL_MARKET_MOVE"
    if lm >= 0.25 or pm >= 2:
        return "MARKET_MOVE"
    return "STABLE"

def lifecycle_views(timeline):
    if timeline.empty:
        return pd.DataFrame(), pd.DataFrame()
    keys = [
        "sport","event_id","market",
        "market_subtype","selection_key"
    ]
    moves = []
    closes = []
    for key, g in timeline.groupby(keys,dropna=False):
        g = g.sort_values("snapshot_at")
        first = g.iloc[0]
        last = g.iloc[-1]
        p0 = american_prob(first.consensus_price_american)
        p1 = american_prob(last.consensus_price_american)
        line0 = num(first.consensus_line)
        line1 = num(last.consensus_line)
        if line0 is not None and line1 is not None:
            line_delta = line1-line0
        else:
            line_delta = None
        if p0 is not None and p1 is not None:
            prob_delta = (p1-p0)*100
        else:
            prob_delta = None
        start = first.start
        obs = int(g.snapshot_at.nunique())
        moves.append({
            "sport":key[0],
            "event_id":key[1],
            "market":key[2],
            "market_subtype":key[3],
            "selection_key":key[4],
            "selection":clean(last.selection),
            "away_team":clean(last.away_team),
            "home_team":clean(last.home_team),
            "start":start.isoformat() if pd.notna(start) else "",
            "first_seen":first.snapshot_at.isoformat(),
            "latest_seen":last.snapshot_at.isoformat(),
            "observations":obs,
            "opening_line":line0,
            "latest_line":line1,
            "line_move":line_delta,
            "opening_price_american":num(first.consensus_price_american),
            "latest_price_american":num(last.consensus_price_american),
            "market_implied_prob_move_pp":prob_delta,
            "movement_signal":move_signal(obs,line_delta,prob_delta),
            "latest_sportsbook_count":int(last.sportsbook_count),
            "latest_provider_count":int(last.provider_count),
            "latest_is_poststart":bool(pd.notna(start) and last.snapshot_at>start),
            "score_is_model_probability":False,
        })
        if pd.notna(start) and start <= NOW_TS:
            pre = g[g.snapshot_at.le(start)]
            if len(pre):
                opening = pre.iloc[0]
                closing = pre.iloc[-1]
                op = american_prob(opening.consensus_price_american)
                cp = american_prob(closing.consensus_price_american)
                ol = num(opening.consensus_line)
                cl = num(closing.consensus_line)
                age_min = round(
                    (start-closing.snapshot_at).total_seconds()/60,2
                )
                if age_min <= 30:
                    close_quality = "TIGHT_CLOSE"
                elif age_min <= 120:
                    close_quality = "USABLE_CLOSE"
                else:
                    close_quality = "STALE_LAST_OBSERVATION"
                closes.append({
                    "sport":key[0], "event_id":key[1],
                    "market":key[2], "market_subtype":key[3],
                    "selection_key":key[4],
                    "selection":clean(closing.selection),
                    "start":start.isoformat(),
                    "opening_seen":opening.snapshot_at.isoformat(),
                    "closing_seen":closing.snapshot_at.isoformat(),
                    "opening_line":ol, "closing_line":cl,
                    "line_move_to_close":(
                        cl-ol if cl is not None and ol is not None else None
                    ),
                    "opening_price_american":num(opening.consensus_price_american),
                    "closing_price_american":num(closing.consensus_price_american),
                    "market_implied_prob_move_to_close_pp":(
                        (cp-op)*100
                        if cp is not None and op is not None else None
                    ),
                    "close_age_minutes":age_min,
                    "close_quality":close_quality,
                    "pregame_observations":int(len(pre)),
                    "closing_sportsbook_count":int(closing.sportsbook_count),
                    "closing_provider_count":int(closing.provider_count),
                    "close_is_last_observed_pregame":True,
                    "score_is_model_probability":False,
                })
    return pd.DataFrame(moves), pd.DataFrame(closes)

def write_views(timeline):
    movement, closes = lifecycle_views(timeline)
    movement.to_csv(MOVEMENT,index=False)
    closes.to_csv(CLOSES,index=False)
    return movement, closes

def build_catalog(discovered, timeline):
    rows = []
    for sport,(rel,pattern) in SPORT_PATHS.items():
        files = discovered[discovered.sport.eq(sport)]
        t = timeline[timeline.sport.eq(sport)] if not timeline.empty else pd.DataFrame()
        status = "LIVE" if len(t) else (
            "NO_LIVE_ROWS_YET" if len(files) else "NO_FILES"
        )
        first_seen = (
            t.snapshot_at.min().isoformat() if len(t) else ""
        )
        last_seen = (
            t.snapshot_at.max().isoformat() if len(t) else ""
        )
        rows.append({
            "sport":sport,
            "source_directory":rel,
            "raw_snapshot_files":int(len(files)),
            "consensus_timeline_rows":int(len(t)),
            "first_consensus_seen":first_seen,
            "last_consensus_seen":last_seen,
            "status":status,
            "sampling_policy":"backfill<=1 snapshot/hour; live=latest/content refresh",
            "game_markets_only":True,
            "player_props_included":False,
            "generated_at":NOW,
        })
    d = pd.DataFrame(rows)
    d.to_csv(CATALOG,index=False)
    return d

def receipt_data(chosen_rows, timeline, movement, closes, catalog):
    return {
        "generated_at":NOW,
        "new_snapshot_files_processed":int(len(chosen_rows)),
        "new_snapshot_files_by_sport":(
            pd.DataFrame(chosen_rows).sport.value_counts().astype(int).to_dict()
            if chosen_rows else {}
        ),
        "consensus_timeline_rows":int(len(timeline)),
        "timeline_rows_by_sport":(
            timeline.sport.value_counts().astype(int).to_dict()
            if len(timeline) else {}
        ),
        "movement_rows":int(len(movement)),
        "movement_signal_counts":(
            movement.movement_signal.value_counts().astype(int).to_dict()
            if len(movement) else {}
        ),
        "frozen_close_rows":int(len(closes)),
        "close_rows_by_sport":(
            closes.sport.value_counts().astype(int).to_dict()
            if len(closes) else {}
        ),
        "close_quality_counts":(
            closes.close_quality.value_counts().astype(int).to_dict()
            if len(closes) else {}
        ),
        "source_catalog":catalog[
            ["sport","raw_snapshot_files","status"]
        ].to_dict("records"),
        "american_price_delta_is_probability":False,
        "market_implied_probability_is_model_probability":False,
        "automatic_model_adjustment":False,
        "player_props_included":False,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill",action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)

    discovered = discover()
    chosen = choose_files(discovered,args.backfill)
    ledger_rows = process_files(chosen,args.backfill)
    timeline = load_timeline()
    movement, closes = write_views(timeline)
    catalog = build_catalog(discovered,timeline)
    receipt = receipt_data(
        ledger_rows,timeline,movement,closes,catalog
    )
    RECEIPT.write_text(
        json.dumps(receipt,indent=2,sort_keys=True)
    )

    print("NEW SNAPSHOTS:",receipt["new_snapshot_files_processed"])
    print("TIMELINE:",receipt["consensus_timeline_rows"])
    print("MOVEMENT:",receipt["movement_rows"],
          receipt["movement_signal_counts"])
    print("FROZEN CLOSES:",receipt["frozen_close_rows"],
          receipt["close_rows_by_sport"])
    print("RESULT: MARKET_LIFECYCLE_READY")

if __name__ == "__main__":
    main()
