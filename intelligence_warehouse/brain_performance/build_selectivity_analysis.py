#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

THRESHOLDS = [65, 67.5, 70, 72.5, 75, 77.5, 80, 82.5, 85, 87.5, 90, 92.5, 95]
ELIGIBLE_LANES = {"GAME", "PROP", "PRIZEPICKS"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def wilson(wins, losses, z=1.96):
    n = int(wins) + int(losses)
    if n <= 0:
        return None, None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def metrics(frame):
    if frame is None or frame.empty:
        return {
            "decisions": 0, "wins": 0, "losses": 0, "pushes": 0,
            "hit_rate_pct": None, "wilson_low_pct": None, "wilson_high_pct": None,
        }
    grade = frame["grade"].astype(str).str.upper()
    wins = int((grade == "WIN").sum())
    losses = int((grade == "LOSS").sum())
    pushes = int((grade == "PUSH").sum())
    decisions = wins + losses
    low, high = wilson(wins, losses)
    return {
        "decisions": decisions,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate_pct": None if decisions == 0 else round(100 * wins / decisions, 1),
        "wilson_low_pct": None if low is None else round(100 * low, 1),
        "wilson_high_pct": None if high is None else round(100 * high, 1),
    }


def order_frame(frame):
    out = frame.copy()
    start = pd.to_datetime(out.get("start"), errors="coerce", utc=True)
    snap = pd.to_datetime(out.get("_snapshot"), errors="coerce", utc=True)
    if not isinstance(snap, pd.Series):
        snap = pd.to_datetime(out.get("snapshot_at"), errors="coerce", utc=True)
    out["_order_time"] = start.fillna(snap)
    out["_order_time"] = out["_order_time"].fillna(pd.Timestamp("1970-01-01", tz="UTC"))
    return out.sort_values(["_order_time", "recommendation_key"])


def split_time(frame, train_fraction=0.70):
    ordered = order_frame(frame)
    n = len(ordered)
    if n < 2:
        return ordered, ordered.iloc[0:0]
    cut = max(1, min(n - 1, int(math.floor(n * train_fraction))))
    return ordered.iloc[:cut].copy(), ordered.iloc[cut:].copy()


def threshold_candidates(train, holdout, baseline_train, baseline_holdout):
    train_score = pd.to_numeric(train["score"], errors="coerce")
    hold_score = pd.to_numeric(holdout["score"], errors="coerce")
    rows = []

    min_train = max(12, int(math.ceil(len(train) * 0.30)))
    min_holdout = max(5, int(math.ceil(len(holdout) * 0.25)))

    for threshold in THRESHOLDS:
        t = train[train_score >= threshold].copy()
        h = holdout[hold_score >= threshold].copy()

        tm = metrics(t)
        hm = metrics(h)
        if tm["decisions"] < min_train:
            continue

        train_retention = round(100 * tm["decisions"] / max(1, baseline_train["decisions"]), 1)
        hold_retention = round(100 * hm["decisions"] / max(1, baseline_holdout["decisions"]), 1)
        train_delta = None if tm["hit_rate_pct"] is None or baseline_train["hit_rate_pct"] is None else round(
            tm["hit_rate_pct"] - baseline_train["hit_rate_pct"], 1
        )
        hold_delta = None if hm["hit_rate_pct"] is None or baseline_holdout["hit_rate_pct"] is None else round(
            hm["hit_rate_pct"] - baseline_holdout["hit_rate_pct"], 1
        )

        rows.append({
            "threshold": threshold,
            "train": tm,
            "holdout": hm,
            "train_retention_pct": train_retention,
            "holdout_retention_pct": hold_retention,
            "train_hit_rate_delta_pp": train_delta,
            "holdout_hit_rate_delta_pp": hold_delta,
            "minimum_holdout_decisions": min_holdout,
        })
    return rows


def choose_candidate(candidates, baseline_train):
    eligible = []
    for row in candidates:
        tm = row["train"]
        delta = row.get("train_hit_rate_delta_pp")
        if delta is None or delta < 3.0:
            continue
        if row["train_retention_pct"] < 30:
            continue
        # Favor lower confidence bounds first, then hit rate, then retention.
        eligible.append(row)

    if not eligible:
        return None

    return max(
        eligible,
        key=lambda row: (
            row["train"].get("wilson_low_pct") or -1,
            row["train"].get("hit_rate_pct") or -1,
            row.get("train_retention_pct") or -1,
            -(row.get("threshold") or 0),
        ),
    )


def candidate_status(candidate, baseline_holdout, lane, market):
    if candidate is None:
        return "HOLD_CURRENT_THRESHOLD", "No training threshold improved enough while retaining a useful sample."

    hm = candidate["holdout"]
    hold_n = int(hm.get("decisions") or 0)
    min_hold = int(candidate.get("minimum_holdout_decisions") or 5)
    delta = candidate.get("holdout_hit_rate_delta_pp")
    rate = hm.get("hit_rate_pct")

    if hold_n < min_hold:
        return (
            "PROMISING_NEEDS_MORE_HOLDOUT",
            "Training improved, but too few newer settled decisions remain above the threshold.",
        )

    if delta is not None and delta >= 3.0:
        if lane == "GAME" and market == "MONEYLINE":
            return (
                "VALIDATED_ACCURACY_CANDIDATE_PRICE_AWARE_REVIEW_REQUIRED",
                "The newer holdout improved in win rate, but moneyline profitability still depends on captured price.",
            )
        return (
            "VALIDATED_SELECTIVITY_CANDIDATE",
            "The stricter score threshold improved both the older training sample and the newer holdout sample.",
        )

    if delta is not None and delta <= -2.0:
        return (
            "REJECTED_BY_HOLDOUT",
            "The threshold looked better historically but failed on the newer holdout sample.",
        )

    return (
        "HOLD_CURRENT_THRESHOLD",
        "The newer holdout did not show enough improvement to justify a stricter promotion threshold.",
    )


def analyze_scope(frame, sport, lane, market=None):
    x = frame[
        frame["sport"].astype(str).str.upper().eq(sport)
        & frame["lane"].astype(str).str.upper().eq(lane)
    ].copy()

    if market is not None:
        x = x[x["market"].fillna("").astype(str).str.upper().eq(market)].copy()

    x["score"] = pd.to_numeric(x["score"], errors="coerce")
    x = x[x["score"].notna()].copy()
    if len(x) < 24:
        return {
            "sport": sport,
            "lane": lane,
            "market": market,
            "status": "INSUFFICIENT_SAMPLE",
            "sample": int(len(x)),
            "reason": "At least 24 scored settled decisions are required for a train/holdout threshold test.",
        }

    train, holdout = split_time(x)
    baseline_train = metrics(train)
    baseline_holdout = metrics(holdout)
    baseline_all = metrics(x)

    candidates = threshold_candidates(train, holdout, baseline_train, baseline_holdout)
    candidate = choose_candidate(candidates, baseline_train)
    status, reason = candidate_status(candidate, baseline_holdout, lane, market)

    current_min = float(x["score"].min()) if not x.empty else None
    result = {
        "sport": sport,
        "lane": lane,
        "market": market,
        "sample": int(len(x)),
        "current_observed_min_score": current_min,
        "baseline": baseline_all,
        "train_baseline": baseline_train,
        "holdout_baseline": baseline_holdout,
        "status": status,
        "reason": reason,
        "automatic_change_applied": False,
        "price_aware_profitability_validated": False,
        "candidate": None,
    }

    if candidate is not None:
        result["candidate"] = {
            "minimum_score": candidate["threshold"],
            "train": candidate["train"],
            "holdout": candidate["holdout"],
            "train_retention_pct": candidate["train_retention_pct"],
            "holdout_retention_pct": candidate["holdout_retention_pct"],
            "train_hit_rate_delta_pp": candidate["train_hit_rate_delta_pp"],
            "holdout_hit_rate_delta_pp": candidate["holdout_hit_rate_delta_pp"],
        }
    return result


def score_bands(frame):
    x = frame.copy()
    x["score"] = pd.to_numeric(x["score"], errors="coerce")
    x = x[x["score"].notna()].copy()
    if x.empty:
        return []

    bins = [-math.inf, 69.999, 74.999, 79.999, 84.999, 89.999, math.inf]
    labels = ["<70", "70–74.9", "75–79.9", "80–84.9", "85–89.9", "90+"]
    x["_score_band"] = pd.cut(x["score"], bins=bins, labels=labels)

    rows = []
    for (sport, lane, band), group in x.groupby(["sport", "lane", "_score_band"], observed=True):
        m = metrics(group)
        if m["decisions"] < 5:
            continue
        rows.append({
            "sport": str(sport),
            "lane": str(lane),
            "score_band": str(band),
            **m,
        })
    return rows


def calibration_audit(frame):
    x = frame.copy()
    x["score"] = pd.to_numeric(x["score"], errors="coerce")
    x = x[x["score"].notna()].copy()
    x = x[x["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])].copy()
    if x.empty:
        return []

    rows = []
    for (sport, lane), group in x.groupby(["sport", "lane"]):
        if len(group) < 20:
            continue

        g = group.copy()
        g["_win"] = g["grade"].astype(str).str.upper().eq("WIN").astype(int)
        score_rank = g["score"].rank(method="average")
        win_rank = g["_win"].rank(method="average")
        rho = score_rank.corr(win_rank)

        median = g["score"].median()
        low = g[g["score"] < median]
        high = g[g["score"] >= median]
        low_m = metrics(low)
        high_m = metrics(high)

        q75 = g["score"].quantile(0.75)
        top = g[g["score"] >= q75]
        rest = g[g["score"] < q75]
        top_m = metrics(top)
        rest_m = metrics(rest)

        min_comparison = max(8, int(math.ceil(len(g) * 0.15)))

        half_delta = None
        if (
            low_m["decisions"] >= min_comparison
            and high_m["decisions"] >= min_comparison
            and high_m["hit_rate_pct"] is not None
            and low_m["hit_rate_pct"] is not None
        ):
            half_delta = round(high_m["hit_rate_pct"] - low_m["hit_rate_pct"], 1)

        top_delta = None
        if (
            top_m["decisions"] >= min_comparison
            and rest_m["decisions"] >= min_comparison
            and top_m["hit_rate_pct"] is not None
            and rest_m["hit_rate_pct"] is not None
        ):
            top_delta = round(top_m["hit_rate_pct"] - rest_m["hit_rate_pct"], 1)

        rho_value = None if pd.isna(rho) else round(float(rho), 3)

        if (
            (rho_value is not None and rho_value <= -0.15)
            or (top_delta is not None and top_delta <= -10)
        ):
            status = "NEGATIVE_ORDERING_WARNING"
            reason = "Higher evidence scores have not translated into better outcomes in this archive."
        elif (
            rho_value is not None
            and rho_value >= 0.15
            and half_delta is not None
            and half_delta >= 5
        ):
            status = "POSITIVE_ORDERING_EVIDENCE"
            reason = "Higher evidence scores are directionally associated with better outcomes, but still need forward validation."
        else:
            status = "FLAT_OR_UNPROVEN_ORDERING"
            reason = "The archive does not yet show a reliable monotonic relationship between score and outcome."

        rows.append({
            "sport": str(sport),
            "lane": str(lane),
            "decisions": int(len(g)),
            "score_min": round(float(g["score"].min()), 2),
            "score_max": round(float(g["score"].max()), 2),
            "score_median": round(float(median), 2),
            "spearman_rank_correlation": rho_value,
            "lower_half": low_m,
            "upper_half": high_m,
            "upper_minus_lower_hit_rate_pp": half_delta,
            "top_quartile": top_m,
            "rest": rest_m,
            "top_quartile_minus_rest_hit_rate_pp": top_delta,
            "status": status,
            "reason": reason,
            "score_is_probability": False,
            "automatic_change_applied": False,
        })

    priority = {
        "NEGATIVE_ORDERING_WARNING": 0,
        "POSITIVE_ORDERING_EVIDENCE": 1,
        "FLAT_OR_UNPROVEN_ORDERING": 2,
    }
    rows.sort(key=lambda row: (
        priority.get(row["status"], 9),
        -(row.get("decisions") or 0),
        row["sport"],
        row["lane"],
    ))
    return rows


def segment_watch(frame):
    x = frame.copy()
    x["market"] = x["market"].fillna("").astype(str).str.upper()
    x["side"] = x["side"].fillna("").astype(str).str.upper()

    results = []
    for keys, group in x.groupby(["sport", "lane", "market", "side"], dropna=False):
        sport, lane, market, side = [str(v) for v in keys]
        m = metrics(group)
        n = m["decisions"]
        if n < 8:
            continue

        rate = m["hit_rate_pct"]
        low = m["wilson_low_pct"]
        high = m["wilson_high_pct"]

        if lane == "PARLAY":
            status = "PRICE_REQUIRED"
        elif n >= 20 and low is not None and low > 50:
            status = "POSITIVE_EVIDENCE"
        elif n >= 20 and rate is not None and rate < 45:
            status = "NEGATIVE_EVIDENCE"
        elif n >= 10 and rate is not None and rate <= 35:
            status = "NEGATIVE_EVIDENCE_SMALL_SAMPLE"
        else:
            status = "OBSERVE"

        results.append({
            "sport": sport,
            "lane": lane,
            "market": market or "UNKNOWN",
            "side": side or "UNSPECIFIED",
            **m,
            "status": status,
            "automatic_change_applied": False,
            "profitability_note": (
                "Hit rate only; price/payout-aware profitability is not established."
            ),
        })

    priority = {
        "NEGATIVE_EVIDENCE": 0,
        "POSITIVE_EVIDENCE": 1,
        "NEGATIVE_EVIDENCE_SMALL_SAMPLE": 2,
        "OBSERVE": 3,
        "PRICE_REQUIRED": 4,
    }
    results.sort(key=lambda row: (
        priority.get(row["status"], 9),
        -(row.get("decisions") or 0),
        row["sport"], row["lane"], row["market"], row["side"],
    ))
    return results


def build_selectivity(rows):
    if rows is None or rows.empty:
        return {
            "generated_at": now_iso(),
            "status": "WAITING",
            "threshold_tests": [],
            "segments": [],
            "score_bands": [],
            "calibration_audit": [],
        }

    x = rows[
        rows["settled"]
        & rows["qualified"]
        & rows["lane"].astype(str).str.upper().isin(ELIGIBLE_LANES)
    ].copy()

    if x.empty:
        return {
            "generated_at": now_iso(),
            "status": "WAITING",
            "threshold_tests": [],
            "segments": [],
            "score_bands": [],
            "calibration_audit": [],
        }

    tests = []

    # Lane-level tests for player-style markets.
    for (sport, lane), group in x.groupby(["sport", "lane"]):
        sport = str(sport).upper()
        lane = str(lane).upper()
        if lane in {"PROP", "PRIZEPICKS"}:
            tests.append(analyze_scope(x, sport, lane, None))

    # Market-specific tests keep moneylines/spreads/totals from being mixed.
    markets = (
        x.assign(_market=x["market"].fillna("").astype(str).str.upper())
        .groupby(["sport", "lane", "_market"])
        .size()
    )
    for (sport, lane, market), count in markets.items():
        sport = str(sport).upper()
        lane = str(lane).upper()
        market = str(market).upper()
        if not market or int(count) < 24:
            continue
        tests.append(analyze_scope(x, sport, lane, market))

    actionable = [
        row for row in tests
        if row.get("status") in {
            "VALIDATED_SELECTIVITY_CANDIDATE",
            "VALIDATED_ACCURACY_CANDIDATE_PRICE_AWARE_REVIEW_REQUIRED",
            "REJECTED_BY_HOLDOUT",
            "PROMISING_NEEDS_MORE_HOLDOUT",
        }
    ]

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "method": "70_30_TIME_ORDERED_TRAIN_HOLDOUT",
        "automatic_model_changes": False,
        "rules": [
            "Thresholds are selected on older settled decisions and checked on newer settled decisions.",
            "No threshold is promoted from training performance alone.",
            "Moneyline accuracy candidates still require price-aware ROI review.",
            "Parlays are excluded from threshold promotion until payout economics are consistently captured.",
            "This is research guidance, not the official public betting record.",
        ],
        "threshold_tests": tests,
        "actionable": actionable,
        "segments": segment_watch(x),
        "score_bands": score_bands(x),
        "calibration_audit": calibration_audit(x),
    }


def main():
    import sys
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import build_brain_performance as brain

    rows, _ = brain.load_all_rows()
    payload = build_selectivity(rows)

    root = here.parents[1]
    out = here / "SELECTIVITY_ANALYSIS.json"
    public = root / "commercial_web" / "public" / "selectivity_analysis.json"
    dist = root / "commercial_web" / "dist" / "selectivity_analysis.json"

    rendered = json.dumps(payload, indent=2)
    out.write_text(rendered)
    public.write_text(rendered)
    if dist.parent.exists():
        dist.write_text(rendered)

    print(json.dumps({
        "status": payload["status"],
        "threshold_tests": len(payload["threshold_tests"]),
        "actionable": len(payload["actionable"]),
        "segments": len(payload["segments"]),
    }, indent=2))


if __name__ == "__main__":
    main()
