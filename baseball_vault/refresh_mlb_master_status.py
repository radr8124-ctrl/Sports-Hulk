#!/usr/bin/env python3
"""Refresh only recent official MLB status/score rows in the historical master.

Preserve every gamePk and all historical columns; never replace a finalized
box with stale Scheduled status. This runs after the live StatsAPI collector.
No wagers, grade history, player stats, or model predictions are modified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import unicodedata
import re

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "baseball_vault/derived/MLB_GAME_MASTER.csv"
PARQUET = ROOT / "baseball_vault/derived/MLB_GAME_MASTER.parquet"
RECEIPT = ROOT / "baseball_vault/derived/MLB_MASTER_FRESHNESS_RECEIPT.json"
SCHEDULE = "https://statsapi.mlb.com/api/v1/schedule"
FINAL = {"Final", "Game Over"}
LIVE = {"In Progress", "Manager Challenge", "Delayed", "Warmup"}


def clean(value):
    folded = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]", "", folded.encode("ascii", "ignore").decode("ascii").lower())


def id_value(value):
    try:
        if pd.isna(value):
            return ""
        x = str(value).strip()
        if re.fullmatch(r"[0-9]+(?:\.0)?", x):
            return x[:-2] if x.endswith(".0") else x
    except (ValueError, TypeError):
        pass
    return ""


def official_score(value):
    try:
        if value is None:
            return None
        val = float(value)
        if math.isfinite(val) and val >= 0 and val.is_integer():
            return int(val)
    except (TypeError, ValueError):
        pass
    return None


def parse_datetime(value):
    try:
        d = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def parse_schedule(data):
    if not isinstance(data, dict) or not isinstance(data.get("dates"), list):
        raise ValueError("Invalid official schedule")
    by_id = {}
    conflicting = set()
    for day in data["dates"]:
        for g in day.get("games", []):
            gamepk = id_value(g.get("gamePk"))
            teams = g.get("teams") or {}
            away = (teams.get("away") or {}).get("team") or {}
            home = (teams.get("home") or {}).get("team") or {}
            row = {
                "gamePk": gamepk,
                "officialDate": str(g.get("officialDate") or day.get("date") or ""),
                "gameDate": str(g.get("gameDate") or ""),
                "gameType": str(g.get("gameType") or ""),
                "status": str((g.get("status") or {}).get("detailedState") or ""),
                "away_team": str(away.get("name") or ""),
                "away_team_id": id_value(away.get("id")),
                "home_team": str(home.get("name") or ""),
                "home_team_id": id_value(home.get("id")),
                "away_score": official_score((teams.get("away") or {}).get("score")),
                "home_score": official_score((teams.get("home") or {}).get("score")),
                "gameNumber": id_value(g.get("gameNumber")),
                "venue_id": id_value((g.get("venue") or {}).get("id")),
            }
            if not gamepk or not row["gameDate"] or not row["away_team"] or not row["home_team"]:
                continue
            if gamepk in by_id and by_id[gamepk] != row:
                conflicting.add(gamepk)
            else:
                by_id[gamepk] = row
    for gamepk in conflicting:
        by_id.pop(gamepk, None)
    return by_id, conflicting


def verified_far_start_overrides(master, official, observations, *, clock):
    """Whitelist ONLY independently source-corroborated exceptional kickoff shifts.

    Two distinct original, unmodified collector observations are required,
    five minutes apart, BOTH after the stale old scheduled start and before
    the NEW source-official start, with both official nine-person published
    batting orders, same team IDs/names, game type, date and VENUE as in the
    separate current MLB StatsAPI schedule and in historical master. No
    title/date guesses, no broad tolerance increase and no future records.
    This function does not change any model inputs or stored game rows.
    """
    if clock.tzinfo is None:
        raise ValueError("Need clock with actual offset-aware UTC")
    if not {"gamePk", "gameDate", "status", "gameType", "officialDate",
            "away_team", "away_team_id", "home_team", "home_team_id", "venue_id"}.issubset(master.columns):
        # For synthetic older test master with venue_id omitted, decline
        # all exceptional corrections; ordinary <=2h updates still work.
        return {}
    if master.gamePk.duplicated().any() or master.gamePk.isna().any():
        raise ValueError("Cannot repair kickoff on duplicated official master fixture")
    by_id={id_value(row.gamePk):row for _,row in master.iterrows()}
    verified={}
    utc=clock.astimezone(timezone.utc)
    observations_by_game={}
    for evidence in observations:
        if not isinstance(evidence,dict) or evidence.get("schema")!="MLB_PREGAME_SOURCE_EVIDENCE_V1":
            continue
        pk=id_value(evidence.get("game_pk"))
        if not pk:continue
        observations_by_game.setdefault(pk,[]).append(evidence)
    for gamepk,new in official.items():
        old=by_id.get(str(gamepk))
        if old is None:continue
        if (
            str(old.status) not in {"Scheduled","Pre-Game","Warmup","Delayed"}
            or str(new.get("status")) not in {"Scheduled","Pre-Game","Warmup","In Progress","Final","Game Over"}
            or str(old.officialDate)!=str(new.get("officialDate"))
            or str(old.gameType)!=str(new.get("gameType"))
            or not id_value(old.venue_id)
            or id_value(old.venue_id)!=id_value(new.get("venue_id"))
            or any(
                id_value(old[f"{side}_team_id"])!=id_value(new.get(f"{side}_team_id"))
                or clean(old[f"{side}_team"])!=clean(new.get(f"{side}_team"))
                for side in ("away","home")
            )
        ):
            continue
        old_start=parse_datetime(old.gameDate)
        new_start=parse_datetime(new.get("gameDate"))
        if not old_start or not new_start or old_start>=new_start:
            continue
        shift=(new_start-old_start).total_seconds()
        if shift<=2*3600 or shift>6*3600:
            continue
        matched=[]
        for entry in observations_by_game.get(str(gamepk),[]):
            try:
                capture=parse_datetime(entry.get("captured_at_utc"))
                first=parse_datetime(entry.get("first_pitch_utc"))
                fixture=entry.get("fixture") or {}
                lineup=entry.get("lineups") or {}
                if (
                    not capture or not first or first!=new_start or
                    not old_start<capture<first or capture>utc or
                    fixture.get("official_status_at_capture") not in ("Scheduled","Pre-Game","Warmup","Pre-Game Warmup")
                    or id_value(fixture.get("venue_id"))!=id_value(old.venue_id)
                    or str(fixture.get("official_date"))!=str(new.get("officialDate"))
                    or str(fixture.get("official_game_type"))!=str(new.get("gameType"))
                    or any(
                        id_value(fixture.get(f"{side}_team_id"))!=id_value(new.get(f"{side}_team_id"))
                        or clean(fixture.get(f"{side}_team"))!=clean(new.get(f"{side}_team"))
                        for side in ("away","home")
                    )
                    or lineup.get("status")!="OFFICIAL_BATTING_ORDER_VISIBLE_BEFORE_KICKOFF"
                ):
                    continue
                stable=[]
                for side in ("away","home"):
                    roster=lineup.get(side) or {}
                    players=roster.get("player_ids") or []
                    if (
                        len(players)!=9 or
                        len(set(map(str,players)))!=9 or
                        not all(id_value(player) for player in players) or
                        roster.get("source")!="LIVE_FEED_OFFICIAL_BATTING_ORDER_CAPTURED_PREGAME" or
                        roster.get("confirmed_asof_capture") is not True
                    ):
                        break
                    stable.append(tuple(sorted(id_value(x) for x in players)))
                if len(stable)!=2:
                    continue
                digest=entry.get("_raw_source_line_sha256")
                if not digest:
                    digest=sha256((json.dumps(entry,sort_keys=True,separators=(",",":"))+"\n").encode()).hexdigest()
                if len(digest)!=64:
                    continue
                matched.append((capture,str(entry.get("evidence_id")),str(digest),tuple(stable)))
            except (ValueError,TypeError,KeyError):
                continue
        matched.sort()
        same_roster={}
        for time,evidence_id,digest,roster in matched:
            if not evidence_id:continue
            same_roster.setdefault(roster,[]).append((time,evidence_id,digest))
        candidate=None
        for roster,group in same_roster.items():
            for start in group:
                for end in reversed(group):
                    if (end[0]-start[0]).total_seconds()<5*60:
                        continue
                    if start[1]==end[1] or start[2]==end[2]:
                        continue
                    candidate=(start,end)
                    break
                if candidate:break
            if candidate:break
        if not candidate:continue
        start,end=candidate
        verified[str(gamepk)]={
            "gamePk":str(gamepk),
            "old_start":str(old.gameDate),
            "new_start":str(new["gameDate"]),
            "official_venue_id":int(id_value(old.venue_id)),
            "official_game_date":str(new["officialDate"]),
            "official_game_type":str(new["gameType"]),
            "independent_capture_count":2,
            "source_original_line_sha256":[start[2],end[2]],
            "source_distinct_evidence_ids":[start[1],end[1]],
            "source_capture_times_utc":[start[0].isoformat(),end[0].isoformat()],
            "source_lineups_verifiably_published_after_original_stale_time":True,
            "original_scheduled_kickoff_correction_minutes":int(shift/60),
            "source_corroboration":"ORIGINAL_MLB_PREGAME_JSONL_TWO_FULL_BATTING_ORDERS_PLUS_NEW_OFFICIAL_SCHEDULE",
            "betting_model_changed":False,
        }
    return verified


def verified_future_schedule_start_overrides(master, official, observations, *, clock):
    """Attest a shifted FUTURE MLB start using two original official schedule captures.

    Unlike the already-existing post-old-kickoff published-lineup override,
    this narrow gate may run BEFORE the stale old start, when lineups are not
    yet published. It does not infer starters or substitute a model feature.
    Same MLB gamePk/team numeric IDs/names, venue, officialDate, gameType and
    exact new start MUST match the independently re-fetched official schedule.
    """
    if clock.tzinfo is None:
        raise ValueError("Future MLB start attestation requires offset-aware clock")
    required = {"gamePk", "gameDate", "status", "gameType", "officialDate",
                "away_team", "away_team_id", "home_team", "home_team_id", "venue_id"}
    if not required.issubset(master.columns):
        return {}
    if master.gamePk.isna().any() or master.gamePk.duplicated().any():
        raise ValueError("Duplicated original MLB master identity")
    by_id = {id_value(r.gamePk): r for _, r in master.iterrows()}
    now = clock.astimezone(timezone.utc)
    out = {}
    for gamepk, new in official.items():
        old = by_id.get(str(gamepk))
        if old is None or str(old.status) != "Scheduled" or str(new.get("status")) != "Scheduled":
            continue
        old_start = parse_datetime(old.gameDate)
        new_start = parse_datetime(new.get("gameDate"))
        # A start already reached or fewer than 30m away cannot be safely
        # repaired without the stricter after-old-kickoff lineup proof.
        if (not old_start or not new_start or
            not (now + timedelta(minutes=30) < old_start < new_start) or
            not 2*3600 < (new_start-old_start).total_seconds() <= 6*3600):
            continue
        if (str(old.officialDate) != str(new.get("officialDate")) or
            str(old.gameType) != str(new.get("gameType")) or
            not id_value(old.venue_id) or
            id_value(old.venue_id) != id_value(new.get("venue_id")) or
            any(id_value(old[f"{side}_team_id"]) != id_value(new.get(f"{side}_team_id"))
                or clean(old[f"{side}_team"]) != clean(new.get(f"{side}_team"))
                for side in ("home", "away"))):
            continue
        matches = []
        for event in observations:
            if (not isinstance(event, dict) or
                event.get("schema") != "MLB_PREGAME_SOURCE_EVIDENCE_V1" or
                id_value(event.get("game_pk")) != str(gamepk)):
                continue
            ts = parse_datetime(event.get("captured_at_utc"))
            source_start = parse_datetime(event.get("first_pitch_utc"))
            source_fixture = event.get("fixture") or {}
            if (not ts or not source_start or source_start != new_start or
                not ts < old_start or ts > now or
                str(source_fixture.get("official_status_at_capture")) != "Scheduled" or
                str(source_fixture.get("official_date")) != str(new.get("officialDate")) or
                str(source_fixture.get("official_game_type")) != str(new.get("gameType")) or
                id_value(source_fixture.get("venue_id")) != id_value(old.venue_id) or
                any(id_value(source_fixture.get(f"{side}_team_id")) != id_value(new.get(f"{side}_team_id"))
                    or clean(source_fixture.get(f"{side}_team")) != clean(new.get(f"{side}_team"))
                    for side in ("home", "away"))):
                continue
            evidence_id = str(event.get("evidence_id") or "")
            digest = event.get("_raw_source_line_sha256")
            if not digest:
                # Tests and temporary fixture harnesses use exact serialized rows.
                digest = sha256((json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n").encode()).hexdigest()
            if (not evidence_id or len(str(digest)) != 64 or
                any(c not in "0123456789abcdef" for c in str(digest))):
                continue
            matches.append((ts, evidence_id, str(digest)))
        matches.sort()
        pair = None
        for i, early in enumerate(matches):
            for late in reversed(matches[i+1:]):
                if ((late[0]-early[0]).total_seconds() >= 15*60 and
                    early[1] != late[1] and early[2] != late[2]):
                    pair = (early, late)
                    break
            if pair:
                break
        if not pair:
            continue
        early, late = pair
        out[str(gamepk)] = {
            "gamePk": str(gamepk),
            "old_start": str(old.gameDate),
            "new_start": str(new["gameDate"]),
            "official_venue_id": int(id_value(old.venue_id)),
            "official_game_date": str(new["officialDate"]),
            "official_game_type": str(new["gameType"]),
            "independent_capture_count": 2,
            "source_original_line_sha256": [early[2], late[2]],
            "source_distinct_evidence_ids": [early[1], late[1]],
            "source_capture_times_utc": [early[0].isoformat(), late[0].isoformat()],
            "source_schedule_captures_verified_before_old_start": True,
            "source_lineups_verifiably_published_after_original_stale_time": False,
            "original_scheduled_kickoff_correction_minutes": int(
                (new_start-old_start).total_seconds() / 60
            ),
            "source_corroboration": "TWO_EARLY_ORIGINAL_MLB_OFFICIAL_SCHEDULE_CAPTURES_AND_FRESH_SCHEDULE",
            "original_market_prices_or_model_forecasts_changed": False,
        }
    return out


def update_frame(master, official, *, verified_start_overrides=None, clock=None):
    """Return new frame + immutable result summary; no file I/O."""
    if clock is not None and clock.tzinfo is None:
        raise ValueError("Future MLB source attestation needs real offset-aware clock")
    current_clock=clock.astimezone(timezone.utc) if clock is not None else None
    required = {
        "gamePk", "gameDate", "officialDate", "gameType", "status",
        "away_team", "away_team_id", "home_team", "home_team_id",
        "away_score", "home_score", "total_runs", "home_run_margin",
    }
    missing = sorted(required - set(master.columns))
    if missing or master.gamePk.isna().any() or master.gamePk.duplicated().any():
        raise ValueError("Master missing columns or contains duplicate official game IDs: " + str(missing))

    latest = master.copy(deep=True)
    game_positions = {id_value(pk): idx for idx, pk in enumerate(latest["gamePk"])}
    changes = []
    accepted_kickoff_attestations = []
    verified_start_overrides = verified_start_overrides or {}
    review = []
    unknown = []
    for gamepk, new in official.items():
        if gamepk not in game_positions:
            unknown.append(gamepk)
            continue
        rowi = game_positions[gamepk]
        old = latest.loc[rowi]
        if (
            clean(old["away_team"]) != clean(new["away_team"])
            or clean(old["home_team"]) != clean(new["home_team"])
            or id_value(old["away_team_id"]) != new["away_team_id"]
            or id_value(old["home_team_id"]) != new["home_team_id"]
            or str(old["gameType"]) != new["gameType"]
        ):
            review.append({"gamePk": gamepk, "reason": "OFFICIAL_GAME_TEAM_OR_TYPE_CONFLICT"})
            continue
        official_start, old_start = parse_datetime(new["gameDate"]), parse_datetime(old["gameDate"])
        kickoff_shift_over_limit=(
            bool(official_start and old_start)
            and abs((official_start-old_start).total_seconds())>2*3600
        )
        if not official_start or not old_start or kickoff_shift_over_limit:
            verified=verified_start_overrides.get(str(gamepk))
            identity_checked=(
                kickoff_shift_over_limit and isinstance(verified,dict)
                and verified.get("gamePk")==str(gamepk)
                and verified.get("old_start")==str(old["gameDate"])
                and verified.get("new_start")==str(new["gameDate"])
                and verified.get("official_game_date")==str(new["officialDate"])
                and verified.get("official_game_type")==str(new["gameType"])
                and str(verified.get("official_venue_id"))==id_value(old.get("venue_id"))
                and verified.get("independent_capture_count")==2
                and len(verified.get("source_original_line_sha256") or [])==2
            )
            late_lineups_valid=bool(
                identity_checked
                and verified.get("source_lineups_verifiably_published_after_original_stale_time") is True
            )
            captures=[
                parse_datetime(value)
                for value in (verified.get("source_capture_times_utc") or [])
            ] if isinstance(verified,dict) else []
            fingerprints=(verified.get("source_original_line_sha256") or []) if isinstance(verified,dict) else []
            evidence_ids=(verified.get("source_distinct_evidence_ids") or []) if isinstance(verified,dict) else []
            early_schedule_valid=bool(
                identity_checked
                and verified.get("source_corroboration")==
                    "TWO_EARLY_ORIGINAL_MLB_OFFICIAL_SCHEDULE_CAPTURES_AND_FRESH_SCHEDULE"
                and verified.get("source_schedule_captures_verified_before_old_start") is True
                and current_clock is not None
                and str(old.get("status"))=="Scheduled"
                and str(new.get("status"))=="Scheduled"
                and old_start > current_clock + timedelta(minutes=30)
                and 2*3600 < (official_start-old_start).total_seconds() <= 6*3600
                and len(captures)==2 and all(captures)
                and captures[0] < captures[1] < old_start
                and captures[1] <= current_clock
                and (captures[1]-captures[0]).total_seconds()>=15*60
                and len(fingerprints)==2 and len(set(fingerprints))==2
                and len(evidence_ids)==2 and len(set(evidence_ids))==2
            )
            if not (late_lineups_valid or early_schedule_valid):
                review.append({"gamePk": gamepk, "reason": "KICKOFF_CHANGED_BEYOND_TWO_HOURS"})
                continue
            accepted_kickoff_attestations.append(verified)
        current = str(old.get("status") or "")
        status = new["status"]
        rank = {"Scheduled": 0, "Pre-Game": 1, "Warmup": 1,
                "Delayed": 1, "In Progress": 2, "Manager Challenge": 2,
                "Final": 3, "Game Over": 3}
        if current in rank and status in rank and rank[status] < rank[current]:
            review.append({"gamePk": gamepk, "reason": "ATTEMPTED_OFFICIAL_STATUS_DOWNGRADE"})
            continue
        if status in FINAL:
            if new["away_score"] is None or new["home_score"] is None:
                review.append({"gamePk": gamepk, "reason": "OFFICIAL_FINAL_MISSING_SCORES"})
                continue
            if current in FINAL:
                already = (official_score(old["away_score"]), official_score(old["home_score"]))
                desired = (new["away_score"], new["home_score"])
                if already != desired:
                    review.append({"gamePk": gamepk, "reason": "CONTRADICTORY_FINAL_SCORE"})
                    continue
        if status not in FINAL | LIVE | {"Scheduled", "Pre-Game"}:
            review.append({"gamePk": gamepk, "reason": "UNSUPPORTED_STATUS"})
            continue

        fields = {"status": status, "gameDate": new["gameDate"]}
        if status in FINAL | LIVE:
            for side in ("away", "home"):
                value = new[f"{side}_score"]
                if value is not None:
                    fields[f"{side}_score"] = value
            if new["away_score"] is not None and new["home_score"] is not None:
                fields["total_runs"] = new["away_score"] + new["home_score"]
                fields["home_run_margin"] = new["home_score"] - new["away_score"]

        modified = False
        for field, value in fields.items():
            old_value = old[field]
            numeric = field in {"away_score", "home_score", "total_runs", "home_run_margin"}
            if numeric:
                old_numeric = pd.to_numeric(old_value, errors="coerce")
                equivalent = (pd.isna(old_numeric) and value is None) or (
                    not pd.isna(old_numeric) and value is not None
                    and abs(float(old_numeric) - float(value)) < 1e-9
                )
            else:
                equivalent = (pd.isna(old_value) and value is None) or (
                    not pd.isna(old_value) and str(old_value) == str(value)
                )
            if not equivalent:
                latest.at[rowi, field] = value
                modified = True
        if modified:
            changes.append({"gamePk": gamepk, "before_status": current, "after_status": status})

    summary = {
        "updated_games": len(changes),
        "updated_game_ids": [x["gamePk"] for x in changes],
        "changes": changes,
        "held_for_review": review,
        "verified_large_kickoff_corrections":accepted_kickoff_attestations,
        "new_games_not_in_cached_master": unknown,
        "historical_row_count_preserved": len(latest) == len(master),
    }
    return latest, summary


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=path.parent, encoding="utf-8",
                            prefix=".mlb-master-receipt-", delete=False) as f:
        temp = Path(f.name)
        json.dump(payload, f, indent=2)
        f.write("\n")
    os.replace(temp, path)


def run(root=ROOT, session=None, days_back=8, days_forward=3, clock=None, dry_run=False):
    root = Path(root)
    clock = clock or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise ValueError("Need timezone-aware date")
    session = session or requests.Session()
    master = root / "baseball_vault/derived/MLB_GAME_MASTER.csv"
    parquet = root / "baseball_vault/derived/MLB_GAME_MASTER.parquet"
    receipt_file = root / "baseball_vault/derived/MLB_MASTER_FRESHNESS_RECEIPT.json"
    receipt = {
        "generated_at": clock.isoformat(), "status": "WAITING",
        "dry_run": dry_run, "source": "MLB_STATSAPI_OFFICIAL_SCHEDULE",
        "automatic_model_adjustment": False,
    }
    try:
        before = master.read_bytes()
        prior_hash = sha256(before).hexdigest()
        data = pd.read_csv(master, low_memory=False)
        start = clock.date() - timedelta(days=days_back)
        end = clock.date() + timedelta(days=days_forward)
        r = session.get(SCHEDULE, params={
            "sportId": 1, "startDate": start.isoformat(),
            "endDate": end.isoformat(), "hydrate": "team,linescore",
        }, timeout=20)
        r.raise_for_status()
        official, duplicates = parse_schedule(r.json())
        original_research=root/"intelligence_warehouse/mlb_pregame_capture/MLB_PREGAME_SOURCE_EVIDENCE.jsonl"
        observations=[]
        original_sha=None
        if original_research.is_file():
            original_sha=sha256(original_research.read_bytes()).hexdigest()
            with original_research.open("r",encoding="utf-8") as f:
                for source_line in f:
                    if not source_line.strip():continue
                    event=json.loads(source_line)
                    event["_raw_source_line_sha256"]=sha256(source_line.encode()).hexdigest()
                    observations.append(event)
        verified=verified_far_start_overrides(data,official,observations,clock=clock)
        future=verified_future_schedule_start_overrides(data,official,observations,clock=clock)
        if set(verified) & set(future):
            raise ValueError("Conflicting original MLB future and past-kickoff attestation")
        verified.update(future)
        merged, result = update_frame(data, official,
                                      verified_start_overrides=verified,clock=clock)
        receipt["original_unchanged_pregame_research_source_sha256"]=original_sha
        receipt["official_far_kickoff_corrections_require_two_authenticated_lineups"]=True
        receipt["future_schedule_corrections_require_two_original_prestart_schedule_captures"]=True
        receipt.update({
            **result, "source_start": start.isoformat(),
            "source_end": end.isoformat(),
            "official_games_read": len(official),
            "duplicate_official_ids": sorted(duplicates),
            "master_sha256_before": prior_hash,
        })
        if not result["historical_row_count_preserved"] or duplicates:
            receipt["status"] = "INTEGRITY_HOLD"
        elif any(x["reason"] == "CONTRADICTORY_FINAL_SCORE" for x in result["held_for_review"]):
            receipt["status"] = "INTEGRITY_HOLD"
        elif sha256(master.read_bytes()).hexdigest() != prior_hash:
            receipt["status"] = "MASTER_CHANGED_DURING_REFRESH"
        elif not result["updated_games"]:
            receipt["status"] = "NO_UPDATES"
        elif dry_run:
            receipt["status"] = "DRY_RUN_READY"
        else:
            with NamedTemporaryFile("w", dir=master.parent, encoding="utf-8",
                                    newline="", prefix=".mlb-master-", suffix=".csv",
                                    delete=False) as f:
                csv_temp = Path(f.name)
                merged.to_csv(f, index=False)
            pq_temp = parquet.with_name("." + parquet.name + ".pending")
            try:
                merged.to_parquet(pq_temp, index=False)
                if sha256(master.read_bytes()).hexdigest() != prior_hash:
                    receipt["status"] = "MASTER_CHANGED_BEFORE_PUBLISH"
                else:
                    os.replace(pq_temp, parquet)
                    os.replace(csv_temp, master)
                    receipt["status"] = "UPDATED"
            finally:
                csv_temp.unlink(missing_ok=True)
                pq_temp.unlink(missing_ok=True)
    except (ValueError, KeyError, OSError, requests.exceptions.RequestException) as exc:
        receipt["status"] = "SOURCE_UNAVAILABLE_OR_INVALID"
        receipt["error_type"] = type(exc).__name__
    if not dry_run:
        atomic_json(receipt_file, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days-back", type=int, default=8)
    parser.add_argument("--days-forward", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    opts = parser.parse_args()
    if not 0 <= opts.days_back <= 30 or not 0 <= opts.days_forward <= 30:
        parser.error("Day windows must each be within 0-30 days")
    result = run(days_back=opts.days_back, days_forward=opts.days_forward,
                 dry_run=opts.dry_run)
    print(json.dumps(result, indent=2))
    if result["status"] in {"INTEGRITY_HOLD", "SOURCE_UNAVAILABLE_OR_INVALID", "MASTER_CHANGED_DURING_REFRESH", "MASTER_CHANGED_BEFORE_PUBLISH"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
