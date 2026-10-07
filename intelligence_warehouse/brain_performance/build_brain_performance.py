#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from build_selectivity_analysis import build_selectivity

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from intelligence_warehouse.betting_v2.forward_results_audit import audit_forward_ledgers
OUT_DIR = ROOT / "intelligence_warehouse" / "brain_performance"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "BRAIN_PERFORMANCE.json"
SELECTIVITY_OUT = OUT_DIR / "SELECTIVITY_ANALYSIS.json"
PUBLIC = ROOT / "commercial_web" / "public" / "brain_performance.json"
PUBLIC_SELECTIVITY = ROOT / "commercial_web" / "public" / "selectivity_analysis.json"
DIST = ROOT / "commercial_web" / "dist" / "brain_performance.json"
DIST_SELECTIVITY = ROOT / "commercial_web" / "dist" / "selectivity_analysis.json"

DFS_SUMMARY = ROOT / "intelligence_warehouse" / "dfs_accountability" / "DFS_ACCOUNTABILITY_SUMMARY.json"
DFS_REPLAY = ROOT / "intelligence_warehouse" / "dfs_accountability" / "DFS_REPLAY_BACKTEST.json"
FANTASY_V2_CURRENT = ROOT / "intelligence_warehouse" / "fantasy_accountability" / "FANTASY_V2_CURRENT.json"
FANTASY_V2_FORWARD = ROOT / "intelligence_warehouse" / "fantasy_accountability" / "FANTASY_V2_FORWARD_SUMMARY.json"
SURVIVOR_V2_CURRENT = ROOT / "commercial_web" / "public" / "survivor_v2_current.json"
SURVIVOR_V2_FORWARD = ROOT / "commercial_web" / "public" / "survivor_v2_forward.json"
SELECTIVITY_SHADOW = ROOT / "intelligence_warehouse" / "selectivity_shadow" / "SELECTIVITY_SHADOW_SUMMARY.json"
BETTING_V2_CURRENT = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_CURRENT.json"
BETTING_V2_VALIDATION = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_VALIDATION.json"
BETTING_V2_MODEL = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_MODEL.json"
BETTING_V2_CLV = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_CLV.json"
BETTING_V2_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_FORWARD_SUMMARY.json"
BETTING_V2_ALL_CURRENT = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_ALL_MARKETS_CURRENT.json"
BETTING_V2_ALL_VALIDATION = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_ALL_MARKETS_VALIDATION.json"
BETTING_V2_ALL_MODELS = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_ALL_MARKETS_MODELS.json"
BETTING_V2_ALL_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json"
BETTING_V2_ALL_DEVIG = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_ALL_MARKET_DEVIG.json"
BETTING_V2_GAME_CHALLENGERS = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_GAME_CHALLENGERS.json"
BETTING_V2_GAME_CHALLENGER_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "BETTING_V2_GAME_CHALLENGER_FORWARD_SUMMARY.json"
PROP_V2_CURRENT = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_CURRENT.json"
PROP_V2_VALIDATION = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_VALIDATION.json"
PROP_V2_MODELS = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_MODELS.json"
PROP_V2_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_FORWARD_SUMMARY.json"
PROP_V2_DEVIG = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_DEVIG.json"
PROP_V2_CHALLENGERS = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_CHALLENGERS.json"
PROP_V2_SEGMENTS = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_MARKET_SEGMENTS.json"
PROP_V2_POINTS_SEGMENT_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "PROP_V2_POINTS_SEGMENT_FORWARD_SUMMARY.json"
PARLAY_V2_CURRENT = ROOT / "intelligence_warehouse" / "betting_v2" / "PARLAY_V2_CURRENT.json"
PARLAY_V2_VALIDATION = ROOT / "intelligence_warehouse" / "betting_v2" / "PARLAY_V2_VALIDATION.json"
PARLAY_V2_FORWARD = ROOT / "intelligence_warehouse" / "betting_v2" / "PARLAY_V2_FORWARD_SUMMARY.json"
EXPERIMENT_REGISTRY_SUMMARY = ROOT / "intelligence_warehouse" / "experiment_registry" / "SPORTS_HULK_EXPERIMENT_SUMMARY.json"

SPORT_FILES = {
    "NFL": ROOT / "nfl_live" / "decision" / "history" / "NFL_GRADED_RECOMMENDATIONS.csv",
    "MLB": ROOT / "mlb_live" / "decision" / "history" / "MLB_GRADED_RECOMMENDATIONS.csv",
    "NBA": ROOT / "nba_live" / "decision" / "history" / "NBA_GRADED_RECOMMENDATIONS.csv",
    "NHL": ROOT / "nhl_live" / "decision" / "history" / "NHL_GRADED_RECOMMENDATIONS.csv",
    "CFB": ROOT / "cfb_live" / "decision" / "history" / "CFB_GRADED_RECOMMENDATIONS.csv",
    "CBB": ROOT / "cbb_live" / "decision" / "history" / "CBB_GRADED_RECOMMENDATIONS.csv",
}

SETTLED = {"WIN", "LOSS", "PUSH"}
QUALIFIED_DECISIONS = {
    "QUALIFIED_RESEARCH",
    "QUALIFIED",
    "PLAY",
    "BET",
}
MODEL_VERSION = "BRAIN_RECORD_V1_2026_10_05"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def norm(value):
    return str(value or "").strip().upper()


def safe_float(value):
    try:
        value = float(value)
        return None if math.isnan(value) else value
    except Exception:
        return None


def wilson(wins, losses, z=1.96):
    n = wins + losses
    if n <= 0:
        return None, None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def maturity(decisions):
    if decisions <= 0:
        return "WAITING"
    if decisions < 10:
        return "TINY SAMPLE"
    if decisions < 30:
        return "BUILDING"
    if decisions < 100:
        return "EARLY"
    return "MATURING"


def metric_from_rows(rows, label, lane=None, sport=None):
    if rows.empty:
        return {
            "label": label, "lane": lane, "sport": sport,
            "wins": 0, "losses": 0, "pushes": 0, "decisions": 0,
            "hit_rate_pct": None, "wilson_low_pct": None,
            "wilson_high_pct": None, "maturity": "WAITING",
            "units": None, "roi_pct": None,
            "units_status": "WAITING FOR CONSISTENT PRICE CAPTURE",
        }

    grades = rows["grade"].astype(str).str.upper()
    wins = int((grades == "WIN").sum())
    losses = int((grades == "LOSS").sum())
    pushes = int((grades == "PUSH").sum())
    decisions = wins + losses
    low, high = wilson(wins, losses)
    return {
        "label": label,
        "lane": lane,
        "sport": sport,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "decisions": decisions,
        "hit_rate_pct": None if decisions == 0 else round(100 * wins / decisions, 1),
        "wilson_low_pct": None if low is None else round(100 * low, 1),
        "wilson_high_pct": None if high is None else round(100 * high, 1),
        "maturity": maturity(decisions),
        "units": None,
        "roi_pct": None,
        "units_status": "WAITING FOR CONSISTENT PRICE CAPTURE",
    }


def canonical_rows(path, sport):
    if not path.exists():
        return pd.DataFrame()

    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

    if d.empty or "grade" not in d.columns:
        return pd.DataFrame()

    d = d.copy()
    d["sport"] = sport
    d["grade"] = d["grade"].astype(str).str.upper()
    if "lane" not in d.columns:
        d["lane"] = ""
    d["lane"] = d["lane"].astype(str).str.upper()
    if "decision" not in d.columns:
        d["decision"] = ""
    d["decision"] = d["decision"].astype(str).str.upper()

    if "snapshot_at" in d.columns:
        d["_snapshot"] = pd.to_datetime(d["snapshot_at"], errors="coerce", utc=True)
    else:
        d["_snapshot"] = pd.NaT

    if "recommendation_key" not in d.columns:
        d["recommendation_key"] = [
            f"{sport}|{i}" for i in range(len(d))
        ]
    d["recommendation_key"] = d["recommendation_key"].astype(str)

    chosen = []
    for _, group in d.groupby("recommendation_key", sort=False):
        group = group.sort_values("_snapshot")
        settled = group[group["grade"].isin(SETTLED)]
        if not settled.empty:
            chosen.append(settled.iloc[-1])
        else:
            chosen.append(group.iloc[-1])

    if not chosen:
        return pd.DataFrame()

    out = pd.DataFrame(chosen).reset_index(drop=True)
    out["settled"] = out["grade"].isin(SETTLED)
    out["qualified"] = out["decision"].isin(QUALIFIED_DECISIONS)
    return out


def load_all_rows():
    frames = []
    source_health = []
    for sport, path in SPORT_FILES.items():
        rows = canonical_rows(path, sport)
        frames.append(rows)
        source_health.append({
            "sport": sport,
            "path": str(path.relative_to(ROOT)),
            "available": path.exists(),
            "canonical_recommendations": int(len(rows)),
            "settled": int(rows["settled"].sum()) if not rows.empty else 0,
        })
    nonempty = [x for x in frames if not x.empty]
    return (
        pd.concat(nonempty, ignore_index=True, sort=False)
        if nonempty else pd.DataFrame()
    ), source_health


def qualified_settled(rows, lane=None, sport=None):
    if rows.empty:
        return rows
    x = rows[rows["settled"]].copy()
    if lane is not None:
        x = x[x["lane"].eq(lane)]
    if sport is not None:
        x = x[x["sport"].eq(sport)]
    # Main record intentionally excludes low-confidence leans.
    if "qualified" in x.columns:
        x = x[x["qualified"]]
    return x


def lane_metric(rows, lane, label):
    return metric_from_rows(qualified_settled(rows, lane=lane), label, lane=lane)


def sport_metrics(rows):
    result = []
    for sport in SPORT_FILES:
        x = qualified_settled(rows, sport=sport)
        # Best-bet/prop lanes only for the sport headline; parlays remain separate.
        if not x.empty:
            x = x[x["lane"].isin(["GAME", "PROP", "PRIZEPICKS"])]
        result.append(metric_from_rows(x, sport, sport=sport))
    return result


def dfs_payload():
    summary = read_json(DFS_SUMMARY, {})
    replay = read_json(DFS_REPLAY, {})
    replay_rows = replay.get("strategy_summary") or []

    modes = []
    for row in replay_rows:
        modes.append({
            "platform": row.get("platform"),
            "mode": row.get("mode"),
            "replay_slates": row.get("slates", 0),
            "avg_actual_points": row.get("avg_actual_points"),
            "avg_projection_error": row.get("avg_projection_error"),
            "avg_random_baseline_percentile": row.get("avg_random_baseline_percentile"),
            "random_baseline_salary_floor_pct": 94.0,
            "beat_random_median_rate_pct": row.get("beat_random_median_rate"),
            "top_10pct_vs_random_rate_pct": row.get("top_10pct_vs_random_rate"),
            "avg_actual_minus_max_projection": row.get("avg_actual_minus_max_projection"),
            "beat_max_projection_rate_pct": row.get("beat_max_projection_rate"),
            "distinct_lineup_rate_pct": row.get("distinct_lineup_rate"),
            "mode_collision_slates": row.get("mode_collision_slates", 0),
            "replay_evidence_status": row.get("evidence_status"),
            "promotion_eligible": bool(row.get("promotion_eligible", False)),
            "contest_cash_rate_pct": None,
            "contest_percentile": None,
            "evidence_type": "PRELOCK_REPLAY_VS_SALARY_EFFICIENT_RANDOM_AND_MAX_PROJECTION",
            "maturity": row.get("evidence_status") or maturity(int(row.get("slates") or 0)),
        })

    forward_bundle = summary.get("forward", {}) or {}
    forward = forward_bundle.get("summary") or []
    forward_grades = forward_bundle.get("grades") or []
    capture = summary.get("capture") or {}
    return {
        "status": "BUILDING SAMPLE" if modes else "WAITING",
        "model_version": summary.get("model_version"),
        "forward_official_snapshots": len(forward_grades),
        "forward_version_counts": forward_bundle.get("version_counts") or {},
        "forward_new_snapshots_last_run": int(capture.get("new_snapshots") or 0),
        "forward_summary": forward,
        "replay_modes": modes,
        "contest_cash_rate_pct": None,
        "contest_tournament_percentile": None,
        "contest_metrics_status": (
            summary.get("contest_metrics", {}).get("reason")
            or "Real contest cut lines/standings are not connected yet."
        ),
        "warning": "Random-baseline percentile is NOT a real contest percentile.",
    }


def selectivity_watch(metrics):
    watch = []
    for item in metrics:
        decisions = int(item.get("decisions") or 0)
        rate = item.get("hit_rate_pct")
        low = item.get("wilson_low_pct")
        lane = str(item.get("lane") or "").upper()
        if lane == "PARLAY":
            status = "WAITING_FOR_PAYOUT_ECONOMICS"
            reason = "Parlay hit rate is not comparable to straight bets; payout and price capture are required before strategy changes."
        elif decisions < 30:
            status = "OBSERVE"
            reason = "Sample is too small to tighten or expand automatically."
        elif low is not None and low > 50:
            status = "CANDIDATE_FOR_TIGHTER_PROMOTION_TEST"
            reason = "Lower confidence bound is above 50%; requires review before any model change."
        elif rate is not None and rate < 52:
            status = "CANDIDATE_FOR_MORE_SELECTIVITY"
            reason = "Observed hit rate is weak enough to review stricter thresholds."
        else:
            status = "HOLD"
            reason = "No evidence-backed threshold change yet."
        watch.append({
            "label": item.get("label"),
            "decisions": decisions,
            "hit_rate_pct": rate,
            "wilson_low_pct": low,
            "status": status,
            "reason": reason,
            "automatic_change_applied": False,
        })
    return watch


def main():
    rows, source_health = load_all_rows()

    best_bets = lane_metric(rows, "GAME", "Best Bets")
    props = lane_metric(rows, "PROP", "Props")
    parlays = lane_metric(rows, "PARLAY", "Parlays")
    prizepicks = lane_metric(rows, "PRIZEPICKS", "PrizePicks")
    categories = [best_bets, props, parlays, prizepicks]
    sports = sport_metrics(rows)
    dfs = dfs_payload()
    forward_results_accountability = audit_forward_ledgers(ROOT)
    fantasy_v2 = {
        "current": read_json(FANTASY_V2_CURRENT, {
            "status": "WAITING",
            "lanes": {},
        }),
        "forward": read_json(FANTASY_V2_FORWARD, {
            "status": "WAITING",
            "weekly": {},
            "defense_streaming": {},
        }),
    }
    selectivity = build_selectivity(rows)
    selectivity_shadow = read_json(SELECTIVITY_SHADOW, {
        "status": "WAITING",
        "experiments": [],
        "automatic_live_changes": False,
    })
    betting_v2 = {
        "current": read_json(BETTING_V2_CURRENT, {
            "status": "WAITING",
            "mode": "SHADOW_ONLY",
            "summary": {},
            "picks": [],
        }),
        "validation": read_json(BETTING_V2_VALIDATION, {}),
        "model": read_json(BETTING_V2_MODEL, {}),
        "clv": read_json(BETTING_V2_CLV, {
            "status": "WAITING",
            "summary": {},
            "by_sport": {},
            "open_picks": [],
            "recent_closed": [],
        }),
        "forward": read_json(BETTING_V2_FORWARD, {
            "status": "WAITING",
            "all_predictions": {},
            "monitor_selection": {},
            "promotion": {},
            "by_sport": {},
        }),
    }
    betting_v2_all_markets = {
        "current": read_json(BETTING_V2_ALL_CURRENT, {
            "status": "WAITING",
            "summary": {},
            "by_lane": {},
            "picks": [],
        }),
        "validation": read_json(BETTING_V2_ALL_VALIDATION, {
            "status": "WAITING",
            "lanes": {},
        }),
        "models": read_json(BETTING_V2_ALL_MODELS, {
            "status": "WAITING",
            "models": {},
        }),
        "forward": read_json(BETTING_V2_ALL_FORWARD, {
            "status": "WAITING",
            "all_predictions": {},
            "shadow_selection": {},
            "by_lane": {},
        }),
        "devig": read_json(BETTING_V2_ALL_DEVIG, {
            "status": "WAITING",
            "coverage": {},
        }),
        "challengers": read_json(BETTING_V2_GAME_CHALLENGERS, {
            "status": "WAITING",
            "lanes": {},
        }),
        "challenger_forward": read_json(BETTING_V2_GAME_CHALLENGER_FORWARD, {
            "status": "WAITING",
            "forward": {},
            "current": {},
        }),
    }
    parlay_v2 = {
        "current": read_json(PARLAY_V2_CURRENT, {
            "status": "WAITING",
            "summary": {},
            "by_sport": {},
            "picks": [],
        }),
        "validation": read_json(PARLAY_V2_VALIDATION, {
            "status": "WAITING",
            "by_sport": {},
        }),
        "forward": read_json(PARLAY_V2_FORWARD, {
            "status": "WAITING",
            "all_predictions": {},
            "monitor_selection": {},
            "by_sport": {},
            "promotion": {},
        }),
    }
    prop_v2 = {
        "current": read_json(PROP_V2_CURRENT, {
            "status": "WAITING",
            "summary": {},
            "by_lane": {},
            "picks": [],
        }),
        "validation": read_json(PROP_V2_VALIDATION, {
            "status": "WAITING",
            "lanes": {},
        }),
        "models": read_json(PROP_V2_MODELS, {
            "status": "WAITING",
            "models": {},
        }),
        "forward": read_json(PROP_V2_FORWARD, {
            "status": "WAITING",
            "all_predictions": {},
            "monitor_selection": {},
            "by_lane": {},
        }),
        "devig": read_json(PROP_V2_DEVIG, {
            "status": "WAITING",
            "coverage": {},
        }),
        "challengers": read_json(PROP_V2_CHALLENGERS, {
            "status": "WAITING",
            "lanes": {},
        }),
        "market_segments": read_json(PROP_V2_SEGMENTS, {
            "status": "WAITING",
            "lanes": {},
        }),
        "points_segment_forward": read_json(PROP_V2_POINTS_SEGMENT_FORWARD, {
            "status": "WAITING",
            "all_predictions": {},
            "monitor_selection": {},
            "by_lane": {},
        }),
    }

    experiment_registry = read_json(
        EXPERIMENT_REGISTRY_SUMMARY,
        {
            "registered_experiments": 0,
            "experiments_with_results": 0,
            "unresolved_experiments": 0,
            "decision_counts": {},
            "family_counts": {},
        },
    )

    total_settled = sum(int(x.get("decisions") or 0) + int(x.get("pushes") or 0) for x in categories)

    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "title": "HOW GOOD IS THE BRAIN?",
        "subtitle": "Fewer bets. Better bets. Proven results.",
        "transparency": {
            "rules": [
                "No hidden losses.",
                "No deleted losing picks.",
                "No post-lock DFS benchmark creation.",
                "Pending results stay pending.",
                "Replay metrics are labeled separately from live-forward results.",
                "No simulated DFS percentile is presented as a real contest percentile.",
            ],
            "verified_settled_decisions": total_settled,
            "units_status": "WAITING FOR CONSISTENT PRICE CAPTURE",
            "automatic_model_changes": False,
        },
        "categories": categories,
        "sports": sports,
        "dfs": dfs,
        "fantasy_v2": fantasy_v2,
        "survivor": {
            "current": read_json(SURVIVOR_V2_CURRENT, {
                "status": "WAITING",
                "recommendation_status": "WAITING",
                "candidates": [],
            }),
            "forward": read_json(SURVIVOR_V2_FORWARD, {
                "status": "WAITING",
                "forward": {},
            }),
        },
        "practice_bankroll": {
            "status": "NOT STARTED",
            "starting_bankroll": None,
            "current_bankroll": None,
            "roi_pct": None,
            "reason": "Practice betting ledger has not been launched yet.",
        },
        "selectivity_watch": selectivity_watch(categories + sports),
        "selectivity": selectivity,
        "selectivity_shadow": selectivity_shadow,
        "betting_v2": betting_v2,
        "betting_v2_all_markets": betting_v2_all_markets,
        "forward_results_accountability": forward_results_accountability,
        "parlay_v2": parlay_v2,
        "prop_v2": prop_v2,
        "experiment_registry": experiment_registry,
        "source_health": source_health,
        "definitions": {
            "hit_rate": "Wins divided by wins plus losses; pushes excluded.",
            "qualified_record": "Only settled recommendations whose decision state was qualified/play/bet.",
            "random_baseline_percentile": "Where the replayed optimizer lineup scored versus deterministic random legal lineups from the same historical pre-lock player pool.",
            "units": "Withheld until consistent wager-price capture is verified across lanes.",
        },
    }

    write_json(OUT, payload)
    write_json(PUBLIC, payload)
    # The public proof receipt follows mocked OUT/PUBLIC destinations during
    # isolated tests, never writes to production from a test worktree.
    write_json(OUT.with_name("FORWARD_RESULTS_ACCOUNTABILITY.json"), forward_results_accountability)
    write_json(PUBLIC.with_name("forward_results_accountability.json"), forward_results_accountability)
    write_json(SELECTIVITY_OUT, selectivity)
    write_json(PUBLIC_SELECTIVITY, selectivity)
    if DIST.parent.exists():
        write_json(DIST, payload)
        write_json(DIST_SELECTIVITY, selectivity)
        write_json(DIST.with_name("forward_results_accountability.json"), forward_results_accountability)

    print(json.dumps({
        "status": payload["status"],
        "verified_settled_decisions": total_settled,
        "best_bets": best_bets,
        "props": props,
        "parlays": parlays,
        "prizepicks": prizepicks,
        "dfs_replay_modes": len(dfs["replay_modes"]),
    }, indent=2))


if __name__ == "__main__":
    main()
