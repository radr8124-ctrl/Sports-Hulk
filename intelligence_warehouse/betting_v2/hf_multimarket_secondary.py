"""Frozen HF MLB 4-market study: June-fitted models vs already-seen July grades.

Independent-source research only. No production bet/pick/model/ledger writes.
The July grades were inspected in older research: never call this a fresh
prospective holdout or optimize a hyperparameter with its outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from .hf_mlb_prop_asof import _fit_small_ridge_logistic, _logit, _sigmoid

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "reports/HF_ZENITH_MULTI_MARKET_SECONDARY_JULY_PREREG_2026-10-09.json"
OUT = ROOT / "reports/hf_mlb_multimarket_secondary_20261009"
TRAIN_LAST_EXCLUSIVE = datetime.fromisoformat("2026-06-19T00:00:00+00:00")
JULY_START = datetime.fromisoformat("2026-07-01T00:00:00+00:00")
JULY_END_EXCLUSIVE = datetime.fromisoformat("2026-07-06T00:00:00+00:00")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("TIMESTAMP_MISSING")
    x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if x.tzinfo is None:
        # The source's assumed UTC is allowed only because the original
        # official-audit row already established the <=3-minute official match.
        x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc)


def eligible(row: dict, mode: str) -> bool:
    if row.get("status") != ("VERIFIED_HISTORICAL" if mode == "train" else "OFFICIAL_DERIVED_HISTORICAL"):
        return False
    if row.get("pair_status") != "VERIFIED_SAME_BOOK_TIME_PAIR":
        return False
    if row.get("asof_status") != "PREGAME_FEATURE_VERIFIED":
        return False
    if row.get("feature_rule") != "STRICTLY_PRIOR_COMPLETED_DATE_ONLY;TARGET_AND_LATER_GAMES_EXCLUDED":
        return False
    if not isinstance(row.get("verified_win"), bool) or row.get("official_game_pk") is None:
        return False
    if not isinstance(row.get("official_player_id"), int):
        return False
    if str(row.get("side") or "").lower() not in ("over", "under"):
        return False
    if not row.get("game_id") or not row.get("book") or not row.get("market"):
        return False
    try:
        game = stamp(row["official_start"])
        quote = stamp(row["ts"])
        latest_prior = datetime.fromisoformat(str(row["prior_latest_date"])).date()
        prob = float(row["market_fair_probability"])
        trend = float(row["pregame_context_signal"])
        odds = float(row["odds"])
        line = float(row["line"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return False
    if not (0.001 < prob < 0.999 and 1.000001 < odds <= 1000 and math.isfinite(odds) and
            math.isfinite(trend) and math.isfinite(line) and line >= 0):
        return False
    if not (quote < game and latest_prior < quote.date()):
        return False
    if mode == "train" and not (game < TRAIN_LAST_EXCLUSIVE):
        return False
    if mode == "test" and not (JULY_START <= game < JULY_END_EXCLUSIVE):
        return False
    return True


def one_game_rows(rows: list[dict], market: str, mode: str) -> list[dict]:
    seen: dict[int, dict] = {}
    for row in rows:
        if row.get("market") != market or not eligible(row, mode):
            continue
        pk = int(row["official_game_pk"])
        if pk in seen:
            raise ValueError(f"DUPLICATE_OFFICIAL_GAME_{mode}: {market}, {pk}")
        seen[pk] = row
    return sorted(seen.values(), key=lambda r: (stamp(r["official_start"]), int(r["official_game_pk"])))


def features(rows: list[dict], trend: bool) -> np.ndarray:
    p = np.array([float(r["market_fair_probability"]) for r in rows], dtype=float)
    cols = [np.ones(len(rows)), _logit(p)]
    if trend:
        cols.append(np.array([min(4.0, max(-4.0, float(r["pregame_context_signal"]))) for r in rows]))
    return np.column_stack(cols)


def scores(y: np.ndarray, p: np.ndarray) -> dict:
    q = np.clip(p, 1e-6, 1 - 1e-6)
    return {
        "brier": round(float(np.mean((q-y)**2)), 6),
        "log_loss": round(float(np.mean(-(y*np.log(q) + (1-y)*np.log(1-q)))), 6),
    }


def uncertainty(rows: list[dict], gains: np.ndarray, reps: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = len(gains)
    draws = rng.integers(0, n, size=(reps, n))
    game = np.quantile(gains[draws].mean(axis=1), [0.025, 0.975])
    dates = [stamp(r["official_start"]).date().isoformat() for r in rows]
    groups = defaultdict(list)
    for i, day in enumerate(dates):
        groups[day].append(i)
    days = sorted(groups)
    day_means = []
    for _ in range(reps):
        sample_days = rng.integers(0, len(days), size=len(days))
        indices = [i for di in sample_days for i in groups[days[int(di)]]]
        day_means.append(float(gains[indices].mean()))
    day_ci = np.quantile(day_means, [0.025, 0.975])
    return {
        "independent_game_blocks": n,
        "calendar_day_blocks": len(days),
        "brier_gain_market_minus_trend": round(float(gains.mean()), 6),
        "game_bootstrap95_ci": [round(float(z), 6) for z in game],
        "day_cluster_bootstrap95_ci": [round(float(z), 6) for z in day_ci],
        "confidence_supported": bool(game[0] > 0 and day_ci[0] > 0 and len(days) >= 30),
    }


def selected(rows: list[dict], p: np.ndarray, *, min_prob: float, min_ev: float) -> dict:
    picks = []
    for r, pred in zip(rows, p):
        odds = float(r["odds"])
        if float(pred) < min_prob or float(pred)*odds-1 < min_ev:
            continue
        win = bool(r["verified_win"])
        picks.append((r, odds - 1 if win else -1.0, win))
    count = len(picks)
    return {
        "count": count,
        "coverage_pct": round(100*count/len(rows), 2),
        "distinct_official_games": len({int(r["official_game_pk"]) for r, _, _ in picks}),
        "wins": sum(w for _, _, w in picks),
        "losses": sum(not w for _, _, w in picks),
        "hit_rate_pct": round(100*sum(w for _, _, w in picks)/count, 2) if count else None,
        "paper_units": round(sum(u for _, u, _ in picks), 4),
        "paper_roi_pct": round(100*sum(u for _, u, _ in picks)/count, 2) if count else None,
        "price_caution": "Historical quoted lines, not independently proven executable bets or paid PrizePicks payouts",
    }


def verify_spec(spec: dict) -> dict:
    if spec.get("trial_class") != "RETROSPECTIVE_SECONDARY_HISTORICAL_NOT_UNSEEN":
        raise ValueError("NOT_RETROSPECTIVE_SPEC")
    if spec.get("ridge_lambda") != 16.0:
        raise ValueError("CHANGED_PREREG_HYPERPARAMETERS")
    if spec.get("model_promotion_allowed") is not False or spec.get("no_writes_to_live_predictions") is not True:
        raise ValueError("LIVE_MODEL_PROMOTION_NOT_PERMITTED")
    files = {}
    for k, val in spec["input_paths"].items():
        p = ROOT / val
        digest = sha(p)
        if digest != spec["frozen_inputs_sha256"][k]:
            raise ValueError(f"FROZEN_INPUT_FILE_CHANGED:{k}")
        files[k] = p
    return files


def evaluate(spec: dict, training: list[dict], july: list[dict]) -> tuple[dict,list[dict]]:
    predictions = []
    result = {}
    seed = spec["evaluation"]["bootstrap_seed"]
    reps = spec["evaluation"]["bootstrap_repetitions"]
    min_prob = spec["evaluation"]["selection_test"]
    if min_prob != ">=70pct probability AND >=3pct paper expected value at recorded decimal odds; no in-test threshold adjustment":
        raise ValueError("PRESPECIFIED_SELECTION_FILTER_CHANGED")
    for j, market in enumerate(spec["fixed_markets"]):
        a = one_game_rows(training, market, "train")
        b = one_game_rows(july, market, "test")
        if not a or len(b) < spec["evaluation"]["min_samples_per_market_for_comparison"]:
            result[market] = {"status": "INSUFFICIENT_GAME_SAMPLE", "train_games":len(a), "test_games":len(b)}
            continue
        if set(int(r["official_game_pk"]) for r in a) & set(int(r["official_game_pk"]) for r in b):
            raise ValueError("TRAIN_TEST_OFFICIAL_GAMES_OVERLAP")
        if max(stamp(r["official_start"]) for r in a) >= min(stamp(r["official_start"]) for r in b):
            raise ValueError("TIME_LEAKAGE_TRAIN_TEST")
        ytrain = np.asarray([int(r["verified_win"]) for r in a],dtype=float)
        ytest = np.asarray([int(r["verified_win"]) for r in b],dtype=float)
        p_raw = np.asarray([float(r["market_fair_probability"]) for r in b])
        beta_m = _fit_small_ridge_logistic(features(a,False), ytrain, regularization=16.0)
        beta_t = _fit_small_ridge_logistic(features(a,True), ytrain, regularization=16.0)
        p_m = _sigmoid(features(b,False) @ beta_m)
        p_t = _sigmoid(features(b,True) @ beta_t)
        uncertainty_data = uncertainty(b, (p_m-ytest)**2-(p_t-ytest)**2, reps, seed+j)
        result[market] = {
            "status":"SECONDARY_HISTORICAL_COMPARISON_COMPLETE_NOT_FUTURE_PROOF",
            "train_independent_games":len(a), "test_independent_games":len(b),
            "train_last_start":max(r["official_start"] for r in a),
            "test_first_start":min(r["official_start"] for r in b),
            "test_last_start":max(r["official_start"] for r in b),
            "train_game_id_manifest_sha256":hashlib.sha256(
                json.dumps([int(r["official_game_pk"]) for r in a],sort_keys=True).encode()).hexdigest(),
            "market_only_beta":[round(float(v),10) for v in beta_m],
            "market_plus_last5_beta":[round(float(v),10) for v in beta_t],
            "fair_book_market":scores(ytest,p_raw),
            "frozen_calibrated_market":scores(ytest,p_m),
            "frozen_market_plus_prior_player_stat":scores(ytest,p_t),
            "comparisons":uncertainty_data,
            "raw_market_selected":selected(b,p_raw,min_prob=0.7,min_ev=0.03),
            "calibrated_market_selected":selected(b,p_m,min_prob=0.7,min_ev=0.03),
            "market_plus_player_selected":selected(b,p_t,min_prob=0.7,min_ev=0.03),
            "official_grades_source":"OFFICIAL_DERIVED_HISTORICAL, NOT PLATFORM_SETTLEMENT",
            "production_model_approved":False,
        }
        for r,market_p,cal_p,model_p in zip(b,p_raw,p_m,p_t):
            predictions.append({
                "market":market,"official_game_pk":int(r["official_game_pk"]),
                "game_start":r["official_start"],"quote_ts":r["ts"],
                "book":r["book"],"side":r["side"],"line":r["line"],
                "decimal_odds":r["odds"],"official_derived_win":r["verified_win"],
                "fair_market_probability":round(float(market_p),9),
                "market_calibration_prediction":round(float(cal_p),9),
                "prior_player_challenger_prediction":round(float(model_p),9),
                "paper_only":True,
            })
    return result,predictions


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--output-dir",type=Path,default=OUT)
    args=ap.parse_args()
    if not (ROOT/"reports") in args.output_dir.resolve().parents:
        raise SystemExit("RESEARCH_OUTPUT_MUST_BE_UNDER_REPORTS")
    if any(part in args.output_dir.parts for part in ("live","decision","commercial_web","public","latest")):
        raise SystemExit("RESEARCH_OUTPUT_MUST_NOT_BE_LIVE")
    spec_sha=sha(SPEC)
    spec=json.loads(SPEC.read_text())
    paths=verify_spec(spec)
    train=json.loads(paths["historical_june_train"].read_text())
    july=json.loads(paths["historical_july_test"].read_text())
    results, predictions=evaluate(spec,train,july)
    if sha(SPEC)!=spec_sha:
        raise RuntimeError("CHANGED_PREREG_DURING_EVALUATION")
    summary={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "study_id":spec["study_id"],
        "preregistration_sha256":spec_sha,
        "status":"RESEARCH_ONLY_ALREADY_SEEN_JULY_NO_PRODUCTION_PROMOTION",
        "model_comparison":results,
        "holdout_prediction_rows":len(predictions),
        "fresh_future_games_evaluated":0,
        "new_cloud_hf_compute_spend":False,
        "live_models_picks_ledgers_changed":False,
        "source_license_cleared_for_commercial_use":False,
    }
    args.output_dir.mkdir(parents=True,exist_ok=True)
    # Exclusive create keeps the original frozen evaluation intact.
    files={"secondary_comparison_summary.json":summary, "historical_predictions_PRIVATE.json":predictions}
    for name,payload in files.items():
        p=args.output_dir/name
        with p.open("x") as handle:
            handle.write(json.dumps(payload,indent=2,sort_keys=True,default=str)+"\n")
            handle.flush();os.fsync(handle.fileno())
    print(json.dumps(summary,sort_keys=True,indent=2))


if __name__=="__main__":
    main()
