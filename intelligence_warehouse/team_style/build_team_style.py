#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import json
import math
import time

import pandas as pd
import requests

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "team_style"
RAW = OUT / "raw"
OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

STYLE_OUT = OUT / "TEAM_STYLE_CURRENT.csv"
COACH_OUT = OUT / "COACHING_STYLE_CONTEXT_CURRENT.csv"
SOURCE_OUT = OUT / "TEAM_STYLE_SOURCE_CATALOG.csv"
FEATURE_OUT = OUT / "TEAM_STYLE_FEATURE_CATALOG.csv"
RECEIPT_OUT = OUT / "TEAM_STYLE_RECEIPT.json"

NOW = datetime.now(timezone.utc)
HEADERS = {"User-Agent": "Sports-HULK/1.0 team-style"}
def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text

def num(value):
    try:
        return float(value)
    except Exception:
        return None

def safe_div(a, b):
    a = num(a)
    b = num(b)
    if a is None or b in (None, 0):
        return None
    return a / b

def pct_decimal(value):
    value = num(value)
    if value is None:
        return None
    return value / 100.0 if abs(value) > 1.5 else value

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if Path(path).exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
def cache_json(url, name, ttl_minutes):
    path = RAW / name
    if path.exists():
        age = (time.time() - path.stat().st_mtime) / 60.0
        if age <= ttl_minutes:
            try:
                return json.loads(path.read_text()), "CACHE"
            except Exception:
                pass
    response = requests.get(url, headers=HEADERS, timeout=12)
    response.raise_for_status()
    payload = response.json()
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return payload, "LIVE"

def espn_stats_map(payload):
    stats = {}
    try:
        categories = payload["results"]["stats"]["categories"]
    except Exception:
        return stats
    for category in categories:
        for item in category.get("stats") or []:
            name = clean(item.get("name"))
            if not name:
                continue
            stats[name] = item.get("value")
            if item.get("perGameValue") is not None:
                stats[name + "__per_game"] = item.get("perGameValue")
    return stats

def percentile_signal(series, high_label, low_label, middle_label):
    values = pd.to_numeric(series, errors="coerce")
    q25 = values.quantile(0.25)
    q75 = values.quantile(0.75)
    return values.apply(
        lambda x: high_label if pd.notna(x) and x >= q75
        else low_label if pd.notna(x) and x <= q25
        else middle_label if pd.notna(x) else "LIMITED_SAMPLE"
    )
STYLE_COLUMNS = [
    "sport", "team_id", "team", "team_name", "season_basis", "sample_stage",
    "games", "coach", "primary_style", "tempo_signal", "play_mix_signal",
    "concentration_signal", "pass_rate", "rush_rate", "plays_per_game",
    "points_per_game", "yards_per_game", "possession_minutes_per_game",
    "offensive_epa_per_play", "explosive_play_rate", "top_target_share",
    "top3_target_share", "top_carry_share", "estimated_possessions_per_game",
    "three_point_attempt_rate", "free_throw_rate", "turnover_rate",
    "offensive_rebounds_per_game", "assist_to_turnover_ratio",
    "shots_for_per_game", "shots_against_per_game", "shot_environment_per_game",
    "shooting_pct", "faceoff_pct", "penalty_minutes_per_game",
    "runs_per_game", "home_runs_per_game", "stolen_bases_per_game",
    "walks_per_game", "strikeouts_per_game", "obp", "slg", "ops",
    "pitches_per_plate_appearance", "source", "source_tier", "generated_at",
    "automatic_model_adjustment", "score_is_probability",
]

def style_row(**kwargs):
    row = {column: None for column in STYLE_COLUMNS}
    row.update(kwargs)
    row["generated_at"] = NOW.isoformat()
    row["automatic_model_adjustment"] = False
    row["score_is_probability"] = False
    return row
def build_nfl():
    path = ROOT / "nfl_live" / "player_context" / "raw" / "player_stats.parquet"
    if not path.exists():
        return [], [], {"status": "MISSING_PLAYER_STATS"}

    players = pd.read_parquet(path)
    players = players[
        (players["season"] == 2026)
        & (players["season_type"].astype(str).str.upper() == "REG")
    ].copy()
    if players.empty:
        return [], [], {"status": "NO_CURRENT_ROWS"}

    numeric = [
        "attempts", "sacks_suffered", "carries", "passing_epa", "rushing_epa",
        "passing_20", "rushing_20", "targets",
    ]
    for col in numeric:
        players[col] = pd.to_numeric(players[col], errors="coerce").fillna(0)

    game = players.groupby(
        ["team", "game_id", "week"], as_index=False
    ).agg({
        "attempts": "sum",
        "sacks_suffered": "sum",
        "carries": "sum",
        "passing_epa": "sum",
        "rushing_epa": "sum",
        "passing_20": "sum",
        "rushing_20": "sum",
    })
    game["dropbacks"] = game["attempts"] + game["sacks_suffered"]
    game["plays"] = game["dropbacks"] + game["carries"]
    game["pass_rate"] = game["dropbacks"] / game["plays"].replace(0, pd.NA)
    game["epa"] = game["passing_epa"] + game["rushing_epa"]
    game["explosives"] = game["passing_20"] + game["rushing_20"]

    season = game.groupby("team", as_index=False).agg(
        games=("game_id", "nunique"),
        dropbacks=("dropbacks", "sum"),
        carries=("carries", "sum"),
        plays=("plays", "sum"),
        epa=("epa", "sum"),
        explosives=("explosives", "sum"),
    )
    season["pass_rate"] = season["dropbacks"] / season["plays"].replace(0, pd.NA)
    season["rush_rate"] = season["carries"] / season["plays"].replace(0, pd.NA)
    season["plays_per_game"] = season["plays"] / season["games"].replace(0, pd.NA)
    season["offensive_epa_per_play"] = season["epa"] / season["plays"].replace(0, pd.NA)
    season["explosive_play_rate"] = season["explosives"] / season["plays"].replace(0, pd.NA)

    usage = players.groupby(
        ["team", "player_id", "player_display_name"], as_index=False
    ).agg(targets=("targets", "sum"), carries=("carries", "sum"))
    concentration = {}
    for team, frame in usage.groupby("team"):
        target_total = frame["targets"].sum()
        carry_total = frame["carries"].sum()
        targets = frame["targets"].sort_values(ascending=False)
        carries = frame["carries"].sort_values(ascending=False)
        concentration[team] = {
            "top_target_share": safe_div(targets.iloc[0] if len(targets) else 0, target_total),
            "top3_target_share": safe_div(targets.head(3).sum(), target_total),
            "top_carry_share": safe_div(carries.iloc[0] if len(carries) else 0, carry_total),
        }

    schedule_files = sorted(glob.glob(str(
        ROOT / "nfl_live" / "context_cache" / "NFLVERSE_SCHEDULES_*.csv"
    )))
    coaches_2026 = {}
    coaches_2025 = {}
    team_names = {}
    if schedule_files:
        schedules = pd.read_csv(schedule_files[-1], low_memory=False)
        for season_year, target in [(2025, coaches_2025), (2026, coaches_2026)]:
            subset = schedules[schedules["season"] == season_year].copy()
            subset["gameday"] = pd.to_datetime(subset["gameday"], errors="coerce")
            subset = subset.sort_values(["gameday", "week"])
            for r in subset.itertuples():
                target[clean(r.home_team)] = clean(r.home_coach)
                target[clean(r.away_team)] = clean(r.away_coach)
    try:
        payload, _ = cache_json(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=100",
            "nfl_teams.json",
            1440,
        )
        for item in payload.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            team = item.get("team") or {}
            team_names[clean(team.get("abbreviation"))] = clean(team.get("displayName"))
    except Exception:
        pass

    rows = []
    coach_rows = []
    for r in season.itertuples():
        team = clean(r.team)
        conc = concentration.get(team, {})
        rows.append(style_row(
            sport="NFL",
            team_id=team,
            team=team,
            team_name=team_names.get(team, team),
            season_basis="2026_REGULAR_SEASON",
            sample_stage="CURRENT_SEASON_LIVE",
            games=int(r.games),
            coach=coaches_2026.get(team, ""),
            pass_rate=r.pass_rate,
            rush_rate=r.rush_rate,
            plays_per_game=r.plays_per_game,
            offensive_epa_per_play=r.offensive_epa_per_play,
            explosive_play_rate=r.explosive_play_rate,
            top_target_share=conc.get("top_target_share"),
            top3_target_share=conc.get("top3_target_share"),
            top_carry_share=conc.get("top_carry_share"),
            source="NFLVERSE_PLAYER_STATS_2026",
            source_tier="CURRENT_STRUCTURED_STATS",
        ))
        current_coach = coaches_2026.get(team, "")
        prior_coach = coaches_2025.get(team, "")
        if current_coach and prior_coach:
            continuity = "NEW_REGIME" if current_coach != prior_coach else "COACH_CONTINUITY"
        else:
            continuity = "COACH_UNKNOWN"
        coach_rows.append({
            "sport": "NFL",
            "team": team,
            "team_name": team_names.get(team, team),
            "current_coach": current_coach,
            "prior_season_coach": prior_coach,
            "coach_continuity_signal": continuity,
            "coach_changed_from_prior_season": (
                current_coach != prior_coach if current_coach and prior_coach else None
            ),
            "current_games": int(r.games),
            "current_pass_rate": r.pass_rate,
            "current_plays_per_game": r.plays_per_game,
            "current_top_target_share": conc.get("top_target_share"),
            "current_top_carry_share": conc.get("top_carry_share"),
            "source": "NFLVERSE_SCHEDULES_AND_PLAYER_STATS",
            "generated_at": NOW.isoformat(),
            "automatic_model_adjustment": False,
        })
    return rows, coach_rows, {
        "status": "CURRENT_SEASON_LIVE",
        "rows": len(rows),
        "games": int(game["game_id"].nunique()),
    }
def fetch_many_stats(requests_spec, max_workers=16):
    results = {}
    errors = []
    def one(item):
        key, url, cache_name, ttl = item
        payload, mode = cache_json(url, cache_name, ttl)
        return key, payload, mode
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(one, item): item[0] for item in requests_spec}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result_key, payload, mode = future.result()
                results[result_key] = (payload, mode)
            except Exception as exc:
                errors.append({"key": clean(key), "error": repr(exc)})
    return results, errors

def build_cfb():
    teams = read_csv(
        ROOT / "intelligence_warehouse" / "cfb_roster"
        / "CFB_ROSTER_CONTINUITY_CURRENT.csv"
    )
    if teams.empty:
        return [], {"status": "MISSING_TEAM_LIST", "errors": []}

    specs = []
    metadata = {}
    for r in teams.itertuples():
        team_id = int(r.team_id)
        metadata[str(team_id)] = {
            "team": clean(r.team),
            "team_name": clean(r.team_name),
        }
        specs.append((
            str(team_id),
            "https://site.api.espn.com/apis/site/v2/sports/football/"
            f"college-football/teams/{team_id}/statistics?season=2026",
            f"cfb_{team_id}_2026_stats.json",
            180,
        ))
    fetched, errors = fetch_many_stats(specs)
    rows = []
    modes = []
    for team_id, (payload, mode) in fetched.items():
        stats = espn_stats_map(payload)
        meta = metadata.get(team_id, {})
        games = num(stats.get("gamesPlayed")) or num(stats.get("teamGamesPlayed"))
        pass_attempts = num(stats.get("passingAttempts"))
        rush_attempts = num(stats.get("rushingAttempts"))
        play_mix_total = (
            (pass_attempts or 0) + (rush_attempts or 0)
            if pass_attempts is not None or rush_attempts is not None else None
        )
        total_plays = num(stats.get("totalOffensivePlays"))
        possession = num(stats.get("possessionTimeSeconds"))
        rows.append(style_row(
            sport="CFB",
            team_id=team_id,
            team=meta.get("team", team_id),
            team_name=meta.get("team_name", meta.get("team", team_id)),
            season_basis="2026_REGULAR_SEASON",
            sample_stage="CURRENT_SEASON_LIVE",
            games=games,
            pass_rate=safe_div(pass_attempts, play_mix_total),
            rush_rate=safe_div(rush_attempts, play_mix_total),
            plays_per_game=safe_div(total_plays, games),
            points_per_game=num(stats.get("totalPointsPerGame")),
            yards_per_game=num(stats.get("yardsPerGame")),
            possession_minutes_per_game=safe_div(possession, games * 60 if games else None),
            source="ESPN_CFB_TEAM_STATS",
            source_tier="CURRENT_STRUCTURED_TEAM_STATS",
        ))
        modes.append(mode)
    return rows, {
        "status": "CURRENT_SEASON_LIVE",
        "rows": len(rows),
        "errors": errors,
        "live_fetches": modes.count("LIVE"),
        "cache_hits": modes.count("CACHE"),
    }
def espn_team_list(league_path, cache_name):
    payload, _ = cache_json(
        f"https://site.api.espn.com/apis/site/v2/sports/{league_path}/teams?limit=100",
        cache_name,
        1440,
    )
    rows = []
    try:
        items = payload["sports"][0]["leagues"][0]["teams"]
    except Exception:
        items = []
    for item in items:
        team = item.get("team") or {}
        rows.append({
            "id": clean(team.get("id")),
            "team": clean(team.get("abbreviation")),
            "team_name": clean(team.get("displayName")),
        })
    return rows

def build_nba():
    teams = espn_team_list("basketball/nba", "nba_teams.json")
    specs = [
        (
            t["id"],
            "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/"
            f"teams/{t['id']}/statistics?season=2026",
            f"nba_{t['id']}_2026_stats.json",
            1440,
        )
        for t in teams if t["id"]
    ]
    fetched, errors = fetch_many_stats(specs)
    meta = {t["id"]: t for t in teams}
    rows = []
    modes = []
    for team_id, (payload, mode) in fetched.items():
        s = espn_stats_map(payload)
        t = meta.get(team_id, {})
        games = num(s.get("gamesPlayed"))
        fga = num(s.get("avgFieldGoalsAttempted"))
        oreb = num(s.get("avgOffensiveRebounds"))
        turnovers = num(s.get("avgTurnovers"))
        fta = num(s.get("avgFreeThrowsAttempted"))
        three_pa = num(s.get("avgThreePointFieldGoalsAttempted"))
        possessions = None
        if None not in (fga, oreb, turnovers, fta):
            possessions = fga - oreb + turnovers + (0.44 * fta)
        rows.append(style_row(
            sport="NBA",
            team_id=team_id,
            team=t.get("team", team_id),
            team_name=t.get("team_name", t.get("team", team_id)),
            season_basis="2025_26_PRIOR_SEASON",
            sample_stage="PRIOR_SEASON_BASELINE",
            games=games,
            points_per_game=num(s.get("avgPoints")),
            estimated_possessions_per_game=possessions,
            three_point_attempt_rate=safe_div(three_pa, fga),
            free_throw_rate=safe_div(fta, fga),
            turnover_rate=safe_div(turnovers, possessions),
            offensive_rebounds_per_game=oreb,
            assist_to_turnover_ratio=num(s.get("assistTurnoverRatio")),
            source="ESPN_NBA_TEAM_STATS",
            source_tier="PRIOR_SEASON_STRUCTURED_TEAM_STATS",
        ))
        modes.append(mode)
    return rows, {
        "status": "PRIOR_SEASON_BASELINE",
        "rows": len(rows), "errors": errors,
        "live_fetches": modes.count("LIVE"), "cache_hits": modes.count("CACHE"),
    }
def build_nhl():
    teams = espn_team_list("hockey/nhl", "nhl_teams.json")
    specs = [
        (
            t["id"],
            "https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/"
            f"teams/{t['id']}/statistics?season=2026",
            f"nhl_{t['id']}_2026_stats.json",
            1440,
        )
        for t in teams if t["id"]
    ]
    fetched, errors = fetch_many_stats(specs)
    meta = {t["id"]: t for t in teams}
    rows = []
    modes = []
    for team_id, (payload, mode) in fetched.items():
        s = espn_stats_map(payload)
        t = meta.get(team_id, {})
        games = num(s.get("games"))
        shots_for = safe_div(s.get("shotsTotal"), games)
        shots_against = safe_div(s.get("shotsAgainst"), games)
        rows.append(style_row(
            sport="NHL",
            team_id=team_id,
            team=t.get("team", team_id),
            team_name=t.get("team_name", t.get("team", team_id)),
            season_basis="2025_26_PRIOR_SEASON",
            sample_stage="PRIOR_SEASON_BASELINE",
            games=games,
            points_per_game=safe_div(s.get("goals"), games),
            shots_for_per_game=shots_for,
            shots_against_per_game=shots_against,
            shot_environment_per_game=(
                shots_for + shots_against
                if shots_for is not None and shots_against is not None else None
            ),
            shooting_pct=pct_decimal(s.get("shootingPct")),
            faceoff_pct=pct_decimal(s.get("faceoffPercent")),
            penalty_minutes_per_game=safe_div(s.get("penaltyMinutes"), games),
            source="ESPN_NHL_TEAM_STATS",
            source_tier="PRIOR_SEASON_STRUCTURED_TEAM_STATS",
        ))
        modes.append(mode)
    return rows, {
        "status": "PRIOR_SEASON_BASELINE",
        "rows": len(rows), "errors": errors,
        "live_fetches": modes.count("LIVE"), "cache_hits": modes.count("CACHE"),
    }
def build_mlb():
    teams_payload, team_mode = cache_json(
        "https://statsapi.mlb.com/api/v1/teams?sportId=1&season=2026",
        "mlb_active_teams_2026.json",
        1440,
    )
    team_map = {
        str(team.get("id")): clean(team.get("name"))
        for team in teams_payload.get("teams") or []
        if team.get("id") is not None and team.get("active") is not False
    }
    if len(team_map) != 30:
        return [], {
            "status": "TEAM_LIST_VALIDATION_FAILED",
            "errors": [{"expected": 30, "actual": len(team_map)}],
        }

    specs = [
        (
            team_id,
            f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats"
            "?stats=season&group=hitting&season=2026",
            f"mlb_{team_id}_2026_hitting.json",
            60,
        )
        for team_id in team_map
    ]
    fetched, errors = fetch_many_stats(specs)
    rows = []
    modes = []
    for team_id, (payload, mode) in fetched.items():
        splits = []
        for block in payload.get("stats") or []:
            splits.extend(block.get("splits") or [])
        stat = (splits[0].get("stat") if splits else {}) or {}
        team_name = team_map.get(team_id, team_id)
        games_played = num(stat.get("gamesPlayed"))
        rows.append(style_row(
            sport="MLB",
            team_id=team_id,
            team=team_name,
            team_name=team_name,
            season_basis="2026_REGULAR_SEASON",
            sample_stage="CURRENT_SEASON_LIVE",
            games=games_played,
            runs_per_game=safe_div(stat.get("runs"), games_played),
            home_runs_per_game=safe_div(stat.get("homeRuns"), games_played),
            stolen_bases_per_game=safe_div(stat.get("stolenBases"), games_played),
            walks_per_game=safe_div(stat.get("baseOnBalls"), games_played),
            strikeouts_per_game=safe_div(stat.get("strikeOuts"), games_played),
            obp=num(stat.get("obp")),
            slg=num(stat.get("slg")),
            ops=num(stat.get("ops")),
            pitches_per_plate_appearance=safe_div(
                stat.get("numberOfPitches"), stat.get("plateAppearances")
            ),
            source="MLB_STATSAPI_TEAM_HITTING",
            source_tier="OFFICIAL_CURRENT_TEAM_STATS",
        ))
        modes.append(mode)
    return rows, {
        "status": "CURRENT_SEASON_LIVE",
        "rows": len(rows), "errors": errors,
        "live_fetches": modes.count("LIVE") + (1 if team_mode == "LIVE" else 0),
        "cache_hits": modes.count("CACHE") + (1 if team_mode == "CACHE" else 0),
    }
def build_cbb():
    data = read_csv(
        ROOT / "intelligence_warehouse" / "cbb_efficiency"
        / "CBB_EFFICIENCY_CURRENT.csv"
    )
    if data.empty:
        return [], {"status": "MISSING_CBB_EFFICIENCY"}
    rows = []
    for r in data.itertuples():
        rows.append(style_row(
            sport="CBB",
            team_id=clean(r.team_id),
            team=clean(r.team),
            team_name=clean(r.team_name),
            season_basis="2025_26_PRIOR_SEASON",
            sample_stage=clean(r.context_stage),
            games=num(r.prior_games),
            estimated_possessions_per_game=num(r.prior_tempo_possessions_per_game),
            three_point_attempt_rate=num(r.prior_three_point_attempt_rate),
            free_throw_rate=num(r.prior_free_throw_rate),
            turnover_rate=num(r.prior_turnover_pct),
            source="HULK_CBB_EFFICIENCY_BASELINE",
            source_tier="DERIVED_POSSESSION_BASELINE",
        ))
    return rows, {"status": "PRESEASON_BASELINE", "rows": len(rows)}
def apply_style_labels(style):
    if style.empty:
        return style

    style["tempo_signal"] = "NOT_MODELED"
    style["play_mix_signal"] = "NOT_MODELED"
    style["concentration_signal"] = "NOT_MODELED"

    for sport in style["sport"].dropna().unique():
        mask = style["sport"] == sport
        frame = style.loc[mask]

        if sport in {"NFL", "CFB"}:
            style.loc[mask, "tempo_signal"] = percentile_signal(
                frame["plays_per_game"], "HIGH_VOLUME", "LOW_VOLUME", "NORMAL_VOLUME"
            ).values
            style.loc[mask, "play_mix_signal"] = percentile_signal(
                frame["pass_rate"], "PASS_HEAVY", "RUN_HEAVY", "BALANCED"
            ).values
        elif sport in {"NBA", "CBB"}:
            style.loc[mask, "tempo_signal"] = percentile_signal(
                frame["estimated_possessions_per_game"],
                "FAST_PACE", "SLOW_PACE", "MID_PACE",
            ).values
            style.loc[mask, "play_mix_signal"] = percentile_signal(
                frame["three_point_attempt_rate"],
                "THREE_POINT_HEAVY", "TWO_POINT_HEAVY", "BALANCED_SHOT_MIX",
            ).values
        elif sport == "NHL":
            style.loc[mask, "tempo_signal"] = percentile_signal(
                frame["shot_environment_per_game"],
                "HIGH_EVENT", "LOW_EVENT", "MID_EVENT",
            ).values
            style.loc[mask, "play_mix_signal"] = percentile_signal(
                frame["shots_for_per_game"],
                "SHOT_VOLUME_HEAVY", "LOW_SHOT_VOLUME", "MID_SHOT_VOLUME",
            ).values
        elif sport == "MLB":
            style.loc[mask, "tempo_signal"] = percentile_signal(
                frame["pitches_per_plate_appearance"],
                "PATIENT_AT_BATS", "EARLY_COUNT_CONTACT", "MID_COUNT_PROFILE",
            ).values
            style.loc[mask, "play_mix_signal"] = percentile_signal(
                frame["home_runs_per_game"],
                "POWER_HEAVY", "LOW_POWER", "MID_POWER",
            ).values
    nfl_mask = style["sport"] == "NFL"
    if nfl_mask.any():
        target_signal = percentile_signal(
            style.loc[nfl_mask, "top_target_share"],
            "TARGET_CONCENTRATED", "TARGET_DISTRIBUTED", "MID_TARGET_CONCENTRATION",
        )
        carry_signal = percentile_signal(
            style.loc[nfl_mask, "top_carry_share"],
            "CARRY_CONCENTRATED", "CARRY_DISTRIBUTED", "MID_CARRY_CONCENTRATION",
        )
        combined = []
        for target, carry in zip(target_signal, carry_signal):
            if "CONCENTRATED" in target or "CONCENTRATED" in carry:
                combined.append("USAGE_CONCENTRATED")
            elif "DISTRIBUTED" in target and "DISTRIBUTED" in carry:
                combined.append("USAGE_DISTRIBUTED")
            else:
                combined.append("MID_USAGE_CONCENTRATION")
        style.loc[nfl_mask, "concentration_signal"] = combined

    style["primary_style"] = (
        style["tempo_signal"].astype(str)
        + "|" + style["play_mix_signal"].astype(str)
        + "|" + style["concentration_signal"].astype(str)
    )
    return style
FEATURES = [
    ("NFL", "pass_rate", "Dropbacks divided by estimated offensive plays.", "CURRENT"),
    ("NFL", "plays_per_game", "Estimated offensive plays per game.", "CURRENT"),
    ("NFL", "offensive_epa_per_play", "Player-stat passing+rushing EPA divided by estimated plays.", "CURRENT"),
    ("NFL", "explosive_play_rate", "20+ yard pass/rush plays divided by estimated plays.", "CURRENT"),
    ("NFL", "top_target_share", "Season target share of the most-targeted player.", "CURRENT"),
    ("NFL", "top_carry_share", "Season carry share of the highest-volume rusher.", "CURRENT"),
    ("CFB", "pass_rate", "Pass attempts divided by pass+rush attempts.", "CURRENT"),
    ("CFB", "plays_per_game", "Official total offensive plays divided by games.", "CURRENT"),
    ("NBA", "estimated_possessions_per_game", "FGA-OREB+TO+0.44*FTA possession estimate; not official NBA Pace.", "PRIOR_BASELINE"),
    ("NBA", "three_point_attempt_rate", "Three-point attempts divided by field-goal attempts.", "PRIOR_BASELINE"),
    ("NHL", "shot_environment_per_game", "Team shots for plus shots against per game.", "PRIOR_BASELINE"),
    ("NHL", "penalty_minutes_per_game", "Penalty minutes divided by games.", "PRIOR_BASELINE"),
    ("MLB", "home_runs_per_game", "Home runs divided by games played.", "CURRENT"),
    ("MLB", "stolen_bases_per_game", "Stolen bases divided by games played.", "CURRENT"),
    ("MLB", "pitches_per_plate_appearance", "Pitches seen divided by plate appearances.", "CURRENT"),
    ("CBB", "estimated_possessions_per_game", "Existing HULK prior-season possession baseline.", "PRIOR_BASELINE"),
    ("CBB", "three_point_attempt_rate", "Prior-season three-point attempt rate.", "PRIOR_BASELINE"),
]

def feature_catalog():
    return pd.DataFrame([
        {
            "sport": sport,
            "feature": feature,
            "definition": definition,
            "data_stage": stage,
            "score_is_probability": False,
            "automatic_model_adjustment": False,
        }
        for sport, feature, definition, stage in FEATURES
    ])
builders = [
    ("NFL", build_nfl),
    ("CFB", build_cfb),
    ("NBA", build_nba),
    ("NHL", build_nhl),
    ("MLB", build_mlb),
    ("CBB", build_cbb),
]

all_rows = []
coach_rows = []
source_rows = []
all_errors = []

for sport, builder in builders:
    try:
        result = builder()
        if sport == "NFL":
            rows, coaches, meta = result
            coach_rows.extend(coaches)
        else:
            rows, meta = result
        all_rows.extend(rows)
        errors = meta.get("errors", []) if isinstance(meta, dict) else []
        all_errors.extend([{"sport": sport, **e} for e in errors])
        source_rows.append({
            "sport": sport,
            "status": meta.get("status", "UNKNOWN"),
            "rows": int(meta.get("rows", len(rows))),
            "live_fetches": int(meta.get("live_fetches", 0)),
            "cache_hits": int(meta.get("cache_hits", 0)),
            "error_count": len(errors),
            "generated_at": NOW.isoformat(),
        })
    except Exception as exc:
        all_errors.append({"sport": sport, "error": repr(exc)})
        source_rows.append({
            "sport": sport,
            "status": "ERROR",
            "rows": 0,
            "live_fetches": 0,
            "cache_hits": 0,
            "error_count": 1,
            "generated_at": NOW.isoformat(),
        })

style = pd.DataFrame(all_rows, columns=STYLE_COLUMNS)
style = apply_style_labels(style)
coaching = pd.DataFrame(coach_rows)
sources = pd.DataFrame(source_rows)

source_meta = {
    "NFL": ("NFLVERSE_PLAYER_STATS_2026 + NFLVERSE_SCHEDULES", "CURRENT"),
    "CFB": ("ESPN_CFB_TEAM_STATS", "CURRENT"),
    "NBA": ("ESPN_NBA_TEAM_STATS_2025_26", "PRIOR_BASELINE"),
    "NHL": ("ESPN_NHL_TEAM_STATS_2025_26", "PRIOR_BASELINE"),
    "MLB": ("MLB_STATSAPI_TEAM_HITTING_2026", "CURRENT"),
    "CBB": ("HULK_CBB_EFFICIENCY_BASELINE", "PRIOR_BASELINE"),
}
sources["primary_source"] = sources["sport"].map(
    lambda sport: source_meta.get(sport, ("UNKNOWN", "UNKNOWN"))[0]
)
sources["data_stage"] = sources["sport"].map(
    lambda sport: source_meta.get(sport, ("UNKNOWN", "UNKNOWN"))[1]
)
sources["paid_provider_required"] = False
features = feature_catalog()
style.to_csv(STYLE_OUT, index=False)
coaching.to_csv(COACH_OUT, index=False)
sources.to_csv(SOURCE_OUT, index=False)
features.to_csv(FEATURE_OUT, index=False)

sport_counts = (
    style["sport"].value_counts().to_dict() if not style.empty else {}
)
stage_counts = (
    style["sample_stage"].value_counts().to_dict() if not style.empty else {}
)
tempo_counts = (
    style.groupby(["sport", "tempo_signal"]).size().to_dict()
    if not style.empty else {}
)
mix_counts = (
    style.groupby(["sport", "play_mix_signal"]).size().to_dict()
    if not style.empty else {}
)

receipt = {
    "generated_at": NOW.isoformat(),
    "team_style_rows": len(style),
    "coaching_context_rows": len(coaching),
    "feature_catalog_rows": len(features),
    "rows_by_sport": {str(k): int(v) for k, v in sport_counts.items()},
    "sample_stage_counts": {str(k): int(v) for k, v in stage_counts.items()},
    "tempo_signal_counts": {
        f"{sport}:{signal}": int(count)
        for (sport, signal), count in tempo_counts.items()
    },
    "play_mix_signal_counts": {
        f"{sport}:{signal}": int(count)
        for (sport, signal), count in mix_counts.items()
    },
    "source_status": {
        row["sport"]: row["status"] for row in source_rows
    },
    "current_coaching_identity_available": ["NFL"],
    "explicit_gaps": [
        "NFL pass rate is raw observed dropback mix, not situation-neutral pass rate.",
        "CFB pass rate is aggregate pass/rush attempt mix, not situation-neutral play calling.",
        "NBA estimated possessions are a transparent box-score estimate, not official NBA Pace.",
        "NBA and NHL use completed 2025-26 baselines until 2026-27 regular-season samples mature.",
        "NHL event style does not yet include zone-entry or EDGE spatial tracking.",
        "MLB style is team offensive identity; tactical bunt/steal decision propensity is not yet modeled.",
        "CBB uses the existing prior-season possession/efficiency baseline during preseason.",
        "Named coaching-regime context is currently modeled only for NFL.",
    ],
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
    "errors": all_errors,
}
RECEIPT_OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("TEAM STYLE ROWS:", len(style))
print("BY SPORT:", receipt["rows_by_sport"])
print("STAGES:", receipt["sample_stage_counts"])
print("COACHING CONTEXT:", len(coaching))
print("SOURCE STATUS:", receipt["source_status"])
print("ERRORS:", len(all_errors))
print("RESULT: TEAM_STYLE_READY")
