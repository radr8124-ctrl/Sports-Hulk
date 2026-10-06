#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "matchup_style"
OUT.mkdir(parents=True, exist_ok=True)

STYLE_FILE = ROOT / "intelligence_warehouse" / "team_style" / "TEAM_STYLE_CURRENT.csv"
COACH_FILE = ROOT / "intelligence_warehouse" / "team_style" / "COACHING_STYLE_CONTEXT_CURRENT.csv"

CURRENT_OUT = OUT / "MATCHUP_STYLE_CURRENT.csv"
SOURCE_OUT = OUT / "MATCHUP_STYLE_SOURCE_CATALOG.csv"
FEATURE_OUT = OUT / "MATCHUP_STYLE_FEATURE_CATALOG.csv"
RECEIPT_OUT = OUT / "MATCHUP_STYLE_RECEIPT.json"

NOW = datetime.now(timezone.utc)
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

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())

def num(value):
    try:
        return float(value)
    except Exception:
        return None

def mean2(a, b):
    vals = [x for x in [num(a), num(b)] if x is not None]
    return sum(vals) / len(vals) if vals else None

def absdiff(a, b):
    a = num(a)
    b = num(b)
    return abs(a - b) if a is not None and b is not None else None

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if Path(path).exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()
NFL_FULL_TO_ABBR = {
    "Arizona Cardinals":"ARI","Atlanta Falcons":"ATL","Baltimore Ravens":"BAL",
    "Buffalo Bills":"BUF","Carolina Panthers":"CAR","Chicago Bears":"CHI",
    "Cincinnati Bengals":"CIN","Cleveland Browns":"CLE","Dallas Cowboys":"DAL",
    "Denver Broncos":"DEN","Detroit Lions":"DET","Green Bay Packers":"GB",
    "Houston Texans":"HOU","Indianapolis Colts":"IND","Jacksonville Jaguars":"JAX",
    "Kansas City Chiefs":"KC","Las Vegas Raiders":"LV","Los Angeles Chargers":"LAC",
    "Los Angeles Rams":"LA","Miami Dolphins":"MIA","Minnesota Vikings":"MIN",
    "New England Patriots":"NE","New Orleans Saints":"NO","New York Giants":"NYG",
    "New York Jets":"NYJ","Philadelphia Eagles":"PHI","Pittsburgh Steelers":"PIT",
    "San Francisco 49ers":"SF","Seattle Seahawks":"SEA","Tampa Bay Buccaneers":"TB",
    "Tennessee Titans":"TEN","Washington Commanders":"WAS",
}

NHL_ALIAS = {
    "LAK":"LA","NJD":"NJ","SJS":"SJ","TBL":"TB","UTA":"UTAH",
}

def normalize_team_key(sport, value):
    text = clean(value)
    if sport == "NFL":
        return NFL_FULL_TO_ABBR.get(text, text)
    if sport == "NHL":
        return NHL_ALIAS.get(text, text)
    return text
style = read_csv(STYLE_FILE)
coaching = read_csv(COACH_FILE)
if style.empty:
    raise SystemExit("TEAM_STYLE_CURRENT.csv is missing or empty")

style_lookup = {}
for row in style.to_dict("records"):
    sport = clean(row.get("sport")).upper()
    keys = {
        normalize_team_key(sport, row.get("team")),
        clean(row.get("team_id")),
        clean(row.get("team_name")),
    }
    for key in keys:
        if not key:
            continue
        style_lookup[(sport, norm(key))] = row

coach_lookup = {}
if not coaching.empty:
    for row in coaching.to_dict("records"):
        coach_lookup[("NFL", norm(row.get("team")))] = row

def get_style(sport, team_value=None, team_id=None, team_name=None):
    sport = clean(sport).upper()
    candidates = [
        clean(team_id),
        normalize_team_key(sport, team_value),
        clean(team_name),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        found = style_lookup.get((sport, norm(candidate)))
        if found:
            return found
    return None
def schedule_games():
    games = []

    nfl = read_csv(ROOT / "nfl_live" / "derived" / "NFL_CURRENT_WEEK.csv")
    for r in nfl.itertuples(index=False):
        games.append({
            "sport":"NFL","event_id":clean(r.event_id),"start":clean(r.start),
            "away_team":clean(r.away_team),"away_team_id":"","away_team_name":clean(r.away_team),
            "home_team":clean(r.home_team),"home_team_id":"","home_team_name":clean(r.home_team),
            "schedule_source":"NFL_CURRENT_WEEK",
        })

    cfb = read_csv(ROOT / "cfb_live" / "derived" / "CFB_GAMES_CURRENT.csv")
    if not cfb.empty:
        cfb = cfb[cfb["status_state"].astype(str).eq("pre")]
        for r in cfb.itertuples(index=False):
            games.append({
                "sport":"CFB","event_id":clean(r.event_id),"start":clean(r.start),
                "away_team":clean(r.away_team),"away_team_id":clean(r.away_team_id),"away_team_name":clean(r.away_team_name),
                "home_team":clean(r.home_team),"home_team_id":clean(r.home_team_id),"home_team_name":clean(r.home_team_name),
                "schedule_source":"CFB_GAMES_CURRENT",
            })
    nba = read_csv(ROOT / "nba_live" / "derived" / "NBA_GAMES_CURRENT.csv")
    if not nba.empty:
        nba = nba[nba["status_state"].astype(str).eq("pre")]
        for r in nba.itertuples(index=False):
            games.append({
                "sport":"NBA","event_id":clean(r.event_id),"start":clean(r.start),
                "away_team":clean(r.away_team),"away_team_id":clean(r.away_team_id),"away_team_name":clean(r.away_team_name),
                "home_team":clean(r.home_team),"home_team_id":clean(r.home_team_id),"home_team_name":clean(r.home_team_name),
                "schedule_source":"NBA_GAMES_CURRENT",
            })

    nhl = read_csv(ROOT / "nhl_live" / "derived" / "NHL_GAMES_CURRENT.csv")
    if not nhl.empty:
        nhl = nhl[~nhl["completed"].astype(str).str.lower().isin(["true","1"])]
        for r in nhl.itertuples(index=False):
            games.append({
                "sport":"NHL","event_id":clean(r.event_id),"start":clean(r.start),
                "away_team":clean(r.away_team),"away_team_id":clean(r.away_team_id),"away_team_name":clean(r.away_team_name),
                "home_team":clean(r.home_team),"home_team_id":clean(r.home_team_id),"home_team_name":clean(r.home_team_name),
                "schedule_source":"NHL_GAMES_CURRENT",
            })
    mlb = read_csv(ROOT / "baseball_vault" / "latest" / "MLB_SCHEDULE.csv")
    if not mlb.empty:
        mlb = mlb[mlb["abstractState"].astype(str).str.lower().eq("preview")]
        for r in mlb.itertuples(index=False):
            games.append({
                "sport":"MLB","event_id":clean(r.gamePk),"start":clean(r.gameDate),
                "away_team":clean(r.away_team),"away_team_id":clean(r.away_team_id),"away_team_name":clean(r.away_team),
                "home_team":clean(r.home_team),"home_team_id":clean(r.home_team_id),"home_team_name":clean(r.home_team),
                "schedule_source":"MLB_SCHEDULE",
            })

    cbb = read_csv(ROOT / "cbb_live" / "derived" / "CBB_GAMES_CURRENT.csv")
    if not cbb.empty:
        cbb = cbb[cbb["status_state"].astype(str).eq("pre")]
        for r in cbb.itertuples(index=False):
            games.append({
                "sport":"CBB","event_id":clean(r.event_id),"start":clean(r.start),
                "away_team":clean(r.away_team),"away_team_id":clean(r.away_team_id),"away_team_name":clean(r.away_team_name),
                "home_team":clean(r.home_team),"home_team_id":clean(r.home_team_id),"home_team_name":clean(r.home_team_name),
                "schedule_source":"CBB_GAMES_CURRENT",
            })

    return games
def football_interactions(away, home):
    a_tempo = clean(away.get("tempo_signal"))
    h_tempo = clean(home.get("tempo_signal"))
    a_mix = clean(away.get("play_mix_signal"))
    h_mix = clean(home.get("play_mix_signal"))

    if a_tempo == h_tempo == "HIGH_VOLUME":
        pace = "DUAL_HIGH_VOLUME"
    elif a_tempo == h_tempo == "LOW_VOLUME":
        pace = "DUAL_LOW_VOLUME"
    elif {a_tempo, h_tempo} == {"HIGH_VOLUME", "LOW_VOLUME"}:
        pace = "VOLUME_CLASH"
    else:
        pace = "MIXED_VOLUME"

    if a_mix == h_mix == "PASS_HEAVY":
        mix = "DUAL_PASS_HEAVY"
    elif a_mix == h_mix == "RUN_HEAVY":
        mix = "DUAL_RUN_HEAVY"
    elif {a_mix, h_mix} == {"PASS_HEAVY", "RUN_HEAVY"}:
        mix = "PASS_RUN_STYLE_CLASH"
    elif "PASS_HEAVY" in {a_mix, h_mix}:
        mix = "ONE_SIDE_PASS_HEAVY"
    elif "RUN_HEAVY" in {a_mix, h_mix}:
        mix = "ONE_SIDE_RUN_HEAVY"
    else:
        mix = "BALANCED_MIX"

    return {
        "pace_interaction": pace,
        "play_mix_interaction": mix,
        "matchup_volume_proxy": mean2(away.get("plays_per_game"), home.get("plays_per_game")),
        "tempo_gap": absdiff(away.get("plays_per_game"), home.get("plays_per_game")),
        "play_mix_gap": absdiff(away.get("pass_rate"), home.get("pass_rate")),
    }
def basketball_interactions(away, home):
    a_tempo = clean(away.get("tempo_signal"))
    h_tempo = clean(home.get("tempo_signal"))
    a_mix = clean(away.get("play_mix_signal"))
    h_mix = clean(home.get("play_mix_signal"))

    if a_tempo == h_tempo == "FAST_PACE":
        pace = "DUAL_FAST_PACE"
    elif a_tempo == h_tempo == "SLOW_PACE":
        pace = "DUAL_SLOW_PACE"
    elif {a_tempo, h_tempo} == {"FAST_PACE", "SLOW_PACE"}:
        pace = "PACE_CLASH"
    else:
        pace = "MIXED_PACE"

    if a_mix == h_mix == "THREE_POINT_HEAVY":
        mix = "DUAL_THREE_POINT_HEAVY"
    elif a_mix == h_mix == "TWO_POINT_HEAVY":
        mix = "DUAL_TWO_POINT_HEAVY"
    elif {a_mix, h_mix} == {"THREE_POINT_HEAVY", "TWO_POINT_HEAVY"}:
        mix = "PERIMETER_INTERIOR_CLASH"
    elif "THREE_POINT_HEAVY" in {a_mix, h_mix}:
        mix = "ONE_SIDE_THREE_POINT_HEAVY"
    elif "TWO_POINT_HEAVY" in {a_mix, h_mix}:
        mix = "ONE_SIDE_TWO_POINT_HEAVY"
    else:
        mix = "BALANCED_SHOT_MIX"

    return {
        "pace_interaction": pace,
        "play_mix_interaction": mix,
        "matchup_volume_proxy": mean2(
            away.get("estimated_possessions_per_game"),
            home.get("estimated_possessions_per_game"),
        ),
        "tempo_gap": absdiff(
            away.get("estimated_possessions_per_game"),
            home.get("estimated_possessions_per_game"),
        ),
        "play_mix_gap": absdiff(
            away.get("three_point_attempt_rate"),
            home.get("three_point_attempt_rate"),
        ),
    }
def nhl_interactions(away, home):
    a_tempo = clean(away.get("tempo_signal"))
    h_tempo = clean(home.get("tempo_signal"))
    a_mix = clean(away.get("play_mix_signal"))
    h_mix = clean(home.get("play_mix_signal"))

    if a_tempo == h_tempo == "HIGH_EVENT":
        pace = "DUAL_HIGH_EVENT"
    elif a_tempo == h_tempo == "LOW_EVENT":
        pace = "DUAL_LOW_EVENT"
    elif {a_tempo, h_tempo} == {"HIGH_EVENT", "LOW_EVENT"}:
        pace = "EVENT_STYLE_CLASH"
    else:
        pace = "MIXED_EVENT_ENVIRONMENT"

    if a_mix == h_mix == "SHOT_VOLUME_HEAVY":
        mix = "DUAL_SHOT_VOLUME_HEAVY"
    elif a_mix == h_mix == "LOW_SHOT_VOLUME":
        mix = "DUAL_LOW_SHOT_VOLUME"
    elif {a_mix, h_mix} == {"SHOT_VOLUME_HEAVY", "LOW_SHOT_VOLUME"}:
        mix = "SHOT_VOLUME_CLASH"
    else:
        mix = "MIXED_SHOT_VOLUME"

    away_opportunity = mean2(
        away.get("shots_for_per_game"), home.get("shots_against_per_game")
    )
    home_opportunity = mean2(
        home.get("shots_for_per_game"), away.get("shots_against_per_game")
    )
    return {
        "pace_interaction": pace,
        "play_mix_interaction": mix,
        "away_opportunity_proxy": away_opportunity,
        "home_opportunity_proxy": home_opportunity,
        "matchup_volume_proxy": mean2(away_opportunity, home_opportunity),
        "tempo_gap": absdiff(
            away.get("shot_environment_per_game"),
            home.get("shot_environment_per_game"),
        ),
        "play_mix_gap": absdiff(
            away.get("shots_for_per_game"),
            home.get("shots_for_per_game"),
        ),
    }
def mlb_interactions(away, home):
    a_power = clean(away.get("play_mix_signal"))
    h_power = clean(home.get("play_mix_signal"))
    a_approach = clean(away.get("tempo_signal"))
    h_approach = clean(home.get("tempo_signal"))

    if a_power == h_power == "POWER_HEAVY":
        power = "DUAL_POWER_HEAVY"
    elif a_power == h_power == "LOW_POWER":
        power = "DUAL_LOW_POWER"
    elif {a_power, h_power} == {"POWER_HEAVY", "LOW_POWER"}:
        power = "POWER_STYLE_CLASH"
    elif "POWER_HEAVY" in {a_power, h_power}:
        power = "ONE_SIDE_POWER_HEAVY"
    elif "LOW_POWER" in {a_power, h_power}:
        power = "ONE_SIDE_LOW_POWER"
    else:
        power = "MID_POWER_PAIRING"

    if a_approach == h_approach == "PATIENT_AT_BATS":
        approach = "DUAL_PATIENT_APPROACH"
    elif a_approach == h_approach == "EARLY_COUNT_CONTACT":
        approach = "DUAL_EARLY_COUNT_CONTACT"
    elif {a_approach, h_approach} == {"PATIENT_AT_BATS", "EARLY_COUNT_CONTACT"}:
        approach = "PLATE_APPROACH_CLASH"
    else:
        approach = "MIXED_PLATE_APPROACH"

    return {
        "pace_interaction": approach,
        "play_mix_interaction": power,
        "matchup_volume_proxy": mean2(
            away.get("runs_per_game"), home.get("runs_per_game")
        ),
        "tempo_gap": absdiff(
            away.get("pitches_per_plate_appearance"),
            home.get("pitches_per_plate_appearance"),
        ),
        "play_mix_gap": absdiff(
            away.get("home_runs_per_game"),
            home.get("home_runs_per_game"),
        ),
    }
def usage_interaction(sport, away, home):
    if sport != "NFL":
        return "NOT_MODELED"
    a = clean(away.get("concentration_signal"))
    h = clean(home.get("concentration_signal"))
    if a == h == "USAGE_CONCENTRATED":
        return "DUAL_USAGE_CONCENTRATED"
    if "USAGE_CONCENTRATED" in {a, h}:
        return "ONE_SIDE_USAGE_CONCENTRATED"
    if a == h == "USAGE_DISTRIBUTED":
        return "DUAL_USAGE_DISTRIBUTED"
    if a and h:
        return "MIXED_USAGE_CONCENTRATION"
    return "LIMITED_SAMPLE"

def interaction_for(sport, away, home):
    if sport in {"NFL", "CFB"}:
        return football_interactions(away, home)
    if sport in {"NBA", "CBB"}:
        return basketball_interactions(away, home)
    if sport == "NHL":
        return nhl_interactions(away, home)
    if sport == "MLB":
        return mlb_interactions(away, home)
    return {}

STYLE_EXPORT_FIELDS = [
    "primary_style","tempo_signal","play_mix_signal","concentration_signal",
    "sample_stage","games","coach","pass_rate","rush_rate","plays_per_game",
    "offensive_epa_per_play","explosive_play_rate","top_target_share",
    "top3_target_share","top_carry_share","estimated_possessions_per_game",
    "three_point_attempt_rate","turnover_rate","shots_for_per_game",
    "shots_against_per_game","shot_environment_per_game","shooting_pct",
    "runs_per_game","home_runs_per_game","stolen_bases_per_game",
    "walks_per_game","strikeouts_per_game","ops","pitches_per_plate_appearance",
]
rows = []
coverage_rows = []

for game in schedule_games():
    sport = game["sport"]
    away_style = get_style(
        sport,
        game.get("away_team"),
        game.get("away_team_id"),
        game.get("away_team_name"),
    )
    home_style = get_style(
        sport,
        game.get("home_team"),
        game.get("home_team_id"),
        game.get("home_team_name"),
    )

    if away_style and home_style:
        coverage = "FULL_STYLE_COVERAGE"
    elif away_style:
        coverage = "HOME_STYLE_MISSING"
    elif home_style:
        coverage = "AWAY_STYLE_MISSING"
    else:
        coverage = "BOTH_STYLES_MISSING"

    metric_names = {
        "NFL": ("PLAYS_PER_GAME", "PLAYS_PER_GAME_GAP", "PASS_RATE_GAP"),
        "CFB": ("PLAYS_PER_GAME", "PLAYS_PER_GAME_GAP", "PASS_RATE_GAP"),
        "NBA": ("EST_POSSESSIONS_PER_GAME", "POSSESSIONS_PER_GAME_GAP", "THREE_POINT_ATTEMPT_RATE_GAP"),
        "CBB": ("EST_POSSESSIONS_PER_GAME", "POSSESSIONS_PER_GAME_GAP", "THREE_POINT_ATTEMPT_RATE_GAP"),
        "NHL": ("SHOT_OPPORTUNITY_PER_TEAM", "SHOT_EVENT_ENVIRONMENT_GAP", "SHOTS_FOR_PER_GAME_GAP"),
        "MLB": ("RUNS_PER_GAME_OFFENSIVE_BASELINE", "PITCHES_PER_PA_GAP", "HOME_RUNS_PER_GAME_GAP"),
    }.get(sport, ("UNKNOWN", "UNKNOWN", "UNKNOWN"))

    row = {
        **game,
        "coverage_status": coverage,
        "away_style_matched": bool(away_style),
        "home_style_matched": bool(home_style),
        "matchup_volume_metric_name": metric_names[0],
        "tempo_gap_metric_name": metric_names[1],
        "play_mix_gap_metric_name": metric_names[2],
        "away_style_key": clean(
            away_style.get("team") if away_style else ""
        ),
        "home_style_key": clean(
            home_style.get("team") if home_style else ""
        ),
    }

    for prefix, style_row_data in [
        ("away", away_style),
        ("home", home_style),
    ]:
        for field in STYLE_EXPORT_FIELDS:
            row[f"{prefix}_{field}"] = (
                style_row_data.get(field) if style_row_data else None
            )
    if away_style and home_style:
        row.update(interaction_for(sport, away_style, home_style))
        row["usage_interaction"] = usage_interaction(
            sport, away_style, home_style
        )
    else:
        row.update({
            "pace_interaction": "NOT_AVAILABLE",
            "play_mix_interaction": "NOT_AVAILABLE",
            "usage_interaction": "NOT_AVAILABLE",
            "matchup_volume_proxy": None,
            "tempo_gap": None,
            "play_mix_gap": None,
            "away_opportunity_proxy": None,
            "home_opportunity_proxy": None,
        })

    if sport == "NFL":
        away_key = normalize_team_key(sport, game.get("away_team"))
        home_key = normalize_team_key(sport, game.get("home_team"))
        away_coach = coach_lookup.get(("NFL", norm(away_key)), {})
        home_coach = coach_lookup.get(("NFL", norm(home_key)), {})
        row["away_coach_continuity_signal"] = clean(
            away_coach.get("coach_continuity_signal")
        ) or "COACH_UNKNOWN"
        row["home_coach_continuity_signal"] = clean(
            home_coach.get("coach_continuity_signal")
        ) or "COACH_UNKNOWN"
        row["coaching_regime_interaction"] = (
            "BOTH_NEW_REGIME"
            if row["away_coach_continuity_signal"] == "NEW_REGIME"
            and row["home_coach_continuity_signal"] == "NEW_REGIME"
            else "ONE_NEW_REGIME"
            if "NEW_REGIME" in {
                row["away_coach_continuity_signal"],
                row["home_coach_continuity_signal"],
            }
            else "COACH_CONTINUITY_PAIRING"
            if row["away_coach_continuity_signal"] == "COACH_CONTINUITY"
            and row["home_coach_continuity_signal"] == "COACH_CONTINUITY"
            else "COACH_CONTEXT_MIXED"
        )
    else:
        row["away_coach_continuity_signal"] = "NOT_MODELED"
        row["home_coach_continuity_signal"] = "NOT_MODELED"
        row["coaching_regime_interaction"] = "NOT_MODELED"

    row["generated_at"] = NOW.isoformat()
    row["automatic_model_adjustment"] = False
    row["score_is_probability"] = False
    rows.append(row)
matchups = pd.DataFrame(rows)

if not matchups.empty:
    matchups = matchups.drop_duplicates(
        ["sport", "event_id"], keep="last"
    ).reset_index(drop=True)

source_rows = []
for sport in ["NFL","CFB","NBA","NHL","MLB","CBB"]:
    frame = matchups[matchups["sport"] == sport] if not matchups.empty else pd.DataFrame()
    if frame.empty:
        source_rows.append({
            "sport": sport,
            "scheduled_games": 0,
            "full_style_coverage": 0,
            "partial_style_coverage": 0,
            "missing_style_coverage": 0,
            "coverage_rate": None,
            "status": "NO_UPCOMING_GAMES",
            "generated_at": NOW.isoformat(),
        })
        continue
    full = int((frame["coverage_status"] == "FULL_STYLE_COVERAGE").sum())
    partial = int(frame["coverage_status"].isin(
        ["HOME_STYLE_MISSING","AWAY_STYLE_MISSING"]
    ).sum())
    missing = int((frame["coverage_status"] == "BOTH_STYLES_MISSING").sum())
    source_rows.append({
        "sport": sport,
        "scheduled_games": len(frame),
        "full_style_coverage": full,
        "partial_style_coverage": partial,
        "missing_style_coverage": missing,
        "coverage_rate": round(full / len(frame), 4) if len(frame) else None,
        "status": "FULL_COVERAGE" if full == len(frame)
        else "PARTIAL_COVERAGE" if full or partial else "NO_STYLE_COVERAGE",
        "generated_at": NOW.isoformat(),
    })

sources = pd.DataFrame(source_rows)
features = pd.DataFrame([
    {
        "sport_scope": "NFL/CFB",
        "feature": "pace_interaction",
        "definition": "League-relative offensive volume pairing from team plays/game labels.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NFL/CFB",
        "feature": "play_mix_interaction",
        "definition": "Pass-heavy/run-heavy style pairing from observed team play mix.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NFL",
        "feature": "usage_interaction",
        "definition": "Target/carry concentration pairing from current team usage concentration.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NFL",
        "feature": "coaching_regime_interaction",
        "definition": "Current-vs-prior head-coach continuity pairing.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NBA/CBB",
        "feature": "pace_interaction",
        "definition": "Estimated possession pace pairing; NBA estimate is not official NBA Pace.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NBA/CBB",
        "feature": "play_mix_interaction",
        "definition": "League-relative three-point attempt profile pairing.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NHL",
        "feature": "pace_interaction",
        "definition": "Shot-event environment pairing from shots for+against profiles.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "NHL",
        "feature": "opportunity_proxy",
        "definition": "Mean of team shots-for and opponent shots-against baselines.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "MLB",
        "feature": "play_mix_interaction",
        "definition": "League-relative home-run power profile pairing.",
        "predictive_weight": False,
    },
    {
        "sport_scope": "MLB",
        "feature": "pace_interaction",
        "definition": "Plate-approach pairing from pitches per plate appearance.",
        "predictive_weight": False,
    },
])
features["score_is_probability"] = False
features["automatic_model_adjustment"] = False
matchups.to_csv(CURRENT_OUT, index=False)
sources.to_csv(SOURCE_OUT, index=False)
features.to_csv(FEATURE_OUT, index=False)

coverage_counts = (
    matchups["coverage_status"].value_counts().to_dict()
    if not matchups.empty else {}
)
pace_counts = (
    matchups.groupby(["sport","pace_interaction"]).size().to_dict()
    if not matchups.empty else {}
)
mix_counts = (
    matchups.groupby(["sport","play_mix_interaction"]).size().to_dict()
    if not matchups.empty else {}
)

receipt = {
    "generated_at": NOW.isoformat(),
    "matchup_rows": len(matchups),
    "rows_by_sport": (
        {str(k): int(v) for k, v in matchups["sport"].value_counts().to_dict().items()}
        if not matchups.empty else {}
    ),
    "coverage_counts": {str(k): int(v) for k, v in coverage_counts.items()},
    "pace_interaction_counts": {
        f"{sport}:{signal}": int(count)
        for (sport, signal), count in pace_counts.items()
    },
    "play_mix_interaction_counts": {
        f"{sport}:{signal}": int(count)
        for (sport, signal), count in mix_counts.items()
    },
    "source_status": {
        row["sport"]: row["status"] for row in source_rows
    },
    "explicit_gaps": [
        "CFB opponents outside the modeled FBS universe remain partial coverage.",
        "CBB non-Division-I or otherwise unmodeled opponents remain partial coverage.",
        "NFL pass/run interaction is descriptive raw observed mix, not situation-neutral play calling.",
        "NBA pace interaction uses a transparent estimated possession baseline, not official NBA Pace.",
        "NBA/NHL interactions use prior-season baselines until 2026-27 regular-season samples mature.",
        "NHL opportunity proxy is descriptive and does not include zone-entry/EDGE spatial context.",
        "MLB interaction currently compares team offensive identity; pitcher-style interaction is separate future work.",
        "No interaction label changes model weights automatically.",
    ],
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
}
RECEIPT_OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("MATCHUPS:", len(matchups))
print("BY SPORT:", receipt["rows_by_sport"])
print("COVERAGE:", receipt["coverage_counts"])
print("SOURCE STATUS:", receipt["source_status"])
print("RESULT: MATCHUP_STYLE_READY")
