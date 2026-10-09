#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import fcntl
import json
import os
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
BASEBALL = ROOT / "baseball_vault"
OUTDIR = ROOT / "intelligence_warehouse" / "mlb_player_history"
RAWDIR = OUTDIR / "raw_boxscores"
LEDGER = OUTDIR / "MLB_PLAYER_GAME_LEDGER.csv"
FEATURES = OUTDIR / "MLB_PLAYER_PREGAME_FEATURES.csv"
RECEIPT = OUTDIR / "LAST_BUILD.json"
GAME_MASTER = BASEBALL / "derived" / "MLB_GAME_MASTER.csv"
GRADED = ROOT / "mlb_live" / "decision" / "history" / "MLB_GRADED_RECOMMENDATIONS.csv"

HIT_FIELDS = {
    "atBats": "ab", "runs": "runs", "hits": "hits", "doubles": "doubles",
    "triples": "triples", "homeRuns": "home_runs", "rbi": "rbi",
    "baseOnBalls": "walks", "strikeOuts": "strikeouts", "stolenBases": "stolen_bases",
}
PITCH_FIELDS = {
    "gamesStarted": "games_started", "runs": "runs_allowed", "earnedRuns": "earned_runs",
    "hits": "hits_allowed", "baseOnBalls": "walks_allowed", "strikeOuts": "pitcher_strikeouts",
    "homeRuns": "home_runs_allowed", "battersFaced": "batters_faced", "outs": "outs",
}

def n(v, default=0):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except Exception:
        return default

def innings_to_outs(v):
    if v in (None, ""):
        return 0
    s = str(v)
    try:
        if "." in s:
            a, b = s.split(".", 1)
            return int(a) * 3 + int((b or "0")[0])
        return int(float(s)) * 3
    except Exception:
        return 0

def fetch_boxscore(game_pk: int, timeout=8):
    RAWDIR.mkdir(parents=True, exist_ok=True)
    path = RAWDIR / f"{game_pk}.json"
    if path.exists() and path.stat().st_size > 100:
        return json.loads(path.read_text())
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Sports-HULK/1.0"})
    r.raise_for_status()
    payload = r.json()
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return payload

def rows_from_box(game, payload):
    rows = []
    game_pk = int(game["gamePk"])
    game_date = str(game["officialDate"])
    for side in ("away", "home"):
        block = (payload.get("teams") or {}).get(side) or {}
        team = block.get("team") or {}
        team_name = team.get("name") or game.get(f"{side}_team")
        opp_name = game.get("home_team") if side == "away" else game.get("away_team")
        players = block.get("players") or {}
        bat_order = block.get("battingOrder") or []
        for _, p in players.items():
            person = p.get("person") or {}
            pid = person.get("id")
            name = person.get("fullName")
            stats = p.get("stats") or {}
            batting = stats.get("batting") or {}
            pitching = stats.get("pitching") or {}
            position = (p.get("position") or {}).get("abbreviation")
            if batting and (n(batting.get("plateAppearances")) > 0 or n(batting.get("atBats")) > 0):
                r = {
                    "gamePk": game_pk, "officialDate": game_date, "season": game_date[:4],
                    "player_id": pid, "player": name, "team": team_name, "opponent": opp_name,
                    "home_away": side.upper(), "position": position, "group": "HITTING",
                    "started": bool(p.get("allPositions")) and str(pid) in {str(x) for x in bat_order},
                    "plate_appearances": n(batting.get("plateAppearances")),
                }
                for src, dst in HIT_FIELDS.items():
                    r[dst] = n(batting.get(src))
                r["singles"] = max(r["hits"] - r["doubles"] - r["triples"] - r["home_runs"], 0)
                r["total_bases"] = r["singles"] + 2*r["doubles"] + 3*r["triples"] + 4*r["home_runs"]
                r["hrr"] = r["hits"] + r["runs"] + r["rbi"]
                rows.append(r)
            if pitching and (n(pitching.get("battersFaced")) > 0 or pitching.get("inningsPitched")):
                r = {
                    "gamePk": game_pk, "officialDate": game_date, "season": game_date[:4],
                    "player_id": pid, "player": name, "team": team_name, "opponent": opp_name,
                    "home_away": side.upper(), "position": position, "group": "PITCHING",
                    "started": bool(pitching.get("gamesStarted")),
                    "innings_pitched": pitching.get("inningsPitched"),
                }
                for src, dst in PITCH_FIELDS.items():
                    r[dst] = n(pitching.get(src))
                r["outs"] = innings_to_outs(pitching.get("inningsPitched"))
                rows.append(r)
    return rows

def load_existing():
    if not LEDGER.exists():
        return pd.DataFrame()
    # Never silently treat an unreadable protected ledger as empty history.
    return pd.read_csv(LEDGER, low_memory=False)


LEDGER_COLUMNS = [
    "gamePk", "officialDate", "season", "player_id", "player", "team", "opponent",
    "home_away", "position", "group", "started", "plate_appearances", "ab",
    "runs", "hits", "doubles", "triples", "home_runs", "rbi", "walks",
    "strikeouts", "stolen_bases", "singles", "total_bases", "hrr",
    "innings_pitched", "games_started", "runs_allowed", "earned_runs",
    "hits_allowed", "walks_allowed", "pitcher_strikeouts",
    "home_runs_allowed", "batters_faced", "outs",
]


def append_official_player_rows_once(path: Path, new_rows: list[dict]) -> int:
    """Append new game-player-role facts without resorting or rewriting old bytes.

    Share the .csv.lock with the verified official Final player bridge.
    Fail on existing source conflicts instead of silently keeping newer grades.
    """
    if not new_rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(path.suffix + ".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        has_source = path.is_file() and path.stat().st_size > 0
        fieldnames = list(LEDGER_COLUMNS)
        previous = {}
        if has_source:
            with path.open("rb") as raw:
                raw.seek(-1, os.SEEK_END)
                if raw.read(1) != b"\n":
                    raise ValueError("Original protected MLB ledger has an incomplete final line")
            with path.open("r", newline="", encoding="utf-8") as fd:
                reader = csv.DictReader(fd)
                fieldnames = list(reader.fieldnames or [])
                if not fieldnames or len(set(fieldnames)) != len(fieldnames):
                    raise ValueError("Protected player history column schema corrupted")
                for prior in reader:
                    key = (str(prior.get("gamePk") or ""), str(prior.get("player_id") or ""), str(prior.get("group") or ""))
                    if any(not component for component in key) or key in previous:
                        raise ValueError("Duplicate/missing original protected MLB player game identity")
                    previous[key] = prior
        extras = set().union(*(set(r) for r in new_rows)) - set(fieldnames)
        if extras:
            raise ValueError("Unexpected new official player history fields: " + str(sorted(extras)))
        seen = set()
        added = []
        for row in new_rows:
            key = (str(row.get("gamePk") or ""), str(row.get("player_id") or ""), str(row.get("group") or ""))
            if any(not component for component in key) or key in seen:
                raise ValueError("Duplicate or invalid incoming player identity")
            seen.add(key)
            original = previous.get(key)
            if original is not None:
                # Only exact serializable duplicate rows can be safely skipped.
                # A change to existing official player results needs source review.
                for col in fieldnames:
                    before = str(original.get(col) or "")
                    incoming = str(row.get(col) if row.get(col) is not None else "")
                    if before != incoming:
                        raise ValueError(f"Protected official player grade conflict: {key} {col}")
                continue
            added.append({col:row.get(col, "") for col in fieldnames})
        if not added:
            return 0
        with path.open("a", encoding="utf-8", newline="") as fd:
            writer = csv.DictWriter(fd, fieldnames=fieldnames, extrasaction="raise")
            if not has_source:
                writer.writeheader()
            writer.writerows(added)
            fd.flush()
            os.fsync(fd.fileno())
        return len(added)


def build_features(df):
    if df.empty:
        return df
    d = df.copy()
    d["officialDate"] = pd.to_datetime(d["officialDate"], errors="coerce")
    d = d.sort_values(["player_id", "group", "officialDate", "gamePk"])
    batting_metrics = ["hits","runs","rbi","doubles","home_runs","walks","stolen_bases","total_bases","hrr","strikeouts"]
    pitching_metrics = ["pitcher_strikeouts","outs","hits_allowed","earned_runs","walks_allowed","home_runs_allowed","batters_faced"]
    metrics = [m for m in batting_metrics + pitching_metrics if m in d.columns]
    player_keys = ["player_id", "group"]
    season_keys = ["player_id", "group", "season"]
    d["pregame_games"] = d.groupby(player_keys, dropna=False, sort=False).cumcount()

    for metric in metrics:
        d["_metric_value"] = pd.to_numeric(d[metric], errors="coerce")
        d["_player_shift"] = (
            d.groupby(player_keys, dropna=False, sort=False)["_metric_value"]
             .shift(1)
        )
        for window in (5, 10, 20):
            rolled = (
                d.groupby(player_keys, dropna=False, sort=False)["_player_shift"]
                 .rolling(window, min_periods=1)
                 .mean()
                 .reset_index(level=[0, 1], drop=True)
            )
            d[f"pregame_{metric}_{window}"] = rolled

        d["_season_shift"] = (
            d.groupby(season_keys, dropna=False, sort=False)["_metric_value"]
             .shift(1)
        )
        expanded = (
            d.groupby(season_keys, dropna=False, sort=False)["_season_shift"]
             .expanding(min_periods=1)
             .mean()
             .reset_index(level=[0, 1, 2], drop=True)
        )
        d[f"pregame_{metric}_season"] = expanded

    return d.drop(columns=["_metric_value", "_player_shift", "_season_shift"], errors="ignore")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-games", type=int, default=75)
    ap.add_argument("--season-min", type=int, default=2024)
    ap.add_argument("--season-max", type=int, default=2026)
    ap.add_argument("--sleep", type=float, default=0.08)
    ap.add_argument("--skip-feature-rebuild", action="store_true")
    ap.add_argument("--game-pks", nargs="*", type=int, default=None)
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    games = pd.read_csv(GAME_MASTER, low_memory=False)
    games["season"] = pd.to_numeric(games["officialDate"].astype(str).str[:4], errors="coerce")
    eligible = games[
        games["status"].astype(str).str.contains("Final|Game Over|Completed", case=False, na=False, regex=True)
        & games["season"].between(args.season_min, args.season_max)
        & games["gameType"].astype(str).isin(["R","F","D","L","W"])
    ].copy()
    eligible = eligible.sort_values(["officialDate","gamePk"], ascending=[False,False])

    existing = load_existing()
    done = set(pd.to_numeric(existing.get("gamePk", pd.Series(dtype=float)), errors="coerce").dropna().astype(int))
    remaining = eligible[~eligible["gamePk"].astype(int).isin(done)].copy()

    priority_pks = []
    if GRADED.exists():
        try:
            graded = pd.read_csv(GRADED, low_memory=False)
            prop_rows = graded[
                graded["lane"].astype(str).str.upper().eq("PROP")
            ].copy()
            priority_pks = (
                pd.to_numeric(prop_rows.get("result_gamePk"), errors="coerce")
                .dropna()
                .astype(int)
                .drop_duplicates()
                .tolist()
            )
        except Exception:
            priority_pks = []

    if args.game_pks:
        target_rank = {pk: i for i, pk in enumerate(args.game_pks)}
        remaining = remaining[remaining["gamePk"].astype(int).isin(target_rank)].copy()
        remaining["_target_rank"] = remaining["gamePk"].astype(int).map(target_rank)
        remaining = remaining.sort_values("_target_rank")
    elif priority_pks:
        rank = {pk: i for i, pk in enumerate(priority_pks)}
        remaining["_priority"] = remaining["gamePk"].astype(int).map(rank)
        remaining["_is_priority"] = remaining["_priority"].notna()
        remaining = remaining.sort_values(
            ["_is_priority", "_priority", "officialDate", "gamePk"],
            ascending=[False, True, False, False],
            na_position="last",
        )

    todo = remaining.head(max(args.max_games, 0)).copy()

    new_rows = []
    errors = []
    for _, game in todo.iterrows():
        game_pk = int(game["gamePk"])
        try:
            payload = fetch_boxscore(game_pk)
            new_rows.extend(rows_from_box(game, payload))
            time.sleep(max(args.sleep, 0))
        except Exception as exc:
            errors.append({"gamePk": game_pk, "error": str(exc)[:300]})

    # The official Final boxscore bridge and this backfill writer share one
    # immutable source. Neither may re-sort/rewrite any existing CSV bytes.
    appended = append_official_player_rows_once(LEDGER, new_rows)
    combined = load_existing()
    if not combined.empty:
        if combined.duplicated(["gamePk", "player_id", "group"]).any():
            raise ValueError("Protected player game source contains duplicate identities")
        # Parquet is a rebuildable derivative; the original CSV is append-only.
        try:
            combined.to_parquet(OUTDIR / "MLB_PLAYER_GAME_LEDGER.parquet", index=False)
        except Exception:
            pass

    if args.skip_feature_rebuild:
        features = pd.DataFrame()
        if FEATURES.exists():
            try:
                features = pd.read_csv(FEATURES, low_memory=False)
            except Exception:
                features = pd.DataFrame()
    else:
        features = build_features(combined)
        if not features.empty:
            features.to_csv(FEATURES, index=False)
            try:
                features.to_parquet(OUTDIR / "MLB_PLAYER_PREGAME_FEATURES.parquet", index=False)
            except Exception:
                pass

    covered_games = int(pd.to_numeric(combined.get("gamePk", pd.Series(dtype=float)), errors="coerce").nunique()) if not combined.empty else 0
    eligible_games = int(eligible["gamePk"].nunique())
    receipt = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "eligible_games": eligible_games,
        "covered_games": covered_games,
        "remaining_games": max(eligible_games - covered_games, 0),
        "new_games_attempted": int(len(todo)),
        "new_player_game_rows": int(appended),
        "new_player_rows_seen_from_official_boxscores": int(len(new_rows)),
        "original_official_source_csv_rewritten": False,
        "ledger_rows": int(len(combined)),
        "feature_rows": int(len(features)),
        "errors": errors,
        "leakage_rule": "All pregame rolling/season features use shift(1); current-game outcomes are excluded.",
        "status": "PASS" if not errors else "PARTIAL",
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
