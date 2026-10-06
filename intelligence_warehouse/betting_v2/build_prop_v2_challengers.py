#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT = OUT_DIR / "PROP_V2_CHALLENGERS.json"
PUBLIC = ROOT / "commercial_web" / "public" / "prop_v2_challengers.json"
DIST = ROOT / "commercial_web" / "dist" / "prop_v2_challengers.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_prop_v2 as prop

L2_VALUES = (2.0, 5.0, 10.0, 20.0)


def evaluate(y, p):
    return prop.evaluate(np.asarray(y, dtype=float), np.asarray(p, dtype=float))


def inner_choice(train, feature_names):
    n = len(train)
    split = max(20, int(math.floor(n * 0.75)))
    if n - split < 8:
        return feature_names, 5.0, "BASELINE_SMALL_INNER_SAMPLE"

    inner_train = train.iloc[:split]
    inner_val = train.iloc[split:]
    y_train = inner_train["outcome"].astype(int).to_numpy()
    y_val = inner_val["outcome"].astype(int).to_numpy()

    candidates = [(tuple(feature_names), 5.0, "FULL")]
    for name in feature_names:
        candidates.append((tuple(x for x in feature_names if x != name), 5.0, f"DROP:{name}"))
    for l2 in L2_VALUES:
        if l2 != 5.0:
            candidates.append((tuple(feature_names), l2, f"L2:{l2:g}"))

    scored = []
    for feats, l2, label in candidates:
        X_train = prop.matrix(inner_train, list(feats))
        X_val = prop.matrix(inner_val, list(feats))
        beta = prop.fit_logistic(X_train, y_train, l2=l2)
        pred = prop.predict(beta, X_val)
        m = evaluate(y_val, pred)
        scored.append((feats, l2, label, m))

    baseline = next(x for x in scored if x[2] == "FULL")
    bb = baseline[3]["brier"]
    bl = baseline[3]["log_loss"]
    eligible = [
        x for x in scored
        if x[3]["brier"] is not None
        and x[3]["log_loss"] is not None
        and x[3]["brier"] <= bb - 0.0005
        and x[3]["log_loss"] <= bl - 0.0005
    ]
    if not eligible:
        return list(baseline[0]), baseline[1], "FULL"

    eligible.sort(
        key=lambda x: (
            (bb - x[3]["brier"]) + 0.25 * (bl - x[3]["log_loss"]),
            -len(x[0]),
        ),
        reverse=True,
    )
    best = eligible[0]
    return list(best[0]), best[1], best[2]


def nested_lane(frame, cfg):
    n = len(frame)
    if n < 40:
        return {"status": "INSUFFICIENT_HISTORY", "history_n": n}

    min_train = max(30, int(math.floor(n * 0.50)))
    step = max(8, int(math.ceil(n * 0.10)))
    features = list(cfg["features"])
    records = []
    choices = []

    for test_start in range(min_train, n, step):
        test_end = min(n, test_start + step)
        train = frame.iloc[:test_start]
        test = frame.iloc[test_start:test_end]
        if test.empty:
            continue

        chosen_features, chosen_l2, label = inner_choice(train, features)
        choices.append({
            "outer_train_n": int(len(train)),
            "label": label,
            "l2": chosen_l2,
            "features": chosen_features,
        })

        y_train = train["outcome"].astype(int).to_numpy()
        y_test = test["outcome"].astype(int).to_numpy()

        X_base_train = prop.matrix(train, features)
        X_base_test = prop.matrix(test, features)
        beta_base = prop.fit_logistic(X_base_train, y_train, l2=5.0)

        X_ch_train = prop.matrix(train, chosen_features)
        X_ch_test = prop.matrix(test, chosen_features)
        beta_ch = prop.fit_logistic(X_ch_train, y_train, l2=chosen_l2)

        X_cal_train = prop.matrix(train, [])
        X_cal_test = prop.matrix(test, [])
        beta_cal = prop.fit_logistic(X_cal_train, y_train, l2=3.0)

        records.append({
            "y": y_test,
            "blocks": test["block_key"].astype(str).to_numpy(),
            "market_raw": test["market_raw_probability"].astype(float).to_numpy(),
            "market_reference": test["market_probability"].astype(float).to_numpy(),
            "market_calibrated": prop.predict(beta_cal, X_cal_test),
            "current_core": prop.predict(beta_base, X_base_test),
            "challenger": prop.predict(beta_ch, X_ch_test),
        })

    if not records:
        return {"status": "NO_FOLDS", "history_n": n}

    y = np.concatenate([r["y"] for r in records])
    blocks = np.concatenate([r["blocks"] for r in records])
    preds = {
        key: np.concatenate([r[key] for r in records])
        for key in ["market_raw", "market_reference", "market_calibrated", "current_core", "challenger"]
    }
    metrics = {key: evaluate(y, p) for key, p in preds.items()}
    comparisons = {
        "challenger_vs_current_core": prop.paired_block_comparison(y, preds["challenger"], preds["current_core"], blocks, 2201),
        "challenger_vs_reference": prop.paired_block_comparison(y, preds["challenger"], preds["market_reference"], blocks, 2202),
        "challenger_vs_calibrated": prop.paired_block_comparison(y, preds["challenger"], preds["market_calibrated"], blocks, 2203),
    }

    current = metrics["current_core"]
    challenger = metrics["challenger"]
    mean_improvement = bool(
        challenger["brier"] <= current["brier"] - 0.0005
        and challenger["log_loss"] <= current["log_loss"] - 0.0005
    )
    confidence = comparisons["challenger_vs_current_core"]["confidence_supported"]
    beats_reference = (
        challenger["brier"] <= metrics["market_reference"]["brier"] - 0.001
        and challenger["log_loss"] <= metrics["market_reference"]["log_loss"] - 0.001
    )
    beats_calibrated = (
        challenger["brier"] <= metrics["market_calibrated"]["brier"] - 0.0005
        and challenger["log_loss"] <= metrics["market_calibrated"]["log_loss"] - 0.0005
    )

    labels = Counter(x["label"] for x in choices)
    if mean_improvement and confidence and beats_reference and beats_calibrated:
        status = "CHALLENGER_REVIEW_CANDIDATE"
    elif mean_improvement and beats_reference and beats_calibrated:
        status = "PROMISING_NOT_PROVEN"
    elif mean_improvement:
        status = "IMPROVES_FEATURE_MODEL_BUT_STILL_LOSES_TO_MARKET"
    else:
        status = "KEEP_CURRENT_V2"

    time_min = frame["time"].min()
    time_max = frame["time"].max()
    span_days = (
        None if time_min is None or time_max is None
        else round((time_max - time_min).total_seconds() / 86400.0, 2)
    )
    recency_status = (
        "READY_TO_TEST"
        if span_days is not None and span_days >= 30
        else "WAITING_FOR_LONGER_DECISION_HISTORY"
    )

    return {
        "status": status,
        "history_n": n,
        "history_span_days": span_days,
        "recency_decay_status": recency_status,
        "walk_forward_n": int(len(y)),
        "outer_folds": len(records),
        "metrics": metrics,
        "comparisons": comparisons,
        "mean_improvement_vs_current": mean_improvement,
        "confidence_supported_vs_current": bool(confidence),
        "beats_market_reference": bool(beats_reference),
        "beats_calibrated_market": bool(beats_calibrated),
        "inner_choices": choices,
        "choice_counts": dict(labels),
        "automatic_live_change": False,
    }


def main():
    lanes = {}
    for lane_key, cfg in prop.LANES.items():
        frame = prop.build_history(cfg)
        lanes[lane_key] = nested_lane(frame, cfg)

    payload = {
        "status": "READY",
        "method": "NESTED_WALK_FORWARD_TRAINING_ONLY_FEATURE_ABLATION_AND_L2_SELECTION",
        "lanes": lanes,
        "rules": [
            "Feature or regularization choices are made only inside each outer training fold.",
            "The outer test fold is never used to choose challenger features or L2 strength.",
            "At most one feature is removed per inner selection step, preventing aggressive search on small samples.",
            "No challenger changes the live model automatically.",
            "A challenger must beat current V2, the market reference, and calibrated market out of sample before review.",
        ],
    }
    for path in (OUT, PUBLIC):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    if DIST.exists():
        DIST.write_text(json.dumps(payload, indent=2))

    print(json.dumps({
        "status": "READY",
        "lanes": {
            k: {
                "status": v.get("status"),
                "history_n": v.get("history_n"),
                "walk_forward_n": v.get("walk_forward_n"),
                "choice_counts": v.get("choice_counts", {}),
                "metrics": v.get("metrics", {}),
                "vs_current": v.get("comparisons", {}).get("challenger_vs_current_core", {}),
            }
            for k, v in lanes.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
