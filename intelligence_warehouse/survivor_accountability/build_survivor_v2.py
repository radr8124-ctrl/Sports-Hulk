#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "intelligence_warehouse" / "survivor_accountability"
OUTDIR.mkdir(parents=True, exist_ok=True)

ENTRIES = ROOT / "nfl_live" / "derived" / "SURVIVOR_ENTRIES.json"
STRATEGY = ROOT / "nfl_live" / "derived" / "NFL_SURVIVOR_HULK_STRATEGY.csv"
SCHEDULE = ROOT / "nfl_live" / "derived" / "NFLVERSE_2026_SCHEDULE.csv"
OFFICIAL = ROOT / "nfl_live" / "survivor_pool" / "derived" / "LATEST_OFFICIAL_POOL.json"
OWNERSHIP = ROOT / "nfl_live" / "survivor_pool" / "derived" / "SURVIVOR_POOL_OWNERSHIP.csv"

CURRENT = OUTDIR / "SURVIVOR_V2_CURRENT.json"
LEDGER = OUTDIR / "SURVIVOR_V2_FORWARD_LEDGER.jsonl"
SUMMARY = OUTDIR / "SURVIVOR_V2_FORWARD_SUMMARY.json"
PUBLIC_CURRENT = ROOT / "commercial_web" / "public" / "survivor_v2_current.json"
PUBLIC_FORWARD = ROOT / "commercial_web" / "public" / "survivor_v2_forward.json"
DIST = ROOT / "commercial_web" / "dist"
DIST_CURRENT = DIST / "survivor_v2_current.json"
DIST_FORWARD = DIST / "survivor_v2_forward.json"

MODEL_VERSION = "SURVIVOR_V2_FORWARD_2026_10_05"

TEAM_TO_ABBR = {
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

def now():
    return datetime.now(timezone.utc)

def now_iso():
    return now().isoformat()

def clean(v):
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except Exception:
        pass
    return str(v).strip()

def num(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def load_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback

def load_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def read_jsonl(path):
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")

def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)

def canonical():
    latest = {}
    for event in read_jsonl(LEDGER):
        key = event.get("forward_key")
        if key:
            latest[key] = {**latest.get(key, {}), **event}
    return latest

def ownership_context(current_week, official, ownership):
    official_week = int(num(official.get("pool_week")) or 0)
    if official_week != current_week:
        return {
            "status": "WAITING_CURRENT_WEEK_OFFICIAL_SHEET",
            "official_pool_week": official_week or None,
            "current_week": current_week,
            "by_team": {},
        }
    if ownership.empty:
        return {
            "status": "CURRENT_WEEK_SHEET_NO_OWNERSHIP_ROWS",
            "official_pool_week": official_week,
            "current_week": current_week,
            "by_team": {},
        }

    x = ownership[
        pd.to_numeric(ownership.get("week_position"), errors="coerce").eq(current_week)
    ].copy()
    by_team = {}
    for team, group in x.groupby("team"):
        slots = {}
        for _, row in group.iterrows():
            slot = int(num(row.get("week_pick_number")) or 0)
            if slot:
                slots[str(slot)] = num(row.get("pick_share_pct"))
        by_team[clean(team)] = slots
    return {
        "status": "CURRENT_WEEK_OWNERSHIP_AVAILABLE",
        "official_pool_week": official_week,
        "current_week": current_week,
        "by_team": by_team,
    }

def rule_state(entry, week):
    state = entry.get(f"week_{week}") if isinstance(entry, dict) else {}
    state = state if isinstance(state, dict) else {}
    required = None
    try:
        raw = state.get("required_picks")
        required = int(raw) if raw is not None else None
    except Exception:
        required = None
    if required is not None and required <= 0:
        required = None

    status = clean(state.get("rule_status"))
    confirmed = bool(
        required
        and (
            "CONFIRMED" in status.upper()
            or state.get("official_pool_sheet_confirmed") is True
        )
    )
    return state, required, status, confirmed

def unique_game_picks(rows, required):
    required = int(required or 0)
    if required <= 0:
        return []
    chosen = []
    games = set()
    for row in rows:
        team = clean(row.get("team"))
        opponent = clean(row.get("opponent"))
        game = tuple(sorted([team, opponent]))
        if not team or not opponent or game in games:
            continue
        chosen.append(row)
        games.add(game)
        if len(chosen) >= required:
            break
    return chosen

def current_payload():
    entries = load_json(ENTRIES, {})
    strategy = load_csv(STRATEGY)
    official = load_json(OFFICIAL, {})
    ownership = load_csv(OWNERSHIP)

    pool_week = int(num(entries.get("pool_current_week")) or 0)
    if not pool_week and not strategy.empty and "current_week" in strategy.columns:
        vals = pd.to_numeric(strategy["current_week"], errors="coerce").dropna()
        if not vals.empty:
            pool_week = int(vals.mode().iloc[0])

    active_name = clean(entries.get("active"))
    active_entry = (entries.get("entries") or {}).get(active_name, {}) if active_name else {}
    entry_status = clean(active_entry.get("status")).upper()
    entry_week = int(num(active_entry.get("current_week")) or 0) if active_entry else 0
    week_state, required, rule_status, rule_confirmed = rule_state(active_entry, pool_week)
    used = list(dict.fromkeys(active_entry.get("used_teams") or [])) if active_entry else []
    current_picks = list(dict.fromkeys(active_entry.get("current_picks") or [])) if active_entry else []

    own = ownership_context(pool_week, official, ownership)

    rows = []
    if not strategy.empty:
        if "current_week" in strategy.columns:
            strategy = strategy[
                pd.to_numeric(strategy["current_week"], errors="coerce").eq(pool_week)
            ].copy()
        strategy["_start"] = pd.to_datetime(strategy.get("start"), errors="coerce", utc=True)
        strategy = strategy[strategy["_start"].notna()].copy()
        strategy = strategy[strategy["_start"].map(lambda x: x.to_pydatetime() > now())].copy()

        for _, row in strategy.iterrows():
            team = clean(row.get("survivor_team"))
            if not team or team in used:
                continue
            action = clean(row.get("strategy_action")).upper()
            tier = clean(row.get("hulk_decision_tier")).upper()
            safe_for_shadow = action not in {"AVOID"} and tier not in {"CAUTION"}
            slot_shares = own["by_team"].get(team, {})
            rows.append({
                "team": team,
                "opponent": clean(row.get("opponent")),
                "start": clean(row.get("start")),
                "market_prob_pct": num(row.get("market_prob_pct")),
                "spread": num(row.get("survivor_spread")),
                "hulk_context_score": num(row.get("hulk_context_score")),
                "future_value_index": num(row.get("future_value_index")),
                "future_value_label": clean(row.get("future_value_label")),
                "strategy_index": num(row.get("strategy_index")),
                "strategy_action": action,
                "decision_tier": tier,
                "risk_signals": clean(row.get("risk_signals")),
                "positive_signals": clean(row.get("positive_signals")),
                "pool_pick_share_pct_by_slot": slot_shares,
                "ownership_used_for_ranking": False,
                "eligible_for_shadow": safe_for_shadow,
            })

    rows.sort(
        key=lambda r: (
            -(r.get("strategy_index") if r.get("strategy_index") is not None else -999),
            -(r.get("market_prob_pct") if r.get("market_prob_pct") is not None else -999),
        )
    )

    safe_rows = [r for r in rows if r["eligible_for_shadow"]]
    baseline_rows = sorted(
        rows,
        key=lambda r: -(r.get("market_prob_pct") if r.get("market_prob_pct") is not None else -999),
    )

    safe_combo = unique_game_picks(safe_rows, required)
    baseline_combo = unique_game_picks(baseline_rows, required)

    if not active_entry:
        recommendation_status = "WAITING_ACTIVE_ENTRY"
    elif entry_status == "ELIMINATED" and clean(active_entry.get("reentry_status")).upper() != "ACTIVE_REENTRY":
        recommendation_status = "BUYBACK_RULE_NOT_CONFIGURED"
    elif entry_week != pool_week:
        recommendation_status = "STATE_WEEK_MISMATCH"
    elif not rule_confirmed:
        recommendation_status = "WAITING_OFFICIAL_RULE_CONFIRMATION"
    elif not required:
        recommendation_status = "WAITING_REQUIRED_PICK_COUNT"
    elif len(safe_combo) < required:
        recommendation_status = "INSUFFICIENT_UNIQUE_GAME_TEAMS"
    elif len(baseline_combo) < required:
        recommendation_status = "INSUFFICIENT_MARKET_BASELINE_GAMES"
    else:
        recommendation_status = "SHADOW_RECOMMENDATION_READY"

    shadow_picks = safe_combo if recommendation_status == "SHADOW_RECOMMENDATION_READY" else []
    baseline_picks = baseline_combo if recommendation_status == "SHADOW_RECOMMENDATION_READY" else []

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "pool_current_week": pool_week,
        "active_entry": active_name or None,
        "active_entry_status": entry_status or None,
        "active_entry_week": entry_week or None,
        "state_week_matches_pool": bool(entry_week == pool_week) if active_entry else None,
        "used_teams": used,
        "current_saved_picks": current_picks,
        "required_picks": required,
        "rule_status": rule_status or None,
        "rule_confirmed": rule_confirmed,
        "ownership": {
            "status": own["status"],
            "official_pool_week": own["official_pool_week"],
            "current_week": own["current_week"],
        },
        "candidate_count": len(rows),
        "candidates": rows,
        "recommendation_status": recommendation_status,
        "shadow_recommendation": shadow_picks,
        "safest_market_baseline": baseline_picks,
        "rules": [
            "No Survivor recommendation is frozen until the official current-week pick count is confirmed.",
            "Used teams are removed before ranking.",
            "Already-started games are removed before ranking.",
            "CAUTION and AVOID candidates cannot become a shadow recommendation.",
            "When multiple picks are required, every frozen pick must come from a different game.",
            "Current pool ownership is diagnostic only and is never borrowed from a prior week's sheet.",
            "The safest eligible market favorite is frozen as the comparison baseline.",
            "An eliminated entry cannot be silently reactivated; buyback/re-entry must be explicitly recorded.",
            "No pick is submitted to the external pool automatically.",
        ],
    }

def forward_key(current):
    return "|".join([
        MODEL_VERSION,
        clean(current.get("active_entry")),
        str(current.get("pool_current_week") or ""),
    ])

def capture(current):
    if current.get("recommendation_status") != "SHADOW_RECOMMENDATION_READY":
        return {
            "status": current.get("recommendation_status"),
            "entries_added": 0,
        }

    key = forward_key(current)
    existing = canonical()
    if key in existing:
        return {"status": "ALREADY_FROZEN", "entries_added": 0}

    event = {
        "event_type": "ENTRY",
        "forward_key": key,
        "model_version": MODEL_VERSION,
        "captured_at": now_iso(),
        "entry_name": current.get("active_entry"),
        "week": current.get("pool_current_week"),
        "required_picks": current.get("required_picks"),
        "used_teams_at_freeze": current.get("used_teams") or [],
        "rule_status_at_freeze": current.get("rule_status"),
        "ownership_status_at_freeze": current.get("ownership", {}).get("status"),
        "hulk_picks": current.get("shadow_recommendation") or [],
        "market_baseline_picks": current.get("safest_market_baseline") or [],
        "status": "PENDING",
        "hulk_result": "PENDING",
        "baseline_result": "PENDING",
        "live_rule_changed": False,
    }
    append_jsonl(LEDGER, event)
    return {"status": "FROZEN", "entries_added": 1}

def team_result(schedule, week, team_name):
    abbr = TEAM_TO_ABBR.get(clean(team_name))
    if not abbr:
        return None
    hit = schedule[
        (schedule["season"] == 2026)
        & (schedule["week"] == week)
        & (schedule["game_type"] == "REG")
        & (
            schedule["home_team"].astype(str).eq(abbr)
            | schedule["away_team"].astype(str).eq(abbr)
        )
    ]
    if hit.empty:
        return None
    row = hit.iloc[-1]
    hs = num(row.get("home_score"))
    aws = num(row.get("away_score"))
    if hs is None or aws is None:
        return None
    if hs == aws:
        return "LOSS"
    if clean(row.get("home_team")) == abbr:
        return "WIN" if hs > aws else "LOSS"
    return "WIN" if aws > hs else "LOSS"

def combo_result(schedule, week, picks, required):
    if not picks or len(picks) < int(required or 1):
        return None, []
    results = []
    for pick in picks[: int(required or 1)]:
        result = team_result(schedule, week, pick.get("team"))
        if result is None:
            return None, results
        results.append(result)
    return ("LOSS" if "LOSS" in results else "WIN"), results

def settle():
    schedule = load_csv(SCHEDULE)
    if schedule.empty:
        return 0
    entries = canonical()
    settled_now = 0
    for key, row in entries.items():
        if clean(row.get("status")).upper() == "SETTLED":
            continue
        week = int(num(row.get("week")) or 0)
        required = int(num(row.get("required_picks")) or 1)
        if not week:
            continue
        hulk_result, hulk_legs = combo_result(schedule, week, row.get("hulk_picks") or [], required)
        base_result, base_legs = combo_result(schedule, week, row.get("market_baseline_picks") or [], required)
        if hulk_result is None or base_result is None:
            continue
        event = {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "settled_at": now_iso(),
            "hulk_result": hulk_result,
            "hulk_leg_results": hulk_legs,
            "baseline_result": base_result,
            "baseline_leg_results": base_legs,
        }
        append_jsonl(LEDGER, event)
        settled_now += 1
    return settled_now

def build_summary(current, capture_result, settled_now):
    rows = [
        row for row in canonical().values()
        if clean(row.get("model_version")) == MODEL_VERSION
    ]
    settled = [r for r in rows if clean(r.get("status")).upper() == "SETTLED"]
    hulk_wins = sum(clean(r.get("hulk_result")).upper() == "WIN" for r in settled)
    base_wins = sum(clean(r.get("baseline_result")).upper() == "WIN" for r in settled)
    distinct = 0
    for row in settled:
        hp = tuple(clean(x.get("team")) for x in row.get("hulk_picks") or [])
        bp = tuple(clean(x.get("team")) for x in row.get("market_baseline_picks") or [])
        if hp != bp:
            distinct += 1

    weeks = len({int(r.get("week") or 0) for r in settled if int(r.get("week") or 0)})
    if weeks < 10:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif distinct < 3:
        proof = "INSUFFICIENT_STRATEGY_SEPARATION"
    elif hulk_wins > base_wins:
        proof = "PROMISING_REVIEW_CANDIDATE"
    elif hulk_wins == base_wins:
        proof = "NO_PROVEN_ADVANTAGE_VS_MARKET_BASELINE"
    else:
        proof = "UNDERPERFORMING_MARKET_BASELINE"

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "current": current,
        "capture": capture_result,
        "settled_now": settled_now,
        "forward": {
            "tracked_entry_weeks": len(rows),
            "settled_entry_weeks": len(settled),
            "independent_weeks": weeks,
            "hulk_survived": hulk_wins,
            "hulk_lost": len(settled) - hulk_wins,
            "hulk_survival_rate_pct": None if not settled else round(100 * hulk_wins / len(settled), 1),
            "market_baseline_survived": base_wins,
            "market_baseline_lost": len(settled) - base_wins,
            "market_baseline_survival_rate_pct": None if not settled else round(100 * base_wins / len(settled), 1),
            "distinct_from_market_baseline_weeks": distinct,
            "proof_status": proof,
            "minimum_independent_weeks_for_review": 10,
            "automatic_promotion": False,
        },
        "rules": [
            "Forward proof begins only after a current-week rule-confirmed shadow recommendation is frozen.",
            "Historical user picks are not retroactively relabeled as HULK model recommendations.",
            "Performance is compared with the safest eligible market-favorite baseline from the same frozen week.",
            "At least 10 independent weeks and at least 3 strategy-vs-baseline differences are required before review-candidate status.",
            "No automatic Survivor pick promotion or external pool submission occurs.",
        ],
    }

def public_current_payload(current):
    """Return Survivor research safe for anonymous commercial clients.

    Personal entry name/status/week, used teams, saved picks, pool-specific
    rule state, and recommendation state remain server-side.
    """
    pool_week = int(current.get("pool_current_week") or 0)
    strategy = load_csv(STRATEGY)
    rows = []

    if not strategy.empty:
        if "current_week" in strategy.columns:
            strategy = strategy[
                pd.to_numeric(strategy["current_week"], errors="coerce").eq(pool_week)
            ].copy()
        strategy["_start"] = pd.to_datetime(strategy.get("start"), errors="coerce", utc=True)
        strategy = strategy[strategy["_start"].notna()].copy()
        strategy = strategy[strategy["_start"].map(lambda x: x.to_pydatetime() > now())].copy()

        for _, row in strategy.iterrows():
            team = clean(row.get("survivor_team"))
            if not team:
                continue
            action = clean(row.get("strategy_action")).upper()
            tier = clean(row.get("hulk_decision_tier")).upper()
            rows.append({
                "team": team,
                "opponent": clean(row.get("opponent")),
                "start": clean(row.get("start")),
                "market_prob_pct": num(row.get("market_prob_pct")),
                "spread": num(row.get("survivor_spread")),
                "hulk_context_score": num(row.get("hulk_context_score")),
                "future_value_index": num(row.get("future_value_index")),
                "future_value_label": clean(row.get("future_value_label")),
                "strategy_index": num(row.get("strategy_index")),
                "strategy_action": action,
                "decision_tier": tier,
                "risk_signals": clean(row.get("risk_signals")),
                "positive_signals": clean(row.get("positive_signals")),
                "eligible_for_shadow": action not in {"AVOID"} and tier not in {"CAUTION"},
            })

    rows.sort(
        key=lambda r: (
            -(r.get("strategy_index") if r.get("strategy_index") is not None else -999),
            -(r.get("market_prob_pct") if r.get("market_prob_pct") is not None else -999),
        )
    )

    return {
        "generated_at": current.get("generated_at"),
        "status": current.get("status", "READY"),
        "model_version": current.get("model_version", MODEL_VERSION),
        "pool_current_week": pool_week or None,
        "mode": "GENERIC_RESEARCH_ONLY",
        "personal_context_required": True,
        "candidate_count": len(rows),
        "candidates": rows,
        "recommendation_status": "PERSONAL_CONTEXT_REQUIRED",
        "shadow_recommendation": [],
        "safest_market_baseline": [],
        "rules": [
            "Anonymous Survivor data is generic research only.",
            "Used-team history, saved picks, pool ownership, and pool-specific rules require an authenticated member account.",
            "Already-started games are removed before generic research ranking.",
            "CAUTION and AVOID candidates are never presented as recommendation-ready.",
            "No pick is submitted to an external pool automatically.",
        ],
    }


def public_forward_payload(summary, public_current):
    safe = dict(summary or {})
    safe["current"] = public_current
    return safe

def main():
    current = current_payload()
    capture_result = capture(current)
    settled_now = settle()
    summary = build_summary(current, capture_result, settled_now)

    public_current = public_current_payload(current)
    public_forward = public_forward_payload(summary, public_current)

    write_json(CURRENT, current)
    write_json(SUMMARY, summary)
    write_json(PUBLIC_CURRENT, public_current)
    write_json(PUBLIC_FORWARD, public_forward)
    if DIST.exists():
        write_json(DIST_CURRENT, public_current)
        write_json(DIST_FORWARD, public_forward)

    print(json.dumps({
        "status": "READY",
        "current_week": current.get("pool_current_week"),
        "active_entry": current.get("active_entry"),
        "entry_week": current.get("active_entry_week"),
        "recommendation_status": current.get("recommendation_status"),
        "required_picks": current.get("required_picks"),
        "ownership_status": current.get("ownership", {}).get("status"),
        "candidate_count": current.get("candidate_count"),
        "capture": capture_result,
        "forward": summary["forward"],
    }, indent=2))

if __name__ == "__main__":
    main()
