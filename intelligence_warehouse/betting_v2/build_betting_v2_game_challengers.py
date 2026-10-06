#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT = OUT_DIR / "BETTING_V2_GAME_CHALLENGERS.json"
PUBLIC = ROOT / "commercial_web" / "public" / "betting_v2_game_challengers.json"
DIST = ROOT / "commercial_web" / "dist" / "betting_v2_game_challengers.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))

import build_betting_v2_all_markets as game
import build_betting_v2 as base

L2_VALUES = (2.0, 5.0, 10.0, 20.0)

LANE_FEATURES = {
    "CFB_MONEYLINE": {
        "strength": ["elo_edge", "srs_edge"],
        "form": ["current_margin_edge", "l3_margin_edge"],
        "market_support": ["raw_market_support", "sportsbook_count"],
    },
    "CFB_SPREAD": {
        "strength": ["elo_edge", "srs_edge"],
        "form": ["current_margin_edge", "l3_margin_edge"],
        "market_support": ["raw_market_support", "sportsbook_count"],
        "line_context": ["line_value"],
    },
    "CFB_TOTAL": {
        "market_support": ["raw_market_support", "sportsbook_count"],
        "line_context": ["line_value", "selection_direction"],
    },
}

MIN_FEATURE_COVERAGE = 0.65
MIN_FEATURE_UNIQUE = 3


def clean(v):
    return game.clean(v)


def num(v):
    return game.num(v)


def read_history_payloads(sport, market):
    path = game.HISTORY_FILES[sport]
    if not path.exists():
        return {}
    d = pd.read_csv(path, low_memory=False)
    if d.empty:
        return {}
    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["market"].astype(str).str.upper().eq(market)
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    out = {}
    for _, row in d.iterrows():
        rec_key = game.history_rec_key(sport, row)
        try:
            payload = json.loads(row.get("payload_json") or "{}")
        except Exception:
            payload = {}
        out[rec_key] = payload
    return out


def enriched_history(sport, market):
    frame = game.build_history(sport, market)
    if frame.empty:
        return frame
    payloads = read_history_payloads(sport, market)
    rows = []
    for _, row in frame.iterrows():
        rec = row.to_dict()
        payload = payloads.get(clean(row.get("recommendation_key")), {})
        rec.update({
            "elo_edge": num(payload.get("elo_edge")),
            "srs_edge": num(payload.get("srs_edge")),
            "current_margin_edge": num(payload.get("current_margin_edge")),
            "l3_margin_edge": num(payload.get("l3_margin_edge")),
            "raw_market_support": num(payload.get("raw_market_support")),
            "sportsbook_count": num(payload.get("sportsbook_count")),
            "provider_count": num(payload.get("provider_count")),
            "hours_to_start": num(payload.get("hours_to_start")),
            "line_value": num(row.get("line")),
            "selection_direction": (
                1.0 if clean(row.get("selection")).upper() == "OVER"
                else -1.0 if clean(row.get("selection")).upper() == "UNDER"
                else 0.0
            ),
            "old_score": num(row.get("score")),
        })
        rows.append(rec)
    return pd.DataFrame(rows)


def available_features(frame, lane_key):
    groups = LANE_FEATURES.get(lane_key, {})
    valid = {}
    stats = {}
    for group, features in groups.items():
        kept = []
        for feature in features:
            series = pd.to_numeric(frame.get(feature), errors="coerce")
            coverage = float(series.notna().mean()) if len(series) else 0.0
            unique = int(series.nunique(dropna=True))
            stats[feature] = {
                "coverage_pct": round(100 * coverage, 1),
                "unique_values": unique,
            }
            if coverage >= MIN_FEATURE_COVERAGE and unique >= MIN_FEATURE_UNIQUE:
                kept.append(feature)
        if kept:
            valid[group] = kept
    return valid, stats


def ordered_blocks(frame):
    b = (
        frame.groupby("block_key", as_index=False)["_time"]
        .min()
        .sort_values("_time")
    )
    return b["block_key"].astype(str).tolist()


def fit_scaler(train, features):
    scaler = {}
    for f in features:
        s = pd.to_numeric(train[f], errors="coerce")
        median = float(s.median()) if s.notna().any() else 0.0
        filled = s.fillna(median)
        mean = float(filled.mean()) if len(filled) else 0.0
        std = float(filled.std(ddof=0)) if len(filled) else 1.0
        if not math.isfinite(std) or std < 1e-8:
            std = 1.0
        scaler[f] = {"median": median, "mean": mean, "std": std}
    return scaler


def design(frame, features, scaler):
    p = pd.to_numeric(
        frame["market_reference_probability"], errors="coerce"
    ).fillna(0.5).clip(0.005, 0.995)
    cols = [np.ones(len(frame)), np.log(p / (1 - p)).to_numpy()]
    for f in features:
        info = scaler[f]
        s = pd.to_numeric(frame[f], errors="coerce").fillna(info["median"])
        cols.append(((s - info["mean"]) / info["std"]).to_numpy())
    return np.column_stack(cols)


def candidate_specs(groups):
    rich = []
    for feats in groups.values():
        rich.extend(feats)
    rich = list(dict.fromkeys(rich))
    specs = [
        ("RICH_ONLY", rich, 5.0),
        ("RICH_PLUS_OLD_SCORE", rich + ["old_score"], 5.0),
    ]
    for group, feats in groups.items():
        remaining = [f for f in rich if f not in feats]
        if remaining:
            specs.append((f"DROP_GROUP:{group}", remaining, 5.0))
    for l2 in L2_VALUES:
        if l2 != 5.0:
            specs.append((f"RICH_L2:{l2:g}", rich, l2))
    # Deduplicate exact feature/l2 specs.
    seen = set()
    out = []
    for label, features, l2 in specs:
        key = (tuple(features), float(l2))
        if key in seen:
            continue
        seen.add(key)
        out.append((label, features, l2))
    return out


def evaluate(y, p):
    return game.evaluate(
        np.asarray(y, dtype=float),
        np.asarray(p, dtype=float),
    )


def fit_predict(train, test, features, l2):
    scaler = fit_scaler(train, features)
    X_train = design(train, features, scaler)
    X_test = design(test, features, scaler)
    y_train = train["outcome"].astype(int).to_numpy()
    weights = game.block_weights(train)
    beta = game.fit_logistic_weighted(
        X_train, y_train, weights, l2=l2
    )
    return game.predict(beta, X_test)


def inner_choice(train, groups):
    blocks = ordered_blocks(train)
    if len(blocks) < 20:
        rich = [f for feats in groups.values() for f in feats]
        return "RICH_ONLY", list(dict.fromkeys(rich)), 5.0, {
            "status": "SMALL_INNER_BLOCK_SAMPLE",
            "inner_blocks": len(blocks),
        }

    split = max(14, int(math.floor(len(blocks) * 0.72)))
    if len(blocks) - split < 5:
        split = max(10, len(blocks) - 5)
    tr_blocks = set(blocks[:split])
    val_blocks = set(blocks[split:])
    tr = train[train["block_key"].astype(str).isin(tr_blocks)].copy()
    val = train[train["block_key"].astype(str).isin(val_blocks)].copy()
    if tr.empty or val.empty or len(set(tr["outcome"].astype(int))) < 2:
        rich = [f for feats in groups.values() for f in feats]
        return "RICH_ONLY", list(dict.fromkeys(rich)), 5.0, {
            "status": "INNER_SPLIT_UNUSABLE",
            "inner_blocks": len(blocks),
        }

    specs = candidate_specs(groups)
    scored = []
    y_val = val["outcome"].astype(int).to_numpy()
    for label, features, l2 in specs:
        try:
            pred = fit_predict(tr, val, features, l2)
            metrics = evaluate(y_val, pred)
            scored.append((label, features, l2, metrics))
        except Exception:
            continue

    if not scored:
        rich = [f for feats in groups.values() for f in feats]
        return "RICH_ONLY", list(dict.fromkeys(rich)), 5.0, {
            "status": "NO_INNER_CANDIDATES",
            "inner_blocks": len(blocks),
        }

    scored.sort(
        key=lambda x: (
            x[3]["brier"] if x[3]["brier"] is not None else 999,
            x[3]["log_loss"] if x[3]["log_loss"] is not None else 999,
            len(x[1]),
        )
    )
    best = scored[0]
    return best[0], best[1], best[2], {
        "status": "CHOSEN_INNER_TRAINING_ONLY",
        "inner_blocks": len(blocks),
        "inner_train_blocks": len(tr_blocks),
        "inner_validation_blocks": len(val_blocks),
        "candidate_count": len(scored),
        "best_metrics": best[3],
    }


def baseline_predictions(train, test):
    y_train = train["outcome"].astype(int).to_numpy()
    weights = game.block_weights(train)

    p_train = pd.to_numeric(
        train["market_reference_probability"], errors="coerce"
    ).fillna(0.5).clip(0.005, 0.995)
    p_test = pd.to_numeric(
        test["market_reference_probability"], errors="coerce"
    ).fillna(0.5).clip(0.005, 0.995)
    market_logit_train = np.log(p_train / (1 - p_train)).to_numpy()
    market_logit_test = np.log(p_test / (1 - p_test)).to_numpy()

    score_train = pd.to_numeric(train["old_score"], errors="coerce")
    med = float(score_train.median()) if score_train.notna().any() else 80.0
    score_train = score_train.fillna(med)
    score_test = pd.to_numeric(test["old_score"], errors="coerce").fillna(med)
    mean = float(score_train.mean())
    std = float(score_train.std(ddof=0))
    if not math.isfinite(std) or std < 1e-8:
        std = 1.0

    X_cal_train = np.column_stack([
        np.ones(len(train)), market_logit_train
    ])
    X_cal_test = np.column_stack([
        np.ones(len(test)), market_logit_test
    ])
    X_core_train = np.column_stack([
        np.ones(len(train)),
        market_logit_train,
        ((score_train - mean) / std).to_numpy(),
    ])
    X_core_test = np.column_stack([
        np.ones(len(test)),
        market_logit_test,
        ((score_test - mean) / std).to_numpy(),
    ])

    beta_cal = game.fit_logistic_weighted(
        X_cal_train, y_train, weights, l2=2.0
    )
    beta_core = game.fit_logistic_weighted(
        X_core_train, y_train, weights, l2=3.0
    )
    return (
        game.predict(beta_cal, X_cal_test),
        game.predict(beta_core, X_core_test),
    )


def nested_lane(frame, lane_key):
    n = len(frame)
    blocks = ordered_blocks(frame) if not frame.empty else []
    if n < 50 or len(blocks) < 40:
        return {
            "status": "INSUFFICIENT_INDEPENDENT_GAMES",
            "history_n": n,
            "independent_blocks": len(blocks),
            "minimum_rows": 50,
            "minimum_independent_blocks": 40,
        }

    groups, feature_stats = available_features(frame, lane_key)
    if not groups:
        return {
            "status": "NO_RICH_FEATURES_WITH_SUFFICIENT_COVERAGE",
            "history_n": n,
            "independent_blocks": len(blocks),
            "feature_coverage": feature_stats,
        }

    min_train_blocks = max(26, int(math.floor(len(blocks) * 0.50)))
    step_blocks = max(5, int(math.ceil(len(blocks) * 0.10)))
    records = []
    choices = []

    for start in range(min_train_blocks, len(blocks), step_blocks):
        end = min(len(blocks), start + step_blocks)
        train_blocks = set(blocks[:start])
        test_blocks = set(blocks[start:end])
        train = frame[
            frame["block_key"].astype(str).isin(train_blocks)
        ].copy()
        test = frame[
            frame["block_key"].astype(str).isin(test_blocks)
        ].copy()
        if train.empty or test.empty or len(set(train["outcome"].astype(int))) < 2:
            continue

        label, features, l2, inner_meta = inner_choice(train, groups)
        try:
            challenger = fit_predict(train, test, features, l2)
            calibrated, current_core = baseline_predictions(train, test)
        except Exception:
            continue

        records.append({
            "y": test["outcome"].astype(int).to_numpy(),
            "blocks": test["block_key"].astype(str).to_numpy(),
            "market_raw": test["market_raw_probability"].astype(float).to_numpy(),
            "market_reference": test["market_reference_probability"].astype(float).to_numpy(),
            "market_calibrated": calibrated,
            "current_core": current_core,
            "challenger": challenger,
        })
        choices.append({
            "outer_train_blocks": len(train_blocks),
            "outer_test_blocks": len(test_blocks),
            "label": label,
            "features": features,
            "l2": l2,
            "inner": inner_meta,
        })

    if not records:
        return {
            "status": "NO_OUTER_FOLDS",
            "history_n": n,
            "independent_blocks": len(blocks),
            "feature_groups": groups,
            "feature_coverage": feature_stats,
        }

    y = np.concatenate([r["y"] for r in records])
    test_blocks = np.concatenate([r["blocks"] for r in records])
    preds = {
        key: np.concatenate([r[key] for r in records])
        for key in [
            "market_raw",
            "market_reference",
            "market_calibrated",
            "current_core",
            "challenger",
        ]
    }
    metrics = {key: evaluate(y, pred) for key, pred in preds.items()}
    comparisons = {
        "challenger_vs_current_v2": base.paired_block_comparison(
            y, preds["challenger"], preds["current_core"], test_blocks, 4101
        ),
        "challenger_vs_market_reference": base.paired_block_comparison(
            y, preds["challenger"], preds["market_reference"], test_blocks, 4102
        ),
        "challenger_vs_calibrated_market": base.paired_block_comparison(
            y, preds["challenger"], preds["market_calibrated"], test_blocks, 4103
        ),
    }

    challenger = metrics["challenger"]
    current = metrics["current_core"]
    reference = metrics["market_reference"]
    calibrated = metrics["market_calibrated"]

    improves_current = (
        challenger["brier"] <= current["brier"] - 0.0005
        and challenger["log_loss"] <= current["log_loss"] - 0.0005
    )
    beats_reference = (
        challenger["brier"] <= reference["brier"] - 0.001
        and challenger["log_loss"] <= reference["log_loss"] - 0.001
    )
    beats_calibrated = (
        challenger["brier"] <= calibrated["brier"] - 0.0005
        and challenger["log_loss"] <= calibrated["log_loss"] - 0.0005
    )
    confidence_all = all(
        comparisons[name].get("confidence_supported") is True
        for name in [
            "challenger_vs_current_v2",
            "challenger_vs_market_reference",
            "challenger_vs_calibrated_market",
        ]
    )

    if improves_current and beats_reference and beats_calibrated and confidence_all:
        status = "CHALLENGER_REVIEW_CANDIDATE"
    elif improves_current and beats_reference and beats_calibrated:
        status = "PROMISING_NOT_PROVEN"
    elif improves_current:
        status = "IMPROVES_CURRENT_MODEL_BUT_NOT_MARKET"
    else:
        status = "KEEP_CURRENT_V2"

    span_days = round(
        (frame["_time"].max() - frame["_time"].min()).total_seconds() / 86400.0,
        2,
    )
    return {
        "status": status,
        "history_n": n,
        "independent_blocks": len(blocks),
        "history_span_days": span_days,
        "recency_decay_status": (
            "READY_TO_TEST" if span_days >= 30
            else "WAITING_FOR_LONGER_DECISION_HISTORY"
        ),
        "walk_forward_n": int(len(y)),
        "walk_forward_blocks": int(len(set(test_blocks.tolist()))),
        "outer_folds": len(records),
        "feature_groups": groups,
        "feature_coverage": feature_stats,
        "metrics": metrics,
        "comparisons": comparisons,
        "improves_current_v2": bool(improves_current),
        "beats_market_reference": bool(beats_reference),
        "beats_calibrated_market": bool(beats_calibrated),
        "confidence_supported_against_all": bool(confidence_all),
        "inner_choices": choices,
        "choice_counts": dict(Counter(x["label"] for x in choices)),
        "automatic_live_change": False,
    }


def main():
    lanes = {}
    for sport in game.SPORTS:
        for market in game.MARKETS:
            lane_key = f"{sport}_{market}"
            frame = enriched_history(sport, market)
            if lane_key not in LANE_FEATURES:
                lanes[lane_key] = {
                    "status": "RICH_CHALLENGER_NOT_YET_SUPPORTED",
                    "history_n": int(len(frame)),
                    "independent_blocks": (
                        int(frame["block_key"].nunique())
                        if not frame.empty else 0
                    ),
                }
                continue
            lanes[lane_key] = nested_lane(frame, lane_key)

    payload = {
        "status": "READY",
        "method": "NESTED_WHOLE_GAME_WALK_FORWARD_PREDECLARED_FEATURE_FAMILIES",
        "lanes": lanes,
        "rules": [
            "The fair/reference market logit is always the anchor.",
            "Only prediction-time payload features are eligible; no postgame or backfilled hindsight features are used.",
            "Outer train/test splits are by whole game, so alternate lines from one game never cross folds.",
            "Training weights give each game equal total influence even when a game has many alternate lines.",
            "Feature-family/L2 choices are made only inside the outer training window.",
            "The search space is limited to predeclared CFB feature families to reduce multiple-testing risk.",
            "A challenger must beat current V2, market reference, and calibrated market in mean Brier/log loss and paired game-block confidence before review.",
            "No challenger changes live recommendations automatically.",
        ],
    }
    for path in (OUT, PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    if DIST.exists():
        DIST.write_text(json.dumps(payload, indent=2))

    print(json.dumps({
        "status": payload["status"],
        "lanes": {
            k: {
                "status": v.get("status"),
                "history_n": v.get("history_n"),
                "independent_blocks": v.get("independent_blocks"),
                "walk_forward_n": v.get("walk_forward_n"),
                "walk_forward_blocks": v.get("walk_forward_blocks"),
                "choice_counts": v.get("choice_counts"),
                "metrics": v.get("metrics"),
                "comparisons": v.get("comparisons"),
            }
            for k, v in lanes.items()
            if v.get("history_n") or k.startswith("CFB_")
        },
    }, indent=2))


if __name__ == "__main__":
    main()
