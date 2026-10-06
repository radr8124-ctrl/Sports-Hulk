#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import re

import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "player_opportunity"
OUT.mkdir(parents=True, exist_ok=True)

ROLE_FILE = ROOT / "intelligence_warehouse" / "features" / "PLAYER_ROLE_SIGNALS_CURRENT.csv"
AVAIL_FILE = ROOT / "intelligence_warehouse" / "availability" / "AVAILABILITY_CURRENT.csv"
STARTER_FILE = ROOT / "intelligence_warehouse" / "starters" / "STARTER_STATUS_CURRENT.csv"
MATCHUP_FILE = ROOT / "intelligence_warehouse" / "matchup_style" / "MATCHUP_STYLE_CURRENT.csv"
MARKET_FILE = ROOT / "intelligence_warehouse" / "fantasy_market" / "FANTASY_MARKET_CONTEXT_CURRENT.csv"
NBA_ROSTER_FILE = ROOT / "nba_live" / "derived" / "NBA_CURRENT_ROSTERS.csv"
NHL_ROSTER_FILE = ROOT / "nhl_live" / "derived" / "NHL_CURRENT_ROSTERS.csv"

CURRENT_OUT = OUT / "PLAYER_OPPORTUNITY_CONTEXT_CURRENT.csv"
SOURCE_OUT = OUT / "PLAYER_OPPORTUNITY_SOURCE_CATALOG.csv"
FEATURE_OUT = OUT / "PLAYER_OPPORTUNITY_FEATURE_CATALOG.csv"
RECEIPT_OUT = OUT / "PLAYER_OPPORTUNITY_RECEIPT.json"

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
    return "" if text.lower() in {"nan","none","nat","<na>"} else text

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())

def num(value):
    try:
        return float(value)
    except Exception:
        return None

def event_key(value):
    text = clean(value)
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text

def provider_id(value):
    return event_key(value)

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if Path(path).exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def quartile_label(value, low, high, low_label, mid_label, high_label):
    value = num(value)
    if value is None:
        return "LIMITED_SAMPLE"
    if value <= low:
        return low_label
    if value >= high:
        return high_label
    return mid_label
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
NHL_ALIAS = {"LAK":"LA","NJD":"NJ","SJS":"SJ","TBL":"TB","UTA":"UTAH"}
NBA_ALIAS = {
    "NOP":"NO","WAS":"WSH","NYK":"NY","UTA":"UTAH","GSW":"GS","SAS":"SA",
}

def team_key(sport, value):
    text = clean(value)
    if sport == "NFL":
        return NFL_FULL_TO_ABBR.get(text, text)
    if sport == "NHL":
        return NHL_ALIAS.get(text, text)
    if sport == "NBA":
        return NBA_ALIAS.get(text, text)
    return text
roles = read_csv(ROLE_FILE)
availability = read_csv(AVAIL_FILE)
starters = read_csv(STARTER_FILE)
matchups = read_csv(MATCHUP_FILE)
market = read_csv(MARKET_FILE)
nba_rosters = read_csv(NBA_ROSTER_FILE)
nhl_rosters = read_csv(NHL_ROSTER_FILE)

if roles.empty or matchups.empty:
    raise SystemExit("required role or matchup context is missing")

current_team_lookup = {}
roster_player_key_lookup = {}
for sport, roster in [("NBA", nba_rosters), ("NHL", nhl_rosters)]:
    if roster.empty:
        continue
    for row in roster.to_dict("records"):
        pid = provider_id(row.get("player_id"))
        team = clean(row.get("team"))
        if pid and team:
            current_team_lookup[(sport, pid)] = team
        canonical_key = clean(row.get("player_key")) or norm(row.get("player"))
        if pid and canonical_key:
            roster_player_key_lookup[(sport, pid)] = canonical_key

matchups["start_dt"] = pd.to_datetime(
    matchups["start"], errors="coerce", utc=True, format="mixed"
)
now_ts = pd.Timestamp(NOW)
future = matchups[
    matchups["start_dt"].notna()
    & (matchups["start_dt"] >= now_ts - pd.Timedelta(hours=1))
].copy()
future = future.sort_values(["sport","start_dt","event_id"])

team_matchup = {}
for row in future.to_dict("records"):
    sport = clean(row.get("sport")).upper()
    for side, other in [("away","home"),("home","away")]:
        candidates = [
            team_key(sport, row.get(f"{side}_style_key")),
            team_key(sport, row.get(f"{side}_team")),
            clean(row.get(f"{side}_team_id")),
            clean(row.get(f"{side}_team_name")),
        ]
        record = dict(row)
        record["player_team_side"] = side.upper()
        record["opponent_team_side"] = other.upper()
        record["player_team_key"] = team_key(
            sport, row.get(f"{side}_style_key") or row.get(f"{side}_team")
        )
        record["opponent_team_key"] = team_key(
            sport, row.get(f"{other}_style_key") or row.get(f"{other}_team")
        )
        for candidate in candidates:
            key = norm(candidate)
            if key and (sport, key) not in team_matchup:
                team_matchup[(sport, key)] = record
thresholds = {}
for sport in ["NFL","NBA","NHL","MLB"]:
    x = future[
        (future["sport"] == sport)
        & (future["coverage_status"] == "FULL_STYLE_COVERAGE")
    ].copy()
    if sport == "NHL":
        vals = pd.concat([
            pd.to_numeric(x["away_opportunity_proxy"], errors="coerce"),
            pd.to_numeric(x["home_opportunity_proxy"], errors="coerce"),
        ]).dropna()
        metric = "SIDE_SHOT_OPPORTUNITY_PROXY"
    elif sport == "MLB":
        vals = pd.concat([
            pd.to_numeric(x["away_runs_per_game"], errors="coerce"),
            pd.to_numeric(x["home_runs_per_game"], errors="coerce"),
        ]).dropna()
        metric = "TEAM_RUNS_PER_GAME_BASELINE"
    else:
        vals = pd.to_numeric(x["matchup_volume_proxy"], errors="coerce").dropna()
        metric = clean(x["matchup_volume_metric_name"].iloc[0]) if len(x) else ""
    thresholds[sport] = {
        "metric": metric,
        "q25": float(vals.quantile(0.25)) if len(vals) else None,
        "q75": float(vals.quantile(0.75)) if len(vals) else None,
        "n": int(len(vals)),
    }

availability_lookup = {}
availability_lookup_id = {}
for row in availability.to_dict("records"):
    sport = clean(row.get("sport")).upper()
    key = (sport, norm(row.get("player_key")))
    if key[1]:
        availability_lookup[key] = row
    pid = provider_id(row.get("player_id"))
    if pid:
        availability_lookup_id[(sport, pid)] = row

starter_lookup = {}
if not starters.empty:
    player_starters = starters[
        (starters["entity_type"].astype(str) == "PLAYER")
        & (starters["observation_phase"].astype(str) == "PRE_GAME")
    ]
    for row in player_starters.to_dict("records"):
        key = (
            clean(row.get("sport")).upper(),
            event_key(row.get("event_id")),
            norm(row.get("player_key")),
        )
        starter_lookup[key] = row

market_lookup = {}
market_lookup_id = {}
for row in market.to_dict("records"):
    sport = clean(row.get("sport")).upper()
    key = (sport, norm(row.get("player_key")))
    if key[1]:
        market_lookup[key] = row
    pid = provider_id(row.get("espn_id"))
    if pid:
        market_lookup_id[(sport, pid)] = row
BLOCKED_AVAILABILITY = {"OUT","IR","PUP","INACTIVE","DOUBTFUL","SUSPENDED"}
RISK_AVAILABILITY = {"QUESTIONABLE","DAY_TO_DAY"}

def availability_context(sport, player_key, current_team):
    row = None
    if sport in {"NBA","NHL"}:
        row = availability_lookup_id.get((sport, provider_id(player_key)))
    if row is None:
        row = availability_lookup.get((sport, norm(player_key)))
    if not row:
        return "NO_AVAILABILITY_FLAG", "", "", False, "NO_MATCH"
    row_team = team_key(sport, row.get("team"))
    current_team_key = team_key(sport, current_team)
    if row_team and current_team_key and norm(row_team) != norm(current_team_key):
        return "NO_AVAILABILITY_FLAG", "", "", False, "TEAM_MISMATCH"
    join_method = "PLAYER_ID" if sport in {"NBA","NHL"} else "PLAYER_KEY"
    status = clean(row.get("status_normalized")).upper()
    if status in BLOCKED_AVAILABILITY:
        signal = "AVAILABILITY_LIMITED"
    elif status in RISK_AVAILABILITY:
        signal = "AVAILABILITY_RISK"
    elif status == "AVAILABLE":
        signal = "AVAILABLE"
    else:
        signal = "AVAILABILITY_UNCERTAIN"
    return (
        signal,
        status,
        clean(row.get("return_date")),
        bool(row.get("source_disagreement")),
        join_method,
    )

def role_trend(signal):
    signal = clean(signal).upper()
    if signal == "ROLE_UP":
        return "ROLE_EXPANDING"
    if signal == "ROLE_DOWN":
        return "ROLE_CONTRACTING"
    if signal == "STEADY":
        return "ROLE_STEADY"
    return "ROLE_SAMPLE_LIMITED"
def team_side_value(matchup, side, field):
    return matchup.get(f"{side.lower()}_{field}")

def opportunity_environment(sport, position, matchup):
    side = clean(matchup.get("player_team_side")).lower()
    other = clean(matchup.get("opponent_team_side")).lower()
    t = thresholds.get(sport, {})
    q25, q75 = t.get("q25"), t.get("q75")
    pos = clean(position).upper()

    if sport == "NFL":
        volume = num(matchup.get("matchup_volume_proxy"))
        env = quartile_label(
            volume, q25, q75,
            "LOW_PLAY_VOLUME_ENVIRONMENT",
            "MID_PLAY_VOLUME_ENVIRONMENT",
            "HIGH_PLAY_VOLUME_ENVIRONMENT",
        ) if q25 is not None and q75 is not None else "LIMITED_SAMPLE"
        own_mix = clean(team_side_value(matchup, side, "play_mix_signal"))
        opp_tempo = clean(team_side_value(matchup, other, "tempo_signal"))
        if pos in {"QB","WR","TE"}:
            style = (
                "POSITION_STYLE_SUPPORT" if own_mix == "PASS_HEAVY"
                else "POSITION_STYLE_CONSTRAINT" if own_mix == "RUN_HEAVY"
                else "POSITION_STYLE_NEUTRAL"
            )
        elif pos in {"RB","FB"}:
            style = (
                "POSITION_STYLE_SUPPORT" if own_mix == "RUN_HEAVY"
                else "POSITION_STYLE_CONSTRAINT" if own_mix == "PASS_HEAVY"
                else "POSITION_STYLE_NEUTRAL"
            )
        else:
            style = (
                "IDP_VOLUME_SUPPORT" if opp_tempo == "HIGH_VOLUME"
                else "IDP_VOLUME_CONSTRAINT" if opp_tempo == "LOW_VOLUME"
                else "IDP_VOLUME_NEUTRAL"
            )
        return env, style, volume, t.get("metric")

    if sport == "NBA":
        volume = num(matchup.get("matchup_volume_proxy"))
        env = quartile_label(
            volume, q25, q75,
            "LOW_POSSESSION_ENVIRONMENT",
            "MID_POSSESSION_ENVIRONMENT",
            "HIGH_POSSESSION_ENVIRONMENT",
        ) if q25 is not None and q75 is not None else "LIMITED_SAMPLE"
        return env, "TEMPO_CONTEXT_ONLY", volume, t.get("metric")
    if sport == "NHL":
        volume = num(matchup.get(f"{side}_opportunity_proxy"))
        env = quartile_label(
            volume, q25, q75,
            "LOW_SHOT_OPPORTUNITY_ENVIRONMENT",
            "MID_SHOT_OPPORTUNITY_ENVIRONMENT",
            "HIGH_SHOT_OPPORTUNITY_ENVIRONMENT",
        ) if q25 is not None and q75 is not None else "LIMITED_SAMPLE"
        event = clean(matchup.get("pace_interaction"))
        style = (
            "EVENT_VOLUME_SUPPORT" if event == "DUAL_HIGH_EVENT"
            else "EVENT_VOLUME_CONSTRAINT" if event == "DUAL_LOW_EVENT"
            else "EVENT_VOLUME_MIXED"
        )
        return env, style, volume, t.get("metric")

    if sport == "MLB":
        own_runs = num(team_side_value(matchup, side, "runs_per_game"))
        opp_power = clean(team_side_value(matchup, other, "play_mix_signal"))
        opp_approach = clean(team_side_value(matchup, other, "tempo_signal"))
        env = quartile_label(
            own_runs, q25, q75,
            "LOW_OFFENSIVE_BASELINE",
            "MID_OFFENSIVE_BASELINE",
            "HIGH_OFFENSIVE_BASELINE",
        ) if q25 is not None and q75 is not None else "LIMITED_SAMPLE"
        if pos == "P":
            pressure = []
            if opp_power == "POWER_HEAVY":
                pressure.append("POWER_PRESSURE")
            elif opp_power == "LOW_POWER":
                pressure.append("LOW_POWER_OPPONENT")
            if opp_approach == "PATIENT_AT_BATS":
                pressure.append("PITCH_COUNT_PRESSURE")
            elif opp_approach == "EARLY_COUNT_CONTACT":
                pressure.append("EARLY_COUNT_CONTACT_OPPONENT")
            style = "|".join(pressure) if pressure else "MID_OFFENSE_PRESSURE"
        else:
            style = "OFFENSIVE_BASELINE_ONLY"
        return env, style, own_runs, t.get("metric")

    return "NOT_MODELED", "NOT_MODELED", None, ""
SUPPORT_ENVS = {
    "HIGH_PLAY_VOLUME_ENVIRONMENT",
    "HIGH_POSSESSION_ENVIRONMENT",
    "HIGH_SHOT_OPPORTUNITY_ENVIRONMENT",
    "HIGH_OFFENSIVE_BASELINE",
}
CONSTRAINT_ENVS = {
    "LOW_PLAY_VOLUME_ENVIRONMENT",
    "LOW_POSSESSION_ENVIRONMENT",
    "LOW_SHOT_OPPORTUNITY_ENVIRONMENT",
    "LOW_OFFENSIVE_BASELINE",
}
SUPPORT_STYLES = {"POSITION_STYLE_SUPPORT","IDP_VOLUME_SUPPORT","EVENT_VOLUME_SUPPORT"}
CONSTRAINT_STYLES = {"POSITION_STYLE_CONSTRAINT","IDP_VOLUME_CONSTRAINT","EVENT_VOLUME_CONSTRAINT"}

def composite_context(role_signal, env_signal, style_signal, avail_signal):
    trend = role_trend(role_signal)
    if avail_signal == "AVAILABILITY_LIMITED":
        return "AVAILABILITY_LIMITED_CONTEXT"
    support = env_signal in SUPPORT_ENVS or style_signal in SUPPORT_STYLES
    constraint = env_signal in CONSTRAINT_ENVS or style_signal in CONSTRAINT_STYLES
    if trend == "ROLE_EXPANDING":
        base = "EXPANDING_ROLE_WITH_ENVIRONMENT_SUPPORT" if support else "EXPANDING_ROLE"
    elif trend == "ROLE_CONTRACTING":
        base = "CONTRACTING_ROLE_WITH_ENVIRONMENT_CONSTRAINT" if constraint else "CONTRACTING_ROLE"
    elif trend == "ROLE_SAMPLE_LIMITED":
        base = "LIMITED_ROLE_SAMPLE"
    elif support:
        base = "STEADY_ROLE_ENVIRONMENT_SUPPORT"
    elif constraint:
        base = "STEADY_ROLE_ENVIRONMENT_CONSTRAINT"
    else:
        base = "STEADY_ROLE_NEUTRAL"
    if avail_signal == "AVAILABILITY_RISK":
        base += "|AVAILABILITY_RISK"
    elif avail_signal == "AVAILABILITY_UNCERTAIN":
        base += "|AVAILABILITY_UNCERTAIN"
    return base
collision_counts = (
    roles.groupby(["sport","player_key"], dropna=False).size()
    .reset_index(name="rows")
)
collision_keys = {
    (clean(r.sport).upper(), clean(r.player_key))
    for r in collision_counts.itertuples()
    if int(r.rows) > 1
}

rows = []

for role in roles.to_dict("records"):
    sport = clean(role.get("sport")).upper()
    player_key = clean(role.get("player_key"))
    role_team = clean(role.get("team"))
    position = clean(role.get("position"))
    pid = provider_id(player_key)
    current_team = current_team_lookup.get((sport, pid), role_team)
    team_assignment_source = (
        "CURRENT_ROSTER_PLAYER_ID"
        if current_team_lookup.get((sport, pid))
        else "ROLE_STORE_TEAM"
    )
    lookup_team = team_key(sport, current_team)
    matchup = team_matchup.get((sport, norm(lookup_team)))

    (
        avail_signal,
        avail_status,
        return_date,
        source_disagreement,
        availability_join_method,
    ) = availability_context(sport, player_key, current_team)

    market_join_method = "NO_MATCH"
    market_row = {}
    if sport in {"NBA","NHL"} and pid:
        market_row = market_lookup_id.get((sport, pid), {})
        if market_row:
            market_join_method = "PLAYER_ID"
        else:
            roster_key = roster_player_key_lookup.get((sport, pid), "")
            if roster_key:
                market_row = market_lookup.get((sport, norm(roster_key)), {})
                if market_row:
                    market_join_method = "CURRENT_ROSTER_PLAYER_KEY"
    else:
        market_row = market_lookup.get((sport, norm(player_key)), {})
        if market_row:
            market_join_method = "PLAYER_KEY"

    identity_key = player_key
    if (sport, player_key) in collision_keys:
        identity_key = "|".join([
            player_key,
            norm(role_team),
            clean(position).upper(),
            norm(role.get("role_metric")),
        ])

    base = {
        "sport": sport,
        "player_key": player_key,
        "opportunity_identity_key": identity_key,
        "player": clean(role.get("player")),
        "role_store_team": role_team,
        "team": current_team,
        "team_assignment_source": team_assignment_source,
        "position": position,
        "role_metric": clean(role.get("role_metric")),
        "recent_role_value": num(role.get("recent_value")),
        "season_role_value": num(role.get("season_value")),
        "role_delta": num(role.get("role_delta")),
        "role_signal": clean(role.get("signal")),
        "role_trend_context": role_trend(role.get("signal")),
        "role_sample_marker": num(role.get("sample_marker")),
        "availability_context": avail_signal,
        "availability_status": avail_status,
        "availability_return_date": return_date,
        "availability_source_disagreement": source_disagreement,
        "availability_join_method": availability_join_method,
        "market_join_method": market_join_method,
        "market_activity_signal": clean(market_row.get("market_activity_signal")) or "NO_MARKET_ACTIVITY_CONTEXT",
        "market_net_adds_24h": num(market_row.get("net_adds_24h")),
        "market_net_adds_168h": num(market_row.get("net_adds_168h")),
    }
    if not matchup:
        base.update({
            "event_id": "",
            "start": "",
            "opponent": "",
            "matchup_coverage_status": "NO_UPCOMING_MODELED_GAME",
            "pace_interaction": "NOT_AVAILABLE",
            "play_mix_interaction": "NOT_AVAILABLE",
            "usage_interaction": "NOT_AVAILABLE",
            "coaching_regime_interaction": "NOT_AVAILABLE",
            "environment_signal": "NO_UPCOMING_MODELED_GAME",
            "position_style_context": "NO_UPCOMING_MODELED_GAME",
            "environment_metric_value": None,
            "environment_metric_name": "",
            "starter_state": "NO_STARTER_CONTEXT",
            "starter_role": "",
            "opportunity_context": "NO_UPCOMING_MODELED_GAME",
        })
        base["generated_at"] = NOW.isoformat()
        base["automatic_model_adjustment"] = False
        base["score_is_probability"] = False
        rows.append(base)
        continue

    side = clean(matchup.get("player_team_side")).lower()
    other = clean(matchup.get("opponent_team_side")).lower()
    event_id = event_key(matchup.get("event_id"))
    env_signal, style_signal, env_value, env_name = opportunity_environment(
        sport, position, matchup
    )
    starter = starter_lookup.get((sport, event_id, norm(player_key)), {})

    base.update({
        "event_id": event_id,
        "start": clean(matchup.get("start")),
        "opponent": clean(matchup.get(f"{other}_team")),
        "matchup_coverage_status": clean(matchup.get("coverage_status")),
        "pace_interaction": clean(matchup.get("pace_interaction")),
        "play_mix_interaction": clean(matchup.get("play_mix_interaction")),
        "usage_interaction": clean(matchup.get("usage_interaction")),
        "coaching_regime_interaction": clean(matchup.get("coaching_regime_interaction")),
        "environment_signal": env_signal,
        "position_style_context": style_signal,
        "environment_metric_value": env_value,
        "environment_metric_name": env_name,
        "starter_state": clean(starter.get("state")) or "NO_STARTER_CONTEXT",
        "starter_role": clean(starter.get("role")),
        "opportunity_context": composite_context(
            role.get("signal"), env_signal, style_signal, avail_signal
        ),
    })
    base["generated_at"] = NOW.isoformat()
    base["automatic_model_adjustment"] = False
    base["score_is_probability"] = False
    rows.append(base)
current = pd.DataFrame(rows)

features = pd.DataFrame([
    {
        "sport_scope":"NFL",
        "feature":"position_style_context",
        "definition":"QB/WR/TE use own-team pass tendency; RB/FB use own-team rush tendency; IDP uses opponent play-volume tendency.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"NFL",
        "feature":"environment_signal",
        "definition":"Upcoming matchup play-volume quartile from matchup-style context.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"NBA",
        "feature":"environment_signal",
        "definition":"Upcoming estimated-possession environment quartile; based on transparent possession estimate, not official NBA Pace.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"NHL",
        "feature":"environment_signal",
        "definition":"Team-side shot-opportunity proxy quartile using team shots-for and opponent shots-against baselines.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"MLB_PITCHER",
        "feature":"position_style_context",
        "definition":"Opponent offensive power and plate-approach pressure context for pitchers.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"MLB_HITTER",
        "feature":"position_style_context",
        "definition":"Team offensive baseline only; opposing pitcher quality is not inferred.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"ALL",
        "feature":"opportunity_context",
        "definition":"Conservative composition of role trend, matchup environment, position style, and availability gate.",
        "predictive_weight":False,
    },
    {
        "sport_scope":"ALL",
        "feature":"availability_context",
        "definition":"Governed availability lifecycle overlay; blocked states prevent favorable opportunity labels from overriding availability.",
        "predictive_weight":False,
    },
])
features["score_is_probability"] = False
features["automatic_model_adjustment"] = False
source_rows = []
for sport in ["NFL","NBA","NHL","MLB","CFB","CBB"]:
    frame = current[current["sport"] == sport] if not current.empty else pd.DataFrame()
    if frame.empty:
        source_rows.append({
            "sport": sport,
            "player_rows": 0,
            "upcoming_matchup_rows": 0,
            "no_upcoming_game_rows": 0,
            "availability_context_rows": 0,
            "starter_context_rows": 0,
            "market_context_rows": 0,
            "current_roster_remap_rows": 0,
            "identity_collision_rows": 0,
            "status": "PLAYER_ROLE_STORE_NOT_MODELED" if sport in {"CFB","CBB"} else "NO_ROWS",
            "generated_at": NOW.isoformat(),
        })
        continue
    source_rows.append({
        "sport": sport,
        "player_rows": len(frame),
        "upcoming_matchup_rows": int((frame["matchup_coverage_status"] != "NO_UPCOMING_MODELED_GAME").sum()),
        "no_upcoming_game_rows": int((frame["matchup_coverage_status"] == "NO_UPCOMING_MODELED_GAME").sum()),
        "availability_context_rows": int((frame["availability_context"] != "NO_AVAILABILITY_FLAG").sum()),
        "starter_context_rows": int((frame["starter_state"] != "NO_STARTER_CONTEXT").sum()),
        "market_context_rows": int((frame["market_activity_signal"] != "NO_MARKET_ACTIVITY_CONTEXT").sum()),
        "current_roster_remap_rows": int((frame["team_assignment_source"] == "CURRENT_ROSTER_PLAYER_ID").sum()),
        "identity_collision_rows": int(frame["opportunity_identity_key"].astype(str).str.contains("\\|", regex=True).sum()),
        "status": "ACTIVE_PLAYER_OPPORTUNITY_CONTEXT",
        "generated_at": NOW.isoformat(),
    })
sources = pd.DataFrame(source_rows)

current.to_csv(CURRENT_OUT, index=False)
sources.to_csv(SOURCE_OUT, index=False)
features.to_csv(FEATURE_OUT, index=False)
sport_counts = current["sport"].value_counts().to_dict() if not current.empty else {}
context_counts = current["opportunity_context"].value_counts().to_dict() if not current.empty else {}
env_counts = current.groupby(["sport","environment_signal"]).size().to_dict() if not current.empty else {}
starter_counts = current["starter_state"].value_counts().to_dict() if not current.empty else {}

receipt = {
    "generated_at": NOW.isoformat(),
    "player_rows": len(current),
    "rows_by_sport": {str(k): int(v) for k,v in sport_counts.items()},
    "opportunity_context_counts": {str(k): int(v) for k,v in context_counts.items()},
    "environment_signal_counts": {
        f"{sport}:{signal}": int(count)
        for (sport, signal), count in env_counts.items()
    },
    "starter_state_counts": {str(k): int(v) for k,v in starter_counts.items()},
    "player_key_collision_groups": len(collision_keys),
    "identity_duplicates": int(current.duplicated(["sport","opportunity_identity_key"]).sum()),
    "current_roster_remap_rows": int((current["team_assignment_source"] == "CURRENT_ROSTER_PLAYER_ID").sum()),
    "thresholds": thresholds,
    "source_status": {row["sport"]: row["status"] for row in source_rows},
    "explicit_gaps": [
        "CFB player-level opportunity is not modeled because there is no governed CFB player-role store yet.",
        "CBB player-level opportunity is not modeled because there is no governed CBB player-role store yet.",
        "NFL matchup context uses team offensive style and volume, not opponent defensive matchup quality or situation-neutral play calling.",
        "NBA context uses prior-season player roles and estimated-possession team baselines during preseason.",
        "NHL skater context does not include goalies or EDGE spatial tracking.",
        "MLB hitter context does not infer opposing pitcher quality; pitcher context only describes opposing offense style and official starter status when available.",
        "NBA/NHL role trends can originate on a prior team after transactions; current roster team is remapped by exact player ID and the original role-store team is preserved.",
        "Normalized player-key collisions are preserved with a collision-safe opportunity identity instead of dropping records.",
        "Opportunity labels are descriptive research context, not projections, probabilities, prop recommendations, or automatic model weights.",
    ],
    "score_is_probability": False,
    "automatic_model_adjustment": False,
    "paid_provider_required": False,
}
RECEIPT_OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True))

print("PLAYER ROWS:", len(current))
print("BY SPORT:", receipt["rows_by_sport"])
print("UPCOMING:", int((current["matchup_coverage_status"] != "NO_UPCOMING_MODELED_GAME").sum()))
print("NO UPCOMING:", int((current["matchup_coverage_status"] == "NO_UPCOMING_MODELED_GAME").sum()))
print("STARTER CONTEXT:", int((current["starter_state"] != "NO_STARTER_CONTEXT").sum()))
print("RESULT: PLAYER_OPPORTUNITY_READY")
