#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "intelligence_warehouse" / "dfs_accountability"
OUT.mkdir(parents=True, exist_ok=True)

import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premium_ui.dfs_optimizer import CONFIG, eligible, game_key, optimize_nfl

CURRENT_SOURCE = ROOT / "intelligence_warehouse" / "dfs" / "DFS_CONTEST_ARCHETYPES_CURRENT.csv"
TIMELINE = ROOT / "intelligence_warehouse" / "dfs" / "DFS_SALARY_TIMELINE.csv"
SCHEDULE = ROOT / "nfl_live" / "derived" / "NFLVERSE_2026_SCHEDULE.csv"
PLAYER_STATS = ROOT / "nfl_live" / "player_context" / "derived" / "NFL_PLAYER_STATS_RECENT.csv"

LEDGER = OUT / "DFS_BENCHMARK_LEDGER.jsonl"
FORWARD_GRADES = OUT / "DFS_FORWARD_GRADES.json"
REPLAY = OUT / "DFS_REPLAY_BACKTEST.json"
SUMMARY = OUT / "DFS_ACCOUNTABILITY_SUMMARY.json"

MODEL_VERSION = "DFS_OPTIMIZER_V3_2026_10_05"
ET = ZoneInfo("America/New_York")

MODES = {
    "BEST_OVERALL": "Balanced",
    "CASH_SAFE": "Cash Safe",
    "TOURNAMENT_UPSIDE": "GPP",
    "CONTRARIAN": "Contrarian",
}
FORWARD_MODES = {
    **MODES,
    "MAX_PROJECTION_BASELINE": "Max Projection",
}


def now_utc():
    return datetime.now(timezone.utc)


def iso(value):
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return str(value)


def clean_key(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def num(value, default=0.0):
    try:
        x = float(value)
        return default if math.isnan(x) else x
    except Exception:
        return default


def json_safe(value):
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return iso(value)
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def write_json(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False))
    tmp.replace(path)


def load_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def append_jsonl(path, row):
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def load_schedule():
    d = pd.read_csv(SCHEDULE)
    d = d[d["season"].eq(2026)].copy()
    d["_kickoff"] = d.apply(schedule_kickoff, axis=1)
    return d


def schedule_kickoff(row):
    day = str(row.get("gameday") or "").strip()
    tm = str(row.get("gametime") or "").strip()
    if not day:
        return pd.NaT
    if not tm or tm.lower() == "nan":
        tm = "13:00"
    try:
        local = datetime.fromisoformat(day + "T" + tm).replace(tzinfo=ET)
        return pd.Timestamp(local.astimezone(timezone.utc))
    except Exception:
        return pd.NaT


def nearest_game(schedule, team, reference):
    team = str(team or "").upper().strip()
    if not team:
        return None
    ref = pd.Timestamp(reference)
    if ref.tzinfo is None:
        ref = ref.tz_localize("UTC")
    else:
        ref = ref.tz_convert("UTC")
    x = schedule[
        schedule["away_team"].astype(str).str.upper().eq(team)
        | schedule["home_team"].astype(str).str.upper().eq(team)
    ].copy()
    if x.empty:
        return None
    x["_delta"] = (x["_kickoff"] - ref).abs()
    x = x[x["_delta"] <= pd.Timedelta(days=5)].sort_values(["_delta", "_kickoff"])
    if x.empty:
        return None
    return x.iloc[0]


def slate_context(pool, schedule, reference):
    starts = []
    weeks = []
    games = {}
    for team in sorted(set(pool.get("team", pd.Series(dtype=str)).dropna().astype(str).str.upper())):
        row = nearest_game(schedule, team, reference)
        if row is None:
            continue
        kickoff = row.get("_kickoff")
        if pd.notna(kickoff):
            starts.append(pd.Timestamp(kickoff))
        week = row.get("week")
        if pd.notna(week):
            weeks.append(int(week))
        games[team] = {
            "week": int(week) if pd.notna(week) else None,
            "kickoff": iso(kickoff) if pd.notna(kickoff) else None,
            "away": str(row.get("away_team") or ""),
            "home": str(row.get("home_team") or ""),
            "away_score": json_safe(row.get("away_score")),
            "home_score": json_safe(row.get("home_score")),
        }
    lock = None
    if starts:
        ref = pd.Timestamp(reference)
        if ref.tzinfo is None:
            ref = ref.tz_localize("UTC")
        else:
            ref = ref.tz_convert("UTC")
        ref_date = ref.tz_convert(ET).date()

        date_counts = Counter(
            start.tz_convert(ET).date()
            for start in starts
        )
        dominant_date = max(
            date_counts,
            key=lambda day: (
                date_counts[day],
                -abs((day - ref_date).days),
                day,
            ),
        )
        dominant_starts = [
            start for start in starts
            if start.tz_convert(ET).date() == dominant_date
        ]
        lock = min(dominant_starts) if dominant_starts else min(starts)

    week = Counter(weeks).most_common(1)[0][0] if weeks else None
    return lock, week, games


def lineup_record(platform, slate_id, slate_label, mode, strategy, result, source_generated, lock, week):
    observed = now_utc()
    players = []
    for slot, player in result["players"]:
        players.append({
            "slot": slot,
            "player": str(player.get("player") or ""),
            "player_key": str(player.get("player_key") or ""),
            "position": str(player.get("position") or ""),
            "team": str(player.get("team") or ""),
            "opponent": str(player.get("opponent") or ""),
            "salary": int(num(player.get("salary"), 0)),
            "projected_fantasy_points": round(num(player.get("projected_fantasy_points"), 0), 3),
        })
    lineup_signature = hashlib.sha256(
        json.dumps(
            sorted(p["player_key"] for p in players),
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    signature_body = {
        "platform": platform,
        "slate_id": str(slate_id),
        "mode": mode,
        "model_version": MODEL_VERSION,
        "players": [(p["slot"], p["player_key"]) for p in players],
        "projected_points": round(num(result.get("projected_points"), 0), 3),
    }
    signature = hashlib.sha256(
        json.dumps(signature_body, sort_keys=True).encode()
    ).hexdigest()
    return {
        "benchmark_id": signature,
        "lineup_signature": lineup_signature,
        "observed_at": iso(observed),
        "source_generated_at": iso(source_generated),
        "sport": "NFL",
        "season": 2026,
        "week": week,
        "platform": platform,
        "slate_id": str(slate_id),
        "slate_label": str(slate_label or ""),
        "slate_lock": iso(lock),
        "mode": mode,
        "strategy": strategy,
        "model_version": MODEL_VERSION,
        "players": players,
        "salary_used": int(num(result.get("salary_used"), 0)),
        "salary_cap": int(num(result.get("salary_cap"), 0)),
        "salary_remaining": int(num(result.get("salary_remaining"), 0)),
        "projected_points": round(num(result.get("projected_points"), 0), 3),
        "optimizer_score": round(num(result.get("optimizer_score"), 0), 3),
        "stack_pattern": str(result.get("stack_pattern") or ""),
        "games_used": int(num(result.get("games_used"), 0)),
        "ownership_available": bool(result.get("ownership_available", False)),
        "ownership_player_count": int(num(result.get("ownership_player_count"), 0)),
        "projected_ownership_sum": json_safe(result.get("projected_ownership_sum")),
        "strategy_constraints": result.get("strategy_constraints", {}),
        "status": "PRELOCK_FROZEN",
        "score_is_probability": False,
        "automatic_model_adjustment": False,
    }


def capture_forward_benchmarks():
    if not CURRENT_SOURCE.exists() or not SCHEDULE.exists():
        return {"status": "WAITING", "new_snapshots": 0, "slates": []}

    source = pd.read_csv(CURRENT_SOURCE)
    source = source[source["sport"].astype(str).str.upper().eq("NFL")].copy()
    if source.empty:
        return {"status": "WAITING", "new_snapshots": 0, "slates": []}

    schedule = load_schedule()
    existing = load_jsonl(LEDGER)
    existing_ids = {row.get("benchmark_id") for row in existing}
    now = now_utc()
    new_count = 0
    states = []

    for (platform, slate_id), pool in source.groupby(["platform", "slate_id"], dropna=False):
        platform = str(platform).upper()
        if platform not in CONFIG:
            continue

        generated_values = pd.to_datetime(pool.get("generated_at"), errors="coerce", utc=True)
        source_generated = generated_values.max() if len(generated_values) else pd.NaT
        reference = source_generated if pd.notna(source_generated) else pd.Timestamp(now)
        lock, week, games = slate_context(pool, schedule, reference)
        slate_label = pool.get("slate_label", pd.Series([""])).dropna().astype(str)
        slate_label = slate_label.iloc[0] if len(slate_label) else ""

        state = {
            "platform": platform,
            "slate_id": str(slate_id),
            "slate_label": slate_label,
            "slate_lock": iso(lock),
            "week": week,
            "source_generated_at": iso(source_generated) if pd.notna(source_generated) else None,
            "status": "WAITING_FOR_LOCK_CONTEXT" if lock is None else (
                "LOCKED_NO_NEW_SNAPSHOTS" if now >= lock.to_pydatetime() else "PRELOCK_TRACKING"
            ),
        }
        states.append(state)

        if lock is None or now >= lock.to_pydatetime():
            continue

        reference_lineups = []
        for reference_strategy in ["Balanced", "Cash Safe"]:
            reference = optimize_nfl(
                source,
                platform,
                strategy=reference_strategy,
                alternatives=1,
                slate_id=slate_id,
            )
            if reference:
                reference_lineups.append([
                    str(player.get("player_key") or "").strip()
                    for _, player in reference[0]["players"]
                    if str(player.get("player_key") or "").strip()
                ])

        for mode, strategy in MODES.items():
            max_overlap = (
                7 if strategy == "GPP"
                else 6 if strategy == "Contrarian"
                else None
            )
            results = optimize_nfl(
                source,
                platform,
                strategy=strategy,
                alternatives=1,
                slate_id=slate_id,
                reference_lineups=(
                    reference_lineups
                    if strategy in {"GPP", "Contrarian"}
                    else None
                ),
                max_overlap=max_overlap,
            )
            if not results:
                continue
            row = lineup_record(
                platform, slate_id, slate_label, mode, strategy,
                results[0], source_generated, lock, week,
            )
            if row["benchmark_id"] not in existing_ids:
                append_jsonl(LEDGER, row)
                existing_ids.add(row["benchmark_id"])
                new_count += 1

        baseline = optimize_nfl(
            source,
            platform,
            strategy="Max Projection",
            alternatives=1,
            slate_id=slate_id,
        )
        if baseline:
            row = lineup_record(
                platform, slate_id, slate_label,
                "MAX_PROJECTION_BASELINE", "Max Projection",
                baseline[0], source_generated, lock, week,
            )
            if row["benchmark_id"] not in existing_ids:
                append_jsonl(LEDGER, row)
                existing_ids.add(row["benchmark_id"])
                new_count += 1

    return {
        "status": "READY",
        "new_snapshots": new_count,
        "ledger_rows": len(load_jsonl(LEDGER)),
        "slates": states,
    }


def official_forward_records():
    rows = load_jsonl(LEDGER)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(
            row.get("model_version"),
            row.get("platform"),
            row.get("slate_id"),
            row.get("mode"),
        )].append(row)
    official = []
    for _, items in grouped.items():
        items.sort(key=lambda x: x.get("observed_at") or "")
        official.append(items[-1])
    return official


def stat_row_map(stats):
    result = {}
    for _, row in stats.iterrows():
        key = clean_key(row.get("player_display_name") or row.get("player_name"))
        if not key:
            continue
        result[(int(num(row.get("week"), 0)), key, str(row.get("team") or "").upper())] = row
        result[(int(num(row.get("week"), 0)), key, "")] = row
    return result


def offense_points(row, platform):
    pass_yards = num(row.get("passing_yards"))
    pass_tds = num(row.get("passing_tds"))
    ints = num(row.get("passing_interceptions"))
    rush_yards = num(row.get("rushing_yards"))
    rush_tds = num(row.get("rushing_tds"))
    rec = num(row.get("receptions"))
    rec_yards = num(row.get("receiving_yards"))
    rec_tds = num(row.get("receiving_tds"))
    pass_2 = num(row.get("passing_2pt_conversions"))
    rush_2 = num(row.get("rushing_2pt_conversions"))
    rec_2 = num(row.get("receiving_2pt_conversions"))
    returns = num(row.get("special_teams_tds"))
    fumbles_lost = num(row.get("fumbles_lost_total"))
    recovery_tds = num(row.get("fumble_recovery_tds"))

    p = (
        pass_yards * 0.04
        + pass_tds * 4
        - ints
        + rush_yards * 0.1
        + rush_tds * 6
        + rec_yards * 0.1
        + rec_tds * 6
        + (1.0 if platform == "DRAFTKINGS" else 0.5) * rec
        + 2 * (pass_2 + rush_2 + rec_2)
        + 6 * returns
        + 6 * recovery_tds
        - (1.0 if platform == "DRAFTKINGS" else 2.0) * fumbles_lost
    )

    if pass_yards >= 300:
        p += 3
    if rush_yards >= 100:
        p += 3
    if rec_yards >= 100:
        p += 3
    return round(p, 3)


def points_allowed_bonus(points):
    if points <= 0:
        return 10
    if points <= 6:
        return 7
    if points <= 13:
        return 4
    if points <= 20:
        return 1
    if points <= 27:
        return 0
    if points <= 34:
        return -1
    return -4


def defense_points(team, week, stats, schedule):
    team = str(team or "").upper()
    w = stats[(stats["week"].eq(week)) & stats["team"].astype(str).str.upper().eq(team)].copy()
    if w.empty:
        return None

    def total(col):
        if col not in w.columns:
            return 0.0
        return pd.to_numeric(w[col], errors="coerce").fillna(0).sum()

    game = schedule[
        schedule["week"].eq(week)
        & (
            schedule["away_team"].astype(str).str.upper().eq(team)
            | schedule["home_team"].astype(str).str.upper().eq(team)
        )
    ]
    if game.empty:
        return None
    g = game.iloc[0]
    if pd.isna(g.get("away_score")) or pd.isna(g.get("home_score")):
        return None
    opponent_points = num(g.get("home_score")) if str(g.get("away_team")).upper() == team else num(g.get("away_score"))

    sacks = total("def_sacks")
    interceptions = total("def_interceptions")
    fumble_rec = total("fumble_recovery_opp")
    safeties = total("def_safeties")
    blocks = total("def_punt_blocks") + total("def_pat_blocks") + total("def_fg_blocks")
    defensive_tds = total("def_tds")
    return_tds = total("special_teams_tds")
    extra_return = total("def_2pt_made")

    points = (
        sacks
        + 2 * interceptions
        + 2 * fumble_rec
        + 2 * safeties
        + 2 * blocks
        + 6 * (defensive_tds + return_tds)
        + 2 * extra_return
        + points_allowed_bonus(opponent_points)
    )
    return round(float(points), 3)


def team_game_final(schedule, team, week):
    team = str(team or "").upper()
    game = schedule[
        schedule["week"].eq(week)
        & (
            schedule["away_team"].astype(str).str.upper().eq(team)
            | schedule["home_team"].astype(str).str.upper().eq(team)
        )
    ]
    if game.empty:
        return False
    row = game.iloc[0]
    return pd.notna(row.get("away_score")) and pd.notna(row.get("home_score"))


def lineup_actual(players, platform, week, stats, schedule, mapping):
    total = 0.0
    detail = []
    pending = False

    for player in players:
        pos = str(player.get("position") or player.get("slot") or "").upper().replace("D/ST", "DST")
        team = str(player.get("team") or "").upper()
        name = str(player.get("player") or "")
        key = clean_key(player.get("player_key") or name)

        if pos in {"D", "DST"} or str(player.get("slot") or "").upper() in {"D", "DST"}:
            score = defense_points(team, week, stats, schedule)
            if score is None:
                pending = True
                detail.append({"player": name, "team": team, "actual": None, "status": "PENDING"})
            else:
                total += score
                detail.append({"player": name, "team": team, "actual": score, "status": "FINAL", "component": "DST"})
            continue

        row = mapping.get((week, key, team))
        if row is None:
            row = mapping.get((week, key, ""))
        if row is None:
            if team_game_final(schedule, team, week):
                score = 0.0
                total += score
                detail.append({"player": name, "team": team, "actual": score, "status": "FINAL_DNP_OR_NO_STATS"})
            else:
                pending = True
                detail.append({"player": name, "team": team, "actual": None, "status": "PENDING"})
            continue

        score = offense_points(row, platform)
        total += score
        detail.append({"player": name, "team": team, "actual": score, "status": "FINAL"})

    return (None if pending else round(total, 3)), detail


def grade_forward():
    if not PLAYER_STATS.exists() or not SCHEDULE.exists():
        payload = {"generated_at": iso(now_utc()), "status": "WAITING", "grades": []}
        write_json(FORWARD_GRADES, payload)
        return payload

    stats = pd.read_csv(PLAYER_STATS)
    schedule = load_schedule()
    mapping = stat_row_map(stats)
    grades = []

    for record in official_forward_records():
        week = int(num(record.get("week"), 0))
        if week <= 0:
            continue
        actual, detail = lineup_actual(
            record.get("players") or [],
            str(record.get("platform") or ""),
            week,
            stats,
            schedule,
            mapping,
        )
        grade = {
            "benchmark_id": record.get("benchmark_id"),
            "lineup_signature": record.get("lineup_signature"),
            "platform": record.get("platform"),
            "slate_id": record.get("slate_id"),
            "week": week,
            "mode": record.get("mode"),
            "model_version": record.get("model_version"),
            "slate_lock": record.get("slate_lock"),
            "official_snapshot_at": record.get("observed_at"),
            "projected_points": record.get("projected_points"),
            "actual_points": actual,
            "projection_error": None if actual is None else round(actual - num(record.get("projected_points")), 3),
            "status": "GRADED" if actual is not None else "PENDING",
            "player_grades": detail,
            "contest_cash_rate": None,
            "contest_percentile": None,
            "ownership_available": bool(record.get("ownership_available", False)),
            "ownership_player_count": int(num(record.get("ownership_player_count"), 0)),
            "projected_ownership_sum": record.get("projected_ownership_sum"),
            "strategy_constraints": record.get("strategy_constraints", {}),
            "score_quality": "PLATFORM_FORMULA_WITH_WEEKLY_STATS; DST_POINTS_ALLOWED_USES_FINAL_SCORE",
        }
        grades.append(grade)

    payload = {
        "generated_at": iso(now_utc()),
        "status": "READY",
        "grades": grades,
    }
    write_json(FORWARD_GRADES, payload)
    return payload


def enrich_historical_pool(pool, schedule, week):
    d = pool.copy()
    if d.empty:
        return d

    game_rows = schedule[schedule["week"].eq(week)].copy()
    game_by_team = {}
    for _, g in game_rows.iterrows():
        away = str(g.get("away_team") or "").upper()
        home = str(g.get("home_team") or "").upper()
        for team, opp in [(away, home), (home, away)]:
            game_by_team[team] = (opp, home, away, g.get("_kickoff"))

    def context(row):
        team = str(row.get("team") or "").upper()
        return game_by_team.get(team, ("", "", "", pd.NaT))

    ctx = d.apply(context, axis=1)
    d["opponent"] = [x[0] for x in ctx]
    d["home_team"] = [x[1] for x in ctx]
    d["away_team"] = [x[2] for x in ctx]
    d["game_time"] = [iso(x[3]) if pd.notna(x[3]) else None for x in ctx]
    d["audit_value_per_1000"] = pd.to_numeric(
        d.get("provider_value_per_1000"), errors="coerce"
    )
    missing_value = d["audit_value_per_1000"].isna()
    d.loc[missing_value, "audit_value_per_1000"] = (
        pd.to_numeric(d.loc[missing_value, "projected_fantasy_points"], errors="coerce")
        / pd.to_numeric(d.loc[missing_value, "salary"], errors="coerce")
        * 1000
    )
    d["projection_percentile"] = (
        pd.to_numeric(d["projected_fantasy_points"], errors="coerce").rank(pct=True) * 100
    )
    d["value_percentile"] = d["audit_value_per_1000"].rank(pct=True) * 100
    d["context_signal"] = "HISTORICAL_REPLAY_NO_CONTEXT"
    d["contest_archetype"] = ""
    d["availability_status"] = "HISTORICAL_UNKNOWN"
    d["role_signal"] = ""
    d["modelled_ownership_pct"] = None
    d["projected_ownership_pct"] = None
    return d


def random_lineups(
    pool,
    platform,
    count=250,
    seed=20261005,
    min_salary_pct=0.94,
):
    cfg = CONFIG[platform]
    slots = cfg["slots"]
    cap = cfg["cap"]
    min_salary = int(cap * float(min_salary_pct))
    rng = random.Random(seed)
    records = pool.to_dict("records")
    by_slot = {}
    for slot in set(slots):
        by_slot[slot] = [
            row for row in records
            if eligible(slot, row.get("position"), platform)
        ]

    seen = set()
    output = []
    attempts = 0
    while len(output) < count and attempts < count * 120:
        attempts += 1
        used = set()
        lineup = []
        salary = 0
        valid = True
        for slot in slots:
            candidates = [
                row for row in by_slot.get(slot, [])
                if clean_key(row.get("player_key") or row.get("player")) not in used
            ]
            if not candidates:
                valid = False
                break
            row = rng.choice(candidates)
            key = clean_key(row.get("player_key") or row.get("player"))
            used.add(key)
            salary += int(num(row.get("salary")))
            lineup.append((slot, row))
        if not valid or salary > cap or salary < min_salary:
            continue
        games = {game_key(row) for _, row in lineup if game_key(row)}
        if len(games) < cfg.get("min_games", 1):
            continue
        signature = tuple(sorted(used))
        if signature in seen:
            continue
        seen.add(signature)
        output.append({
            "players": lineup,
            "salary_used": salary,
        })
    return output


def reconstruct_prelock_pool(timeline, platform, slate_id, lock):
    g = timeline[
        timeline["platform"].astype(str).str.upper().eq(platform)
        & timeline["slate_id"].astype(str).eq(str(slate_id))
        & (timeline["observed_at"] < lock)
    ].copy()
    if g.empty:
        return g
    g = g.sort_values("observed_at")
    key_col = "player_key" if "player_key" in g.columns else "player"
    g = g.drop_duplicates(key_col, keep="last")
    g["salary"] = pd.to_numeric(g["salary"], errors="coerce")
    g["projected_fantasy_points"] = pd.to_numeric(g["projected_fantasy_points"], errors="coerce")
    return g[g["salary"].notna() & g["projected_fantasy_points"].notna()].copy()


def replay_backtest():
    if not TIMELINE.exists() or not PLAYER_STATS.exists() or not SCHEDULE.exists():
        payload = {"generated_at": iso(now_utc()), "status": "WAITING", "slates": [], "strategy_summary": []}
        write_json(REPLAY, payload)
        return payload

    timeline = pd.read_csv(TIMELINE)
    timeline = timeline[timeline["sport"].astype(str).str.upper().eq("NFL")].copy()
    timeline["observed_at"] = pd.to_datetime(timeline["observed_at"], errors="coerce", utc=True)
    stats = pd.read_csv(PLAYER_STATS)
    schedule = load_schedule()
    mapping = stat_row_map(stats)

    slate_results = []

    for (platform, slate_id), raw in timeline.groupby(["platform", "slate_id"], dropna=False):
        platform = str(platform).upper()
        if platform not in CONFIG or raw.empty:
            continue

        first_observed = raw["observed_at"].min()
        if pd.isna(first_observed):
            continue

        raw_teams = raw["team"].dropna().astype(str).str.upper().unique().tolist()
        context_probe = pd.DataFrame({"team": raw_teams})
        lock, week, _ = slate_context(context_probe, schedule, first_observed)
        if lock is None or week is None:
            continue

        # A replay is valid only when we had data before the slate locked.
        if not (raw["observed_at"] < lock).any():
            continue

        pool = reconstruct_prelock_pool(timeline, platform, slate_id, lock)
        if pool.empty:
            continue
        pool = enrich_historical_pool(pool, schedule, week)

        # Exclude teams that were not actually part of that week's schedule.
        pool = pool[pool["opponent"].astype(str).ne("")].copy()
        if pool.empty:
            continue

        # Require all games represented in any graded lineup to be final.
        if not all(team_game_final(schedule, team, week) for team in pool["team"].dropna().astype(str).str.upper().unique()):
            # Some slates can include a later game that is still pending. We can still
            # grade a lineup if its selected teams are all final, handled below.
            pass

        seed_material = f"{platform}|{slate_id}|{week}".encode()
        stable_seed = int(hashlib.sha256(seed_material).hexdigest()[:8], 16)
        random_pool = random_lineups(pool, platform, count=250, seed=stable_seed)
        random_scores = []
        for line in random_pool:
            players = [
                {
                    "slot": slot,
                    "player": row.get("player"),
                    "player_key": row.get("player_key"),
                    "position": row.get("position"),
                    "team": row.get("team"),
                }
                for slot, row in line["players"]
            ]
            actual, _ = lineup_actual(players, platform, week, stats, schedule, mapping)
            if actual is not None:
                random_scores.append(actual)
        random_scores.sort()

        max_projection_actual = None
        max_projection_result = None
        max_results = optimize_nfl(
            pool,
            platform,
            strategy="Max Projection",
            alternatives=1,
            slate_id=slate_id,
        )
        if max_results:
            max_projection_result = max_results[0]
            max_players = [
                {
                    "slot": slot,
                    "player": row.get("player"),
                    "player_key": row.get("player_key"),
                    "position": row.get("position"),
                    "team": row.get("team"),
                }
                for slot, row in max_projection_result["players"]
            ]
            max_projection_actual, _ = lineup_actual(
                max_players,
                platform,
                week,
                stats,
                schedule,
                mapping,
            )

        mode_signatures = {}
        reference_cache = {}
        reference_lineups = []
        for reference_strategy in ["Balanced", "Cash Safe"]:
            reference = optimize_nfl(
                pool,
                platform,
                strategy=reference_strategy,
                alternatives=1,
                slate_id=slate_id,
            )
            if reference:
                reference_cache[reference_strategy] = reference
                reference_lineups.append([
                    str(player.get("player_key") or "").strip()
                    for _, player in reference[0]["players"]
                    if str(player.get("player_key") or "").strip()
                ])

        for mode, strategy in MODES.items():
            if strategy in reference_cache:
                results = reference_cache[strategy]
            else:
                max_overlap = (
                    7 if strategy == "GPP"
                    else 6 if strategy == "Contrarian"
                    else None
                )
                results = optimize_nfl(
                    pool,
                    platform,
                    strategy=strategy,
                    alternatives=1,
                    slate_id=slate_id,
                    reference_lineups=(
                        reference_lineups
                        if strategy in {"GPP", "Contrarian"}
                        else None
                    ),
                    max_overlap=max_overlap,
                )
            if not results:
                continue
            result = results[0]
            players = [
                {
                    "slot": slot,
                    "player": row.get("player"),
                    "player_key": row.get("player_key"),
                    "position": row.get("position"),
                    "team": row.get("team"),
                    "salary": json_safe(row.get("salary")),
                    "projected_fantasy_points": json_safe(row.get("projected_fantasy_points")),
                }
                for slot, row in result["players"]
            ]
            actual, detail = lineup_actual(players, platform, week, stats, schedule, mapping)
            if actual is None:
                continue

            signature = tuple(sorted(
                clean_key(player.get("player_key") or player.get("player"))
                for player in players
            ))
            collision_with = [
                prior_mode
                for prior_mode, prior_signature in mode_signatures.items()
                if prior_signature == signature
            ]
            mode_signatures[mode] = signature

            percentile = None
            if random_scores:
                at_or_below = sum(1 for value in random_scores if value <= actual)
                percentile = round(100 * at_or_below / len(random_scores), 1)

            slate_results.append({
                "platform": platform,
                "slate_id": str(slate_id),
                "slate_label": str(raw.get("slate_label", pd.Series([""])).dropna().astype(str).iloc[0]) if raw.get("slate_label") is not None and len(raw.get("slate_label").dropna()) else "",
                "season": 2026,
                "week": int(week),
                "lock": iso(lock),
                "prelock_rows": int(len(pool)),
                "mode": mode,
                "strategy": strategy,
                "model_version": MODEL_VERSION,
                "projected_points": round(num(result.get("projected_points")), 3),
                "actual_points": actual,
                "projection_error": round(actual - num(result.get("projected_points")), 3),
                "random_legal_lineups_graded": len(random_scores),
                "random_baseline_salary_floor_pct": 94.0,
                "random_baseline_percentile": percentile,
                "beat_random_median": None if not random_scores else bool(actual > random_scores[len(random_scores)//2]),
                "top_10pct_vs_random": None if percentile is None else bool(percentile >= 90),
                "max_projection_actual_points": max_projection_actual,
                "actual_minus_max_projection": (
                    None
                    if max_projection_actual is None
                    else round(actual - max_projection_actual, 3)
                ),
                "beat_max_projection": (
                    None
                    if max_projection_actual is None
                    else bool(actual > max_projection_actual)
                ),
                "strategy_distinct": not bool(collision_with),
                "mode_collision_with": collision_with,
                "salary_used": int(num(result.get("salary_used"))),
                "stack_pattern": result.get("stack_pattern"),
                "players": players,
                "player_grades": detail,
                "ownership_used": strategy == "Contrarian",
                "contest_cash_rate": None,
                "contest_percentile": None,
                "replay_limitations": [
                    "Historical salary/projection snapshots only; current role/news context was not backfilled.",
                    "Random baseline now requires at least 94% salary-cap usage; its percentile is still not a real contest percentile.",
                    "Each strategy is also compared with a same-slate Max Projection lineup.",
                    "Mode collisions are flagged when two named strategies produce the exact same player set.",
                    "Contrarian replay is withheld when historical ownership is unavailable.",
                    "D/ST points-allowed tier uses final opponent score and can differ from platform settlement when non-offensive scores occurred.",
                ],
            })

    summaries = []
    if slate_results:
        frame = pd.DataFrame(slate_results)
        for (platform, mode), group in frame.groupby(["platform", "mode"]):
            pct = pd.to_numeric(group["random_baseline_percentile"], errors="coerce")
            vs_max = pd.to_numeric(group["actual_minus_max_projection"], errors="coerce")
            collision = ~group["strategy_distinct"].fillna(False).astype(bool)
            slates_n = int(len(group))
            summaries.append({
                "platform": platform,
                "mode": mode,
                "slates": slates_n,
                "avg_actual_points": round(pd.to_numeric(group["actual_points"], errors="coerce").mean(), 2),
                "avg_projection_error": round(pd.to_numeric(group["projection_error"], errors="coerce").mean(), 2),
                "avg_random_baseline_percentile": None if pct.dropna().empty else round(pct.mean(), 1),
                "beat_random_median_rate": round(100 * group["beat_random_median"].fillna(False).mean(), 1),
                "top_10pct_vs_random_rate": round(100 * group["top_10pct_vs_random"].fillna(False).mean(), 1),
                "avg_actual_minus_max_projection": None if vs_max.dropna().empty else round(vs_max.mean(), 2),
                "beat_max_projection_rate": round(100 * group["beat_max_projection"].fillna(False).mean(), 1),
                "distinct_lineup_rate": round(100 * group["strategy_distinct"].fillna(False).mean(), 1),
                "mode_collision_slates": int(collision.sum()),
                "evidence_status": (
                    "REPLAY_SMALL_SAMPLE"
                    if slates_n < 10
                    else "REPLAY_RESEARCH_ONLY"
                ),
                "promotion_eligible": False,
                "contest_cash_rate": None,
                "contest_percentile": None,
            })

    payload = {
        "generated_at": iso(now_utc()),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "method": "LAST_AVAILABLE_PRELOCK_SNAPSHOT_REPLAY",
        "scoring": {
            "draftkings": "Official NFL Classic offensive scoring formula; D/ST event stats from weekly NFL data.",
            "fanduel": "Official NFL scoring formula including 2024+ yardage bonuses; D/ST event stats from weekly NFL data.",
            "dst_points_allowed_quality": "APPROX_FROM_FINAL_OPPONENT_SCORE",
        },
        "slates": slate_results,
        "strategy_summary": summaries,
    }
    write_json(REPLAY, payload)
    return payload


def build_summary(capture, forward, replay):
    all_forward_rows = forward.get("grades") or []
    version_counts = Counter(
        str(row.get("model_version") or "UNKNOWN")
        for row in all_forward_rows
    )
    forward_rows = [
        row for row in all_forward_rows
        if str(row.get("model_version") or "") == MODEL_VERSION
    ]

    forward_summary = []
    if forward_rows:
        df = pd.DataFrame(forward_rows)
        graded_df = df[df["status"].eq("GRADED")].copy()

        baseline = {}
        for _, row in graded_df[
            graded_df["mode"].eq("MAX_PROJECTION_BASELINE")
        ].iterrows():
            baseline[(row.get("platform"), row.get("slate_id"))] = {
                "actual": num(row.get("actual_points"), None),
                "signature": row.get("lineup_signature"),
            }

        user_signatures = defaultdict(list)
        for _, row in graded_df[
            ~graded_df["mode"].eq("MAX_PROJECTION_BASELINE")
        ].iterrows():
            user_signatures[
                (row.get("platform"), row.get("slate_id"))
            ].append((row.get("mode"), row.get("lineup_signature")))

        for (platform, mode), group in df[
            ~df["mode"].eq("MAX_PROJECTION_BASELINE")
        ].groupby(["platform", "mode"]):
            graded = group[group["status"].eq("GRADED")].copy()
            vs_max = []
            beat_max = []
            same_as_max = []
            mode_collision = []
            ownership_ready = []

            for _, row in graded.iterrows():
                key = (row.get("platform"), row.get("slate_id"))
                base = baseline.get(key)
                actual = num(row.get("actual_points"), None)
                if base and actual is not None and base.get("actual") is not None:
                    delta = actual - float(base["actual"])
                    vs_max.append(delta)
                    beat_max.append(delta > 0)
                    same_as_max.append(
                        bool(row.get("lineup_signature"))
                        and row.get("lineup_signature") == base.get("signature")
                    )

                sig = row.get("lineup_signature")
                collision = any(
                    other_mode != mode
                    and sig
                    and sig == other_sig
                    for other_mode, other_sig in user_signatures.get(key, [])
                )
                mode_collision.append(collision)
                ownership_ready.append(bool(row.get("ownership_available", False)))

            graded_n = int(len(graded))
            avg_vs_max = None if not vs_max else round(sum(vs_max) / len(vs_max), 2)
            beat_max_rate = None if not beat_max else round(100 * sum(beat_max) / len(beat_max), 1)
            same_as_max_rate = None if not same_as_max else round(100 * sum(same_as_max) / len(same_as_max), 1)
            distinct_rate = None if not mode_collision else round(
                100 * (1 - sum(mode_collision) / len(mode_collision)), 1
            )
            ownership_rate = None if not ownership_ready else round(
                100 * sum(ownership_ready) / len(ownership_ready), 1
            )

            if graded_n < 20:
                proof_status = "BUILDING_FORWARD_SAMPLE"
            elif mode == "BEST_OVERALL":
                if (
                    avg_vs_max is not None
                    and avg_vs_max > 0
                    and beat_max_rate is not None
                    and beat_max_rate > 50
                    and distinct_rate is not None
                    and distinct_rate >= 70
                ):
                    proof_status = "MANUAL_REVIEW_CANDIDATE"
                else:
                    proof_status = "NOT_PROVEN_VS_MAX_PROJECTION"
            elif mode == "CASH_SAFE":
                proof_status = "AWAITING_REAL_CONTEST_CASH_LINES"
            elif mode in {"TOURNAMENT_UPSIDE", "CONTRARIAN"}:
                if mode == "CONTRARIAN" and ownership_rate is not None and ownership_rate < 100:
                    proof_status = "OWNERSHIP_INCOMPLETE"
                else:
                    proof_status = "AWAITING_REAL_CONTEST_STANDINGS"
            else:
                proof_status = "RESEARCH_ONLY"

            forward_summary.append({
                "platform": platform,
                "mode": mode,
                "model_version": MODEL_VERSION,
                "official_slates": int(len(group)),
                "graded_slates": graded_n,
                "minimum_forward_slates_for_review": 20,
                "avg_actual_points": None if graded.empty else round(
                    pd.to_numeric(graded["actual_points"], errors="coerce").mean(), 2
                ),
                "avg_projection_error": None if graded.empty else round(
                    pd.to_numeric(graded["projection_error"], errors="coerce").mean(), 2
                ),
                "avg_actual_minus_max_projection": avg_vs_max,
                "beat_max_projection_rate": beat_max_rate,
                "same_as_max_projection_rate": same_as_max_rate,
                "distinct_lineup_rate": distinct_rate,
                "ownership_available_rate": ownership_rate,
                "proof_status": proof_status,
                "automatic_promotion": False,
                "cash_rate": None,
                "contest_percentile": None,
            })

    payload = {
        "generated_at": iso(now_utc()),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "principles": [
            "No post-lock benchmark creation.",
            "Append-only benchmark history.",
            "Pending results remain pending.",
            "V3 forward proof never borrows V2 results.",
            "Replay random baseline requires at least 94% salary-cap usage.",
            "Every forward strategy is frozen alongside a same-slate Max Projection baseline.",
            "GPP requires a QB pass-catcher stack.",
            "Contrarian requires ownership data and is withheld when ownership is missing.",
            "Mode collisions are measured instead of counting identical lineups as separate strategy proof.",
            "No automatic strategy promotion from replay or a tiny forward sample.",
        ],
        "capture": capture,
        "forward": {
            "current_model_version": MODEL_VERSION,
            "version_counts": dict(version_counts),
            "summary": forward_summary,
            "grades": forward_rows,
        },
        "replay": {
            "method": replay.get("method"),
            "strategy_summary": replay.get("strategy_summary") or [],
            "graded_slates": len(replay.get("slates") or []),
        },
        "contest_metrics": {
            "cash_rate_available": False,
            "tournament_percentile_available": False,
            "reason": "Real contest cut lines/standings are not connected yet; Cash/GPP/Contrarian cannot be called proven without them.",
        },
    }
    write_json(SUMMARY, payload)
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forward-only",
        action="store_true",
        help="Capture/grade forward benchmarks without rerunning the historical replay.",
    )
    args = parser.parse_args()

    capture = capture_forward_benchmarks()
    forward = grade_forward()

    if args.forward_only and REPLAY.exists():
        try:
            replay = json.loads(REPLAY.read_text())
        except Exception:
            replay = replay_backtest()
    else:
        replay = replay_backtest()

    summary = build_summary(capture, forward, replay)
    print(json.dumps({
        "status": summary["status"],
        "new_snapshots": capture.get("new_snapshots", 0),
        "ledger_rows": capture.get("ledger_rows", 0),
        "forward_grades": len(forward.get("grades") or []),
        "replay_lineups": len(replay.get("slates") or []),
        "replay_strategy_rows": len(replay.get("strategy_summary") or []),
    }, indent=2))


if __name__ == "__main__":
    main()
