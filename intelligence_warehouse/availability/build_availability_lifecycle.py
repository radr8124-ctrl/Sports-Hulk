#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "availability"
TIMELINE = OUT / "AVAILABILITY_TIMELINE.csv"
CURRENT = OUT / "AVAILABILITY_CURRENT.csv"
TRANSITIONS = OUT / "AVAILABILITY_TRANSITIONS.csv"
RETURN_WATCH = OUT / "RETURN_WATCH.csv"
REPORTS = OUT / "AVAILABILITY_REPORTS_CURRENT.csv"
RECEIPT = OUT / "AVAILABILITY_RECEIPT.json"

NOW = datetime.now(timezone.utc)
NOW_ISO = NOW.isoformat()

STATE_RANK = {
    "AVAILABLE": 0,
    "UNKNOWN": 1,
    "GTD": 2,
    "DAY_TO_DAY": 3,
    "QUESTIONABLE": 4,
    "DOUBTFUL": 5,
    "INACTIVE": 6,
    "OUT": 7,
    "PUP": 8,
    "IR": 9,
    "SUSPENDED": 9,
}

def clean(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return re.sub(r"\s+", " ", str(v).strip())

def pkey(v):
    return re.sub(r"[^a-z0-9]+", "", clean(v).lower())

def state(raw, fantasy="", gate=""):
    text = " ".join([clean(raw), clean(fantasy), clean(gate)]).lower()
    if re.search(r"\bsusp", text):
        return "SUSPENDED"
    if "injured reserve" in text or re.search(r"\bir(?:-|\b)", text):
        return "IR"
    if "pup" in text or "physically unable" in text:
        return "PUP"
    if re.search(r"\bout\b", text) or "block" in text:
        return "OUT"
    if "inactive" in text:
        return "INACTIVE"
    if "doubtful" in text:
        return "DOUBTFUL"
    if "questionable" in text:
        return "QUESTIONABLE"
    if "day-to-day" in text or "day to day" in text:
        return "DAY_TO_DAY"
    if re.search(r"\bgtd\b", text) or "game-time decision" in text:
        return "GTD"
    if any(x in text for x in ["active", "available", "healthy"]):
        return "AVAILABLE"
    return "UNKNOWN"

def hash_text(*vals):
    return hashlib.sha256(
        "|".join(clean(v) for v in vals).encode()
    ).hexdigest()[:20]

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

def row(
    sport, player, player_key="", player_id="", team="", position="",
    status_raw="", fantasy_status="", injury_type="", body_part="",
    practice="", return_date="", source="", source_tier="",
    source_url="", event_id="", detail="", observed_at="", source_record_at=""
):
    player = clean(player)
    player_key = clean(player_key) or pkey(player)
    st = state(status_raw, fantasy_status)
    detail = clean(detail)
    obs = clean(observed_at) or NOW_ISO
    return {
        "sport": sport,
        "player_key": player_key,
        "player_id": clean(player_id),
        "player": player,
        "team": clean(team),
        "position": clean(position),
        "status_raw": clean(status_raw),
        "fantasy_status": clean(fantasy_status),
        "status_normalized": st,
        "injury_type": clean(injury_type),
        "body_part": clean(body_part),
        "practice_participation": clean(practice),
        "return_date": clean(return_date),
        "source": clean(source),
        "source_tier": clean(source_tier),
        "source_url": clean(source_url),
        "event_id": clean(event_id),
        "detail": detail,
        "detail_hash": hash_text(detail),
        "observed_at": obs,
        "source_record_at": clean(source_record_at),
    }

def nfl_current():
    rows = []
    espn = read_csv(ROOT / "nfl_live/decision/NFL_ESPN_INJURIES.csv")
    sleeper = read_csv(ROOT / "nfl_live/player_context/derived/NFL_SLEEPER_PLAYER_STATUS.csv")

    sleeper_by_key = {}
    if not sleeper.empty:
        for _, r in sleeper.iterrows():
            sleeper_by_key[pkey(r.get("full_name"))] = r

    if not espn.empty:
        for _, r in espn.iterrows():
            key = clean(r.get("player_key")) or pkey(r.get("player"))
            s = sleeper_by_key.get(key)
            rows.append(row(
                "NFL", r.get("player"), key,
                team=(s.get("team") if s is not None else r.get("team")),
                position=r.get("position") or (s.get("position") if s is not None else ""),
                status_raw=r.get("status"),
                injury_type=r.get("injury_type"),
                body_part=(s.get("injury_body_part") if s is not None else ""),
                practice=(s.get("practice_participation") if s is not None else ""),
                source="ESPN_PUBLIC_INJURY_CONTEXT",
                source_tier="STRUCTURED_INJURY",
                detail=r.get("detail"),
            ))

    if not sleeper.empty:
        for _, r in sleeper.iterrows():
            raw = clean(r.get("injury_status")) or clean(r.get("status"))
            st = state(raw)
            if st == "AVAILABLE" and not clean(r.get("injury_status")):
                continue
            rows.append(row(
                "NFL", r.get("full_name"), pkey(r.get("full_name")), r.get("sleeper_id"),
                r.get("team"), r.get("position"), raw,
                injury_type=r.get("injury_status"),
                body_part=r.get("injury_body_part"),
                practice=r.get("practice_participation"),
                source="SLEEPER_PLAYER_STATUS",
                source_tier="FANTASY_PLATFORM_STATUS",
            ))
    return rows

def nfl_raw_history():
    rows = []
    raw_dir = ROOT / "nfl_live/decision/raw"
    for path in sorted(raw_dir.glob("ESPN_NFL_INJURIES_*.json")):
        try:
            obj = json.loads(path.read_text())
        except Exception:
            continue
        observed = clean(obj.get("timestamp"))
        if not observed:
            m = re.search(r"(\d{8}T\d{6}Z)", path.name)
            observed = m.group(1) if m else ""
        for team in obj.get("injuries") or []:
            for item in team.get("injuries") or []:
                athlete = item.get("athlete") or {}
                tm = athlete.get("team") or {}
                pos = athlete.get("position") or {}
                status = item.get("status") or (athlete.get("status") or {}).get("name")
                rows.append(row(
                    "NFL",
                    athlete.get("displayName"),
                    pkey(athlete.get("displayName")),
                    athlete.get("id") or "",
                    tm.get("abbreviation") or team.get("displayName"),
                    pos.get("abbreviation"),
                    status,
                    injury_type=(item.get("type") or {}).get("description"),
                    source="ESPN_PUBLIC_INJURY_CONTEXT",
                    source_tier="STRUCTURED_INJURY",
                    detail=item.get("shortComment") or item.get("longComment"),
                    observed_at=observed,
                    source_record_at=item.get("date"),
                ))
    return rows

def nba_current():
    rows = []
    d = read_csv(ROOT / "nba_live/derived/NBA_INJURIES_CURRENT.csv")
    for _, r in d.iterrows():
        rows.append(row(
            "NBA", r.get("player"), pkey(r.get("player")), r.get("player_id"),
            r.get("team"), "", r.get("status"), r.get("fantasy_status"),
            r.get("injury_type"), r.get("location"), "",
            r.get("return_date"), "ESPN_PUBLIC_INJURY_CONTEXT",
            "STRUCTURED_INJURY", event_id=r.get("event_id"), detail=r.get("detail"),
            source_record_at=r.get("start"),
        ))
    return rows

def nhl_current():
    rows = []
    d = read_csv(ROOT / "nhl_live/derived/NHL_INJURIES_CURRENT.csv")
    for _, r in d.iterrows():
        rows.append(row(
            "NHL", r.get("player"), r.get("player_key"), r.get("nhl_player_id"),
            r.get("team"), "", r.get("status"), r.get("fantasy_status"),
            r.get("injury_type"), r.get("side"), "",
            r.get("return_date"), r.get("source") or "ESPN_PUBLIC_INJURY_CONTEXT",
            "STRUCTURED_INJURY", detail=r.get("detail"),
            source_record_at=r.get("updated"),
        ))
    return rows

def availability_reports():
    n = read_csv(ROOT / "sports_content/derived/SPORTS_NEWS_CURRENT.csv")
    if n.empty or "news_type" not in n.columns:
        return pd.DataFrame()
    n = n[n["news_type"].astype(str).eq("INJURY")].copy()
    keep = [
        "news_id","sport","source","headline","description",
        "published_at","source_url","ingested_at","provenance_status",
    ]
    keep = [c for c in keep if c in n.columns]
    return n[keep].drop_duplicates("news_id", keep="last")

def make_obs_key(r):
    return hash_text(
        r["sport"], r["player_key"], r["source"],
        r["status_normalized"], r["status_raw"], r["injury_type"],
        r["body_part"], r["practice_participation"], r["return_date"],
        r["detail_hash"],
    )

def main():
    OUT.mkdir(parents=True, exist_ok=True)

    rows = []

    # The raw NFL injury archive is ~1 GB. Keep normal refreshes fast.
    # Historical backfill is opt-in and can be run as a separate governed job.
    if os.environ.get("AVAILABILITY_BACKFILL_NFL") == "1":
        rows += nfl_raw_history()

    rows += nfl_current()
    rows += nba_current()
    rows += nhl_current()

    current_raw = pd.DataFrame(
        nfl_current() + nba_current() + nhl_current()
    )

    incoming = pd.DataFrame(rows)
    if incoming.empty:
        raise SystemExit("No availability rows collected.")

    incoming["observation_key"] = incoming.apply(make_obs_key, axis=1)
    incoming = incoming.drop_duplicates("observation_key", keep="last")

    old = read_csv(TIMELINE)
    if old.empty:
        timeline = incoming.copy()
    else:
        timeline = pd.concat([old, incoming], ignore_index=True, sort=False)
        timeline = timeline.drop_duplicates("observation_key", keep="first")

    timeline["_obs"] = pd.to_datetime(timeline["observed_at"], utc=True, errors="coerce")
    timeline = timeline.sort_values(["sport","player_key","source","_obs"])
    timeline.drop(columns=["_obs"]).to_csv(TIMELINE, index=False)

    # Consensus current: retain source disagreement explicitly.
    current_rows = []
    if not current_raw.empty:
        current_raw["observation_key"] = current_raw.apply(make_obs_key, axis=1)

        first_seen_map = {}
        timeline_first = timeline.copy()
        timeline_first["_obs"] = pd.to_datetime(
            timeline_first["observed_at"],
            utc=True,
            errors="coerce",
        )
        first_series = (
            timeline_first
            .dropna(subset=["_obs"])
            .groupby(["sport","player_key"])["_obs"]
            .min()
        )
        first_seen_map = {
            (str(sport), str(key)): ts.isoformat()
            for (sport, key), ts in first_series.items()
        }

        for (sport, key), g in current_raw.groupby(["sport","player_key"], dropna=False):
            states = sorted(set(g["status_normalized"].astype(str)))
            ranked = g.assign(
                _rank=g["status_normalized"].map(STATE_RANK).fillna(1)
            ).sort_values(["_rank"], ascending=False)
            best = ranked.iloc[0].to_dict()
            return_dates = pd.to_datetime(g["return_date"], errors="coerce")
            return_date = ""
            if return_dates.notna().any():
                return_date = return_dates.max().date().isoformat()
            first_seen = first_seen_map.get(
                (str(sport), str(key)),
                "",
            )
            current_rows.append({
                "sport": sport,
                "player_key": key,
                "player_id": best.get("player_id",""),
                "player": best.get("player",""),
                "team": best.get("team",""),
                "position": best.get("position",""),
                "status_normalized": best.get("status_normalized","UNKNOWN"),
                "status_raw": best.get("status_raw",""),
                "injury_type": best.get("injury_type",""),
                "body_part": best.get("body_part",""),
                "practice_participation": best.get("practice_participation",""),
                "return_date": return_date,
                "source_count": int(g["source"].nunique()),
                "sources": "|".join(sorted(set(g["source"].astype(str)))),
                "source_states": "|".join(states),
                "source_disagreement": len(states) > 1,
                "first_seen_at": first_seen,
                "last_seen_at": NOW_ISO,
                "detail": best.get("detail",""),
            })

    current = pd.DataFrame(current_rows)
    current.to_csv(CURRENT, index=False)

    # State transitions: same-source transitions only, so source changes do not
    # create fake injury transitions. Collapse same-state repeats first.
    tr = timeline.copy()
    tr["_obs"] = pd.to_datetime(
        tr["observed_at"],
        utc=True,
        errors="coerce",
    )
    tr = tr.sort_values(
        ["sport","player_key","source","_obs"]
    )
    group_cols = ["sport","player_key","source"]
    tr["from_state"] = tr.groupby(group_cols)["status_normalized"].shift(1)
    tr = tr[
        tr["from_state"].notna()
        & tr["status_normalized"].notna()
        & tr["from_state"].astype(str).ne(tr["status_normalized"].astype(str))
    ].copy()

    if tr.empty:
        transitions = pd.DataFrame(columns=[
            "transition_id","sport","player_key","player","team","source",
            "from_state","to_state","transition_at","source_record_at",
            "return_date","detail",
        ])
    else:
        transitions = pd.DataFrame({
            "sport": tr["sport"],
            "player_key": tr["player_key"],
            "player": tr["player"],
            "team": tr["team"],
            "source": tr["source"],
            "from_state": tr["from_state"],
            "to_state": tr["status_normalized"],
            "transition_at": tr["observed_at"],
            "source_record_at": tr["source_record_at"],
            "return_date": tr["return_date"],
            "detail": tr["detail"],
        })
        transitions["transition_id"] = transitions.apply(
            lambda r: hash_text(
                r["sport"], r["player_key"], r["source"],
                r["from_state"], r["to_state"], r["transition_at"]
            ),
            axis=1,
        )
        transitions = transitions[
            [
                "transition_id","sport","player_key","player","team","source",
                "from_state","to_state","transition_at","source_record_at",
                "return_date","detail",
            ]
        ].drop_duplicates("transition_id", keep="first")

    transitions.to_csv(TRANSITIONS, index=False)

    # Return watch is research context, not a pickup recommendation.
    watch = current.copy()
    if not watch.empty:
        ret = pd.to_datetime(watch["return_date"], errors="coerce", utc=True)
        days = (ret - pd.Timestamp(NOW)).dt.total_seconds() / 86400.0
        watch["days_to_return"] = days.round(1)
        def window(x):
            if pd.isna(x): return "UNKNOWN"
            if x < -1: return "PAST_DUE_REVIEW"
            if x <= 1: return "TODAY_OR_NEXT_DAY"
            if x <= 3: return "WITHIN_3_DAYS"
            if x <= 7: return "WITHIN_7_DAYS"
            if x <= 21: return "WITHIN_3_WEEKS"
            return "LATER"
        watch["return_window"] = watch["days_to_return"].map(window)
        watch["stash_research_signal"] = (
            watch["status_normalized"].isin(["IR","PUP","OUT","DOUBTFUL","DAY_TO_DAY","GTD"])
            & watch["days_to_return"].between(-1, 21, inclusive="both")
        )
        watch = watch[
            watch["status_normalized"].ne("AVAILABLE")
            | watch["return_date"].astype(str).ne("")
        ].copy()
    watch.to_csv(RETURN_WATCH, index=False)

    reports = availability_reports()
    reports.to_csv(REPORTS, index=False)

    receipt = {
        "generated_at": NOW_ISO,
        "timeline_rows": int(len(timeline)),
        "current_players": int(len(current)),
        "transition_rows": int(len(transitions)),
        "return_watch_rows": int(len(watch)),
        "stash_research_signal_rows": int(
            watch["stash_research_signal"].fillna(False).sum()
        ) if len(watch) else 0,
        "injury_news_reports": int(len(reports)),
        "current_by_sport": (
            current["sport"].value_counts().astype(int).to_dict()
            if len(current) else {}
        ),
        "source_disagreements": int(
            current["source_disagreement"].fillna(False).sum()
        ) if len(current) else 0,
        "automatic_fantasy_move": False,
        "return_date_is_guarantee": False,
        "news_report_is_player_state": False,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

    print("TIMELINE:", len(timeline))
    print("CURRENT PLAYERS:", len(current))
    print("TRANSITIONS:", len(transitions))
    print("RETURN WATCH:", len(watch))
    print("STASH RESEARCH SIGNALS:", receipt["stash_research_signal_rows"])
    print("INJURY NEWS REPORTS:", len(reports))
    print("SOURCE DISAGREEMENTS:", receipt["source_disagreements"])
    print("RESULT: AVAILABILITY_LIFECYCLE_READY")

if __name__ == "__main__":
    main()
