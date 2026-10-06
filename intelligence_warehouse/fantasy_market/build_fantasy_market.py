#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "fantasy_market"
RAW = OUT / "raw"
TREND_OUT = OUT / "FANTASY_MARKET_TRENDS_CURRENT.csv"
CONTEXT_OUT = OUT / "FANTASY_MARKET_CONTEXT_CURRENT.csv"
SOURCE_OUT = OUT / "FANTASY_MARKET_SOURCE_CATALOG.csv"
RECEIPT = OUT / "FANTASY_MARKET_RECEIPT.json"

AVAILABILITY = ROOT / "intelligence_warehouse" / "availability" / "AVAILABILITY_CURRENT.csv"
RETURN_WATCH = ROOT / "intelligence_warehouse" / "availability" / "RETURN_WATCH.csv"
ROLE_SIGNALS = ROOT / "intelligence_warehouse" / "features" / "PLAYER_ROLE_SIGNALS_CURRENT.csv"

SPORTS = ("NFL", "NBA", "NHL", "MLB")
LOOKBACKS = (24, 168)
KINDS = ("add", "drop")
HEADERS = {"User-Agent": "Sports-HULK/1.0 fantasy-market research"}
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

def player_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
def read_csv(path):
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def cached_players(sport):
    path = RAW / f"{sport.lower()}_players.json"
    age_hours = (time.time() - path.stat().st_mtime) / 3600 if path.exists() else None
    if path.exists() and age_hours is not None and age_hours < 6:
        return json.loads(path.read_text()), "CACHE"
    url = f"https://api.sleeper.app/v1/players/{sport.lower()}"
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    data = response.json()
    path.write_text(json.dumps(data, separators=(",", ":")))
    return data, "LIVE"

def fetch_trend(sport, kind, hours):
    url = (
        f"https://api.sleeper.app/v1/players/{sport.lower()}/trending/{kind}"
        f"?lookback_hours={hours}&limit=250"
    )
    response = requests.get(url, headers=HEADERS, timeout=8)
    response.raise_for_status()
    data = response.json()
    path = RAW / f"{sport.lower()}_{kind}_{hours}h.json"
    path.write_text(json.dumps(data, separators=(",", ":")))
    return data

def fetch_sport(sport):
    directory, directory_source = cached_players(sport)
    trends = {}
    for hours in LOOKBACKS:
        for kind in KINDS:
            trends[(kind, hours)] = fetch_trend(sport, kind, hours)
    return sport, directory, directory_source, trends

def rank_map(rows):
    out = {}
    for idx, row in enumerate(rows, start=1):
        pid = str(row.get("player_id") or "")
        if pid:
            out[pid] = {"rank": idx, "count": int(row.get("count") or 0)}
    return out
def clean_external_id(value):
    if value is None or value == "":
        return ""
    try:
        return str(int(value))
    except Exception:
        return str(value).strip()

errors = []
payloads = {}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(fetch_sport, sport): sport for sport in SPORTS}
    for future in as_completed(futures):
        sport = futures[future]
        try:
            got_sport, directory, directory_source, trends = future.result()
            payloads[got_sport] = {
                "directory": directory,
                "directory_source": directory_source,
                "trends": trends,
            }
        except Exception as exc:
            errors.append({"sport": sport, "error": repr(exc)})

generated_at = datetime.now(timezone.utc).isoformat()
trend_rows = []
source_rows = []

for sport in SPORTS:
    payload = payloads.get(sport, {})
    directory = payload.get("directory", {})
    trends = payload.get("trends", {})
    maps = {
        (kind, hours): rank_map(trends.get((kind, hours), []))
        for hours in LOOKBACKS for kind in KINDS
    }
    player_ids = set()
    for mapping in maps.values():
        player_ids.update(mapping)

    for pid in sorted(player_ids):
        meta = directory.get(pid, {}) if isinstance(directory, dict) else {}
        a24 = maps[("add", 24)].get(pid, {})
        d24 = maps[("drop", 24)].get(pid, {})
        a168 = maps[("add", 168)].get(pid, {})
        d168 = maps[("drop", 168)].get(pid, {})
        full_name = meta.get("full_name") or meta.get("search_full_name") or ""
        team = meta.get("team") or ""
        position = meta.get("position") or ""
        if not full_name and sport == "NFL" and pid.isalpha():
            full_name = f"{pid} D/ST"
            team = pid
            position = "DEF"

        adds24 = int(a24.get("count") or 0)
        drops24 = int(d24.get("count") or 0)
        adds168 = int(a168.get("count") or 0)
        drops168 = int(d168.get("count") or 0)
        add_pace = round(adds24 / (adds168 / 7), 3) if adds168 else None
        drop_pace = round(drops24 / (drops168 / 7), 3) if drops168 else None
        add_rank = a24.get("rank")
        drop_rank = d24.get("rank")
        if add_rank and drop_rank and add_rank <= 25 and drop_rank <= 25:
            signal = "TOP_ADD_AND_DROP_ACTIVITY"
        elif add_rank and add_rank <= 25:
            signal = "TOP_25_ADD_ACTIVITY"
        elif drop_rank and drop_rank <= 25:
            signal = "TOP_25_DROP_ACTIVITY"
        elif add_rank and drop_rank:
            signal = "ADD_AND_DROP_ACTIVITY"
        elif add_rank:
            signal = "ADD_ACTIVITY"
        elif drop_rank:
            signal = "DROP_ACTIVITY"
        else:
            signal = "SEVEN_DAY_ACTIVITY_ONLY"

        trend_rows.append({
            "sport": sport,
            "sleeper_player_id": pid,
            "espn_id": clean_external_id(meta.get("espn_id")),
            "player": full_name,
            "player_key": player_key(full_name),
            "team": team,
            "position": position,
            "active": meta.get("active"),
            "player_status": meta.get("status"),
            "source_injury_status": meta.get("injury_status"),
            "adds_24h": adds24,
            "add_rank_24h": add_rank,
            "drops_24h": drops24,
            "drop_rank_24h": drop_rank,
            "net_adds_24h": adds24 - drops24,
            "adds_168h": adds168,
            "add_rank_168h": a168.get("rank"),
            "drops_168h": drops168,
            "drop_rank_168h": d168.get("rank"),
            "net_adds_168h": adds168 - drops168,
            "add_pace_vs_7d_daily": add_pace,
            "drop_pace_vs_7d_daily": drop_pace,
            "market_activity_signal": signal,
            "trend_feed_rank_limited": True,
            "generated_at": generated_at,
            "score_is_probability": False,
            "automatic_model_adjustment": False,
        })

    counts = {
        f"{kind}_{hours}h_rows": len(trends.get((kind, hours), []))
        for hours in LOOKBACKS for kind in KINDS
    }
    source_rows.append({
        "sport": sport,
        "provider": "SLEEPER_PUBLIC",
        "player_directory_rows": len(directory) if isinstance(directory, dict) else 0,
        "player_directory_source": payload.get("directory_source", "ERROR"),
        **counts,
        "trend_status": "LIVE_ACTIVITY" if player_ids else "NO_TREND_ROWS",
        "trend_limit_per_list": 100,
        "ownership_percentage_available": False,
        "faab_bid_data_available": False,
        "private_league_data_used": False,
        "generated_at": generated_at,
    })

trends_df = pd.DataFrame(trend_rows)
source_df = pd.DataFrame(source_rows)
availability_df = read_csv(AVAILABILITY)
return_df = read_csv(RETURN_WATCH)
role_df = read_csv(ROLE_SIGNALS)

availability_lookup = {}
availability_key_lookup = {}
availability_key_counts = {}
for row in availability_df.to_dict("records") if not availability_df.empty else []:
    sport = str(row.get("sport") or "").upper()
    external_key = (sport, clean_external_id(row.get("player_id")))
    normalized_key = (sport, str(row.get("player_key") or ""))
    availability_lookup[external_key] = row
    availability_key_counts[normalized_key] = availability_key_counts.get(normalized_key, 0) + 1
    availability_key_lookup[normalized_key] = row

return_lookup = {}
return_key_lookup = {}
return_key_counts = {}
for row in return_df.to_dict("records") if not return_df.empty else []:
    sport = str(row.get("sport") or "").upper()
    external_key = (sport, clean_external_id(row.get("player_id")))
    normalized_key = (sport, str(row.get("player_key") or ""))
    return_lookup[external_key] = row
    return_key_counts[normalized_key] = return_key_counts.get(normalized_key, 0) + 1
    return_key_lookup[normalized_key] = row

role_lookup = {}
for row in role_df.to_dict("records") if not role_df.empty else []:
    key = (str(row.get("sport") or "").upper(), str(row.get("player_key") or ""))
    role_lookup[key] = row

context_rows = []
for row in trends_df.to_dict("records") if not trends_df.empty else []:
    sport = row["sport"]
    espn_id = clean_external_id(row.get("espn_id"))
    pkey = row.get("player_key") or ""
    availability = availability_lookup.get((sport, espn_id), {}) if espn_id else {}
    availability_join_method = "ESPN_ID" if availability else None
    normalized_lookup_key = (sport, pkey)
    if not availability and pkey and availability_key_counts.get(normalized_lookup_key) == 1:
        availability = availability_key_lookup.get(normalized_lookup_key, {})
        availability_join_method = "PLAYER_KEY" if availability else None

    return_state = return_lookup.get((sport, espn_id), {}) if espn_id else {}
    return_join_method = "ESPN_ID" if return_state else None
    if not return_state and pkey and return_key_counts.get(normalized_lookup_key) == 1:
        return_state = return_key_lookup.get(normalized_lookup_key, {})
        return_join_method = "PLAYER_KEY" if return_state else None

    role = role_lookup.get((sport, pkey), {})
    stash_raw = return_state.get("stash_research_signal")
    stash = str(stash_raw).strip().lower() in {"true", "1", "yes"}
    adds24 = int(row.get("adds_24h") or 0)
    drops24 = int(row.get("drops_24h") or 0)
    role_signal = role.get("signal") or ""

    if stash and adds24 > 0:
        combined = "RETURN_WATCH_WITH_ADD_ACTIVITY"
    elif role_signal == "ROLE_UP" and adds24 > 0:
        combined = "ROLE_UP_WITH_ADD_ACTIVITY"
    elif availability and drops24 > 0:
        combined = "AVAILABILITY_CONTEXT_WITH_DROP_ACTIVITY"
    elif adds24 > 0 or drops24 > 0:
        combined = "MARKET_ACTIVITY_ONLY"
    else:
        combined = "SEVEN_DAY_ACTIVITY_ONLY"

    context_rows.append({
        **row,
        "availability_join_method": availability_join_method,
        "availability_status": availability.get("status_normalized"),
        "availability_injury_type": availability.get("injury_type"),
        "availability_return_date": availability.get("return_date"),
        "availability_source_disagreement": availability.get("source_disagreement"),
        "return_join_method": return_join_method,
        "return_window": return_state.get("return_window"),
        "stash_research_signal": return_state.get("stash_research_signal"),
        "role_signal": role_signal or None,
        "role_delta": role.get("role_delta"),
        "role_score": role.get("role_score"),
        "combined_research_context": combined,
    })

context_df = pd.DataFrame(context_rows)
trends_df.to_csv(TREND_OUT, index=False)
context_df.to_csv(CONTEXT_OUT, index=False)
source_df.to_csv(SOURCE_OUT, index=False)

if not context_df.empty:
    join_availability = int(context_df["availability_status"].notna().sum())
    join_role = int(context_df["role_signal"].notna().sum())
    stash_add = int((context_df["combined_research_context"] == "RETURN_WATCH_WITH_ADD_ACTIVITY").sum())
    role_add = int((context_df["combined_research_context"] == "ROLE_UP_WITH_ADD_ACTIVITY").sum())
    signal_counts = context_df["market_activity_signal"].value_counts().to_dict()
    combined_counts = context_df["combined_research_context"].value_counts().to_dict()
else:
    join_availability = join_role = stash_add = role_add = 0
    signal_counts = {}
    combined_counts = {}

receipt = {
    "generated_at": generated_at,
    "provider": "SLEEPER_PUBLIC",
    "sports_requested": list(SPORTS),
    "sports_with_live_trend_rows": source_df.loc[
        source_df["trend_status"] == "LIVE_ACTIVITY", "sport"
    ].tolist() if not source_df.empty else [],
    "sports_without_trend_rows": source_df.loc[
        source_df["trend_status"] == "NO_TREND_ROWS", "sport"
    ].tolist() if not source_df.empty else [],
    "trend_rows": len(trends_df),
    "context_rows": len(context_df),
    "trend_rows_by_sport": trends_df["sport"].value_counts().to_dict() if not trends_df.empty else {},
    "market_activity_signal_counts": signal_counts,
    "combined_context_counts": combined_counts,
    "availability_context_matches": join_availability,
    "role_context_matches": join_role,
    "return_watch_with_add_activity": stash_add,
    "role_up_with_add_activity": role_add,
    "trend_list_limit": 100,
    "lookback_hours": list(LOOKBACKS),
    "ownership_percentage_available": False,
    "faab_bid_data_available": False,
    "private_league_data_used": False,
    "historical_snapshots_via_hourly_warehouse": True,
    "player_directory_cache_ttl_hours": 6,
    "paid_provider_required": False,
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "errors": errors,
}
RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("TREND ROWS:", len(trends_df))
print("BY SPORT:", receipt["trend_rows_by_sport"])
print("AVAILABILITY MATCHES:", join_availability)
print("ROLE MATCHES:", join_role)
print("RETURN WATCH + ADD:", stash_add)
print("ROLE UP + ADD:", role_add)
print("SOURCE STATUS:", dict(zip(source_df["sport"], source_df["trend_status"])))
print("ERRORS:", len(errors))
print("RESULT: FANTASY_MARKET_READY")
