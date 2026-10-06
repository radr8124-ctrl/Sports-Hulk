#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

MODEL_OUT = OUT_DIR / "BETTING_V2_MODEL.json"
CURRENT_OUT = OUT_DIR / "BETTING_V2_CURRENT.json"
VALIDATION_OUT = OUT_DIR / "BETTING_V2_VALIDATION.json"
GAME_DEVIG_OUT = OUT_DIR / "BETTING_V2_GAME_DEVIG.json"
MODEL_VERSION = "BETTING_V2_FAIR_MARKET_CONFIDENCE_2026_10_05"
_GAME_DEVIG_CACHE = None

SPORTS = ["NFL", "CFB", "CBB", "MLB", "NBA", "NHL"]
QUALIFIED = {"QUALIFIED_RESEARCH"}

HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" / f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}
CURRENT_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / f"{sport}_GAME_DECISIONS.csv"
    for sport in SPORTS
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value).strip()


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def parse_json(value):
    try:
        return json.loads(value) if value else {}
    except Exception:
        return {}


def parse_dt(value):
    try:
        d = pd.to_datetime(value, errors="coerce", utc=True)
        return None if pd.isna(d) else d
    except Exception:
        return None


def game_devig_data():
    global _GAME_DEVIG_CACHE
    if _GAME_DEVIG_CACHE is None:
        try:
            _GAME_DEVIG_CACHE = json.loads(GAME_DEVIG_OUT.read_text())
        except Exception:
            _GAME_DEVIG_CACHE = {
                "history": {},
                "current": {},
                "coverage": {},
                "minimum_paired_books_for_model": 2,
            }
    return _GAME_DEVIG_CACHE


def history_recommendation_key(sport, row):
    key = clean(row.get("recommendation_key"))
    if key:
        return key
    return "|".join([
        sport,
        clean(row.get("snapshot_at")),
        clean(row.get("game_key")),
        clean(row.get("selection")),
    ])


def historical_fair_probability(sport, row):
    key = history_recommendation_key(sport, row)
    record = (
        game_devig_data().get("history", {})
        .get(sport, {})
        .get(key, {})
    )
    p = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    minimum = int(num(game_devig_data().get("minimum_paired_books_for_model")) or 2)
    if p is None or not (0 < p < 1) or books < minimum:
        return None, books
    return p, books


def current_fair_probability(sport, game_key, side):
    key = f"{clean(game_key)}|{clean(side).upper()}"
    record = (
        game_devig_data().get("current", {})
        .get(sport, {})
        .get(key, {})
    )
    p = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    minimum = int(num(game_devig_data().get("minimum_paired_books_for_model")) or 2)
    if p is None or not (0 < p < 1) or books < minimum:
        return None, books
    return p, books


def american_implied(odds):
    odds = num(odds)
    if odds is None or odds == 0:
        return None
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def american_profit(odds):
    odds = num(odds)
    if odds is None or odds == 0:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def logit(p):
    p = min(0.995, max(0.005, float(p)))
    return math.log(p / (1.0 - p))


def sigmoid_array(z):
    z = np.clip(z, -35, 35)
    return 1.0 / (1.0 + np.exp(-z))


def fit_logistic(X, y, l2=1.0, max_iter=100):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    if X.ndim != 2 or len(X) == 0:
        raise ValueError("No calibration rows.")

    beta = np.zeros(X.shape[1], dtype=float)
    mean_y = float(np.mean(y))
    mean_y = min(0.99, max(0.01, mean_y))
    beta[0] = math.log(mean_y / (1 - mean_y))

    penalty = np.eye(X.shape[1], dtype=float)
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        p = sigmoid_array(X @ beta)
        w = np.clip(p * (1 - p), 1e-6, None)
        grad = X.T @ (p - y) + l2 * (penalty @ beta)
        hess = X.T @ (X * w[:, None]) + l2 * penalty
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hess) @ grad
        beta_new = beta - step
        if np.max(np.abs(beta_new - beta)) < 1e-8:
            beta = beta_new
            break
        beta = beta_new
    return beta


def predict(beta, X):
    return sigmoid_array(np.asarray(X, dtype=float) @ np.asarray(beta, dtype=float))


def brier(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2)) if len(y) else None


def log_loss(y, p):
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))) if len(y) else None


def ece(y, p, bins=5):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    if not len(y):
        return None
    cuts = np.linspace(0, 1, bins + 1)
    total = 0.0
    for i in range(bins):
        if i == bins - 1:
            mask = (p >= cuts[i]) & (p <= cuts[i + 1])
        else:
            mask = (p >= cuts[i]) & (p < cuts[i + 1])
        n = int(mask.sum())
        if not n:
            continue
        total += (n / len(y)) * abs(float(p[mask].mean()) - float(y[mask].mean()))
    return float(total)


def extract_price(row):
    market = clean(row.get("market")).upper()
    line = num(row.get("line"))
    if market == "MONEYLINE" and line is not None and abs(line) >= 100:
        return line

    payload = parse_json(row.get("payload_json"))
    for key in [
        "median_price_american", "price_median", "american_odds",
        "sportsbook_price", "line",
    ]:
        value = num(payload.get(key))
        if value is not None and abs(value) >= 100:
            return value
    return None


def extract_start(row):
    for key in ["start", "start_dt"]:
        value = row.get(key)
        dt = parse_dt(value)
        if dt is not None:
            return dt
    payload = parse_json(row.get("payload_json"))
    for key in ["start", "start_dt", "start_sportsbook", "start_dfs"]:
        dt = parse_dt(payload.get(key))
        if dt is not None:
            return dt
    return None


def build_history():
    rows = []
    for sport, path in HISTORY_FILES.items():
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False)
        if frame.empty:
            continue

        if "lane" in frame.columns:
            frame = frame[frame["lane"].astype(str).str.upper().eq("GAME")].copy()
        if "market" not in frame.columns:
            continue
        frame = frame[frame["market"].astype(str).str.upper().eq("MONEYLINE")].copy()
        if "grade" not in frame.columns:
            continue
        frame["grade"] = frame["grade"].astype(str).str.upper()
        frame = frame[frame["grade"].isin(["WIN", "LOSS"])].copy()
        if "decision" in frame.columns:
            frame["decision"] = frame["decision"].astype(str).str.upper()

        if frame.empty:
            continue

        if "snapshot_at" in frame.columns:
            frame["_snapshot"] = pd.to_datetime(frame["snapshot_at"], errors="coerce", utc=True)
        else:
            frame["_snapshot"] = pd.NaT

        normalized = []
        for _, row in frame.iterrows():
            score = num(row.get("score"))
            price = extract_price(row)
            start = extract_start(row)
            snapshot = row.get("_snapshot")
            if score is None or price is None:
                continue
            if start is not None and pd.notna(snapshot) and snapshot >= start:
                # Never train on a recommendation first recorded after event start.
                continue
            raw_p = american_implied(price)
            if raw_p is None:
                continue
            fair_p, fair_books = historical_fair_probability(sport, row)
            reference_p = fair_p if fair_p is not None else raw_p
            game_key = clean(row.get("game_key") or row.get("event_id"))
            normalized.append({
                "sport": sport,
                "game_key": game_key,
                "selection": clean(row.get("selection")),
                "decision": clean(row.get("decision")).upper(),
                "recommendation_key": history_recommendation_key(sport, row),
                "score": score,
                "american_odds": price,
                "market_implied_probability": raw_p,
                "market_reference_probability": reference_p,
                "market_reference_type": "DEVIG_FAIR" if fair_p is not None else "RAW_FALLBACK",
                "devig_paired_books": fair_books,
                "outcome": 1 if clean(row.get("grade")).upper() == "WIN" else 0,
                "snapshot_at": snapshot,
                "event_start": start,
                "block_key": f"{sport}|{game_key}",
            })

        if not normalized:
            continue

        d = pd.DataFrame(normalized)
        d["_order"] = d["snapshot_at"]
        d["_order"] = d["_order"].fillna(d["event_start"])
        d["_order"] = d["_order"].fillna(pd.Timestamp("1970-01-01", tz="UTC"))

        # Freeze the first qualified snapshot for each event/selection.
        d = d.sort_values("_order").drop_duplicates(
            ["sport", "game_key", "selection"], keep="first"
        )
        rows.extend(d.to_dict("records"))

    if not rows:
        return pd.DataFrame()

    data = pd.DataFrame(rows)
    data["market_implied_probability"] = pd.to_numeric(
        data["market_implied_probability"], errors="coerce"
    )
    data["market_reference_probability"] = pd.to_numeric(
        data["market_reference_probability"], errors="coerce"
    )
    data = data[
        data["market_implied_probability"].notna()
        & data["market_reference_probability"].notna()
    ].copy()
    data["_time"] = pd.to_datetime(data["_order"], errors="coerce", utc=True)
    return data.sort_values("_time").reset_index(drop=True)


def official_best_bet_history_counts():
    counts = {}
    for sport, path in HISTORY_FILES.items():
        count = 0
        if path.exists():
            frame = pd.read_csv(path, low_memory=False)
            if (
                not frame.empty
                and "lane" in frame.columns
                and "market" in frame.columns
                and "grade" in frame.columns
            ):
                frame = frame[
                    frame["lane"].astype(str).str.upper().eq("GAME")
                    & frame["market"].astype(str).str.upper().eq("MONEYLINE")
                    & frame["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
                ].copy()
                if "decision" in frame.columns:
                    frame = frame[
                        frame["decision"].astype(str).str.upper().isin(QUALIFIED)
                    ].copy()

                rows = []
                if "snapshot_at" in frame.columns:
                    frame["_snapshot"] = pd.to_datetime(
                        frame["snapshot_at"], errors="coerce", utc=True
                    )
                else:
                    frame["_snapshot"] = pd.NaT
                for _, row in frame.iterrows():
                    if num(row.get("score")) is None or extract_price(row) is None:
                        continue
                    start = extract_start(row)
                    snap = row.get("_snapshot")
                    if start is not None and pd.notna(snap) and snap >= start:
                        continue
                    rows.append({
                        "game_key": clean(row.get("game_key") or row.get("event_id")),
                        "selection": clean(row.get("selection")),
                        "_order": (
                            snap if pd.notna(snap)
                            else start
                            if start is not None
                            else pd.Timestamp("1970-01-01", tz="UTC")
                        ),
                    })
                if rows:
                    x = pd.DataFrame(rows).sort_values("_order").drop_duplicates(
                        ["game_key", "selection"], keep="first"
                    )
                    count = int(len(x))
        counts[sport] = count
    return counts


def feature_matrices(frame):
    p_market = frame["market_reference_probability"].astype(float).clip(0.005, 0.995)
    mlogit = np.log(p_market / (1 - p_market))
    score_z = (frame["score"].astype(float) - 80.0) / 10.0

    market = np.column_stack([np.ones(len(frame)), mlogit])
    score = np.column_stack([np.ones(len(frame)), score_z])
    full = np.column_stack([np.ones(len(frame)), mlogit, score_z])
    return market, score, full


def evaluate_predictions(y, p):
    return {
        "n": int(len(y)),
        "brier": None if not len(y) else round(brier(y, p), 5),
        "log_loss": None if not len(y) else round(log_loss(y, p), 5),
        "ece": None if not len(y) else round(ece(y, p), 5),
        "mean_probability": None if not len(y) else round(float(np.mean(p)), 5),
        "observed_win_rate": None if not len(y) else round(float(np.mean(y)), 5),
    }


def paired_block_comparison(y, candidate, baseline, blocks, seed):
    y = np.asarray(y, dtype=float)
    candidate = np.clip(np.asarray(candidate, dtype=float), 1e-6, 1 - 1e-6)
    baseline = np.clip(np.asarray(baseline, dtype=float), 1e-6, 1 - 1e-6)
    blocks = np.asarray(blocks, dtype=object)

    brier_adv = (baseline - y) ** 2 - (candidate - y) ** 2
    base_ll = -(y * np.log(baseline) + (1 - y) * np.log(1 - baseline))
    cand_ll = -(y * np.log(candidate) + (1 - y) * np.log(1 - candidate))
    logloss_adv = base_ll - cand_ll

    groups = {}
    for idx, block in enumerate(blocks):
        groups.setdefault(str(block), []).append(idx)
    keys = list(groups)
    result = {
        "n": int(len(y)),
        "independent_blocks": len(keys),
        "brier_advantage": round(float(np.mean(brier_adv)), 5),
        "logloss_advantage": round(float(np.mean(logloss_adv)), 5),
        "brier_lcb90": None,
        "logloss_lcb90": None,
        "confidence_supported": False,
    }
    if len(keys) < 2:
        return result

    rng = np.random.default_rng(seed)
    boot_brier = []
    boot_logloss = []
    for _ in range(2000):
        sampled = rng.choice(keys, size=len(keys), replace=True)
        indexes = np.concatenate([np.asarray(groups[str(k)], dtype=int) for k in sampled])
        boot_brier.append(float(np.mean(brier_adv[indexes])))
        boot_logloss.append(float(np.mean(logloss_adv[indexes])))

    result["brier_lcb90"] = round(float(np.percentile(boot_brier, 5)), 5)
    result["logloss_lcb90"] = round(float(np.percentile(boot_logloss, 5)), 5)
    result["confidence_supported"] = bool(
        len(keys) >= 20
        and result["brier_lcb90"] > 0
        and result["logloss_lcb90"] > 0
    )
    return result


def walk_forward(data):
    n = len(data)
    blocks_n = int(data["block_key"].nunique()) if "block_key" in data.columns else n
    if n < 50 or blocks_n < 25:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "n": n,
            "independent_blocks": blocks_n,
            "minimum_required": 50,
            "minimum_independent_blocks": 25,
        }

    min_train = max(40, int(math.floor(n * 0.50)))
    step = max(10, int(math.ceil(n * 0.10)))
    records = []

    for test_start in range(min_train, n, step):
        test_end = min(n, test_start + step)
        train = data.iloc[:test_start].copy()
        test = data.iloc[test_start:test_end].copy()
        if test.empty:
            continue

        Xm_train, Xs_train, Xf_train = feature_matrices(train)
        Xm_test, Xs_test, Xf_test = feature_matrices(test)
        y_train = train["outcome"].astype(int).to_numpy()
        y_test = test["outcome"].astype(int).to_numpy()

        beta_m = fit_logistic(Xm_train, y_train, l2=1.5)
        beta_s = fit_logistic(Xs_train, y_train, l2=2.0)
        beta_f = fit_logistic(Xf_train, y_train, l2=2.0)

        records.append({
            "y": y_test,
            "block": test["block_key"].astype(str).to_numpy(),
            "market_raw": test["market_implied_probability"].astype(float).to_numpy(),
            "market_reference": test["market_reference_probability"].astype(float).to_numpy(),
            "market_calibrated": predict(beta_m, Xm_test),
            "score_only": predict(beta_s, Xs_test),
            "market_plus_hulk": predict(beta_f, Xf_test),
        })

    if not records:
        return {"status": "NO_FOLDS", "n": n, "independent_blocks": blocks_n}

    y = np.concatenate([r["y"] for r in records])
    blocks = np.concatenate([r["block"] for r in records])
    preds = {
        key: np.concatenate([r[key] for r in records])
        for key in [
            "market_raw", "market_reference", "market_calibrated",
            "score_only", "market_plus_hulk",
        ]
    }
    metrics = {key: evaluate_predictions(y, value) for key, value in preds.items()}

    comparisons = {
        "hulk_vs_reference": paired_block_comparison(
            y, preds["market_plus_hulk"], preds["market_reference"], blocks, 2101
        ),
        "hulk_vs_calibrated": paired_block_comparison(
            y, preds["market_plus_hulk"], preds["market_calibrated"], blocks, 2102
        ),
        "calibrated_vs_reference": paired_block_comparison(
            y, preds["market_calibrated"], preds["market_reference"], blocks, 2103
        ),
        "reference_vs_raw": paired_block_comparison(
            y, preds["market_reference"], preds["market_raw"], blocks, 2104
        ),
    }

    ref = metrics["market_reference"]
    cal = metrics["market_calibrated"]
    full = metrics["market_plus_hulk"]
    hulk_mean_beats_reference = (
        full["brier"] <= ref["brier"] - 0.001
        and full["log_loss"] <= ref["log_loss"] - 0.001
    )
    hulk_mean_beats_calibrated = (
        full["brier"] <= cal["brier"] - 0.0005
        and full["log_loss"] <= cal["log_loss"] - 0.0005
    )
    calibration_adds_value = (
        cal["brier"] <= ref["brier"] - 0.001
        and cal["log_loss"] <= ref["log_loss"] - 0.001
    )

    _, _, full_matrix = feature_matrices(data)
    beta_full = fit_logistic(full_matrix, data["outcome"].astype(int).to_numpy(), l2=2.0)
    old_score_coef = float(beta_full[-1])
    old_score_status = (
        "NEGATIVE_ORDERING_REJECTED"
        if old_score_coef < -0.02
        else "POSITIVE_INCREMENTAL_SIGNAL"
        if old_score_coef > 0.02 and hulk_mean_beats_reference and hulk_mean_beats_calibrated
        else "POSITIVE_BUT_NO_INCREMENTAL_VALUE"
        if old_score_coef > 0.02
        else "FLAT_OR_UNPROVEN"
    )

    hulk_mean_value = bool(
        hulk_mean_beats_reference
        and hulk_mean_beats_calibrated
        and old_score_status == "POSITIVE_INCREMENTAL_SIGNAL"
    )
    hulk_confidence = bool(
        hulk_mean_value
        and comparisons["hulk_vs_reference"]["confidence_supported"]
        and comparisons["hulk_vs_calibrated"]["confidence_supported"]
    )

    if hulk_mean_value:
        deployment_source = "MARKET_PLUS_HULK"
        historical_confidence = "SUPPORTED" if hulk_confidence else "PROMISING_BUT_UNCERTAIN"
        selection_status = (
            "FORWARD_VALIDATION_REQUIRED"
            if hulk_confidence
            else "HISTORICAL_SIGNAL_UNCERTAIN_RESEARCH_ONLY"
        )
    elif calibration_adds_value:
        deployment_source = "MARKET_CALIBRATED"
        historical_confidence = (
            "CALIBRATION_SUPPORTED"
            if comparisons["calibrated_vs_reference"]["confidence_supported"]
            else "CALIBRATION_MEAN_ONLY"
        )
        selection_status = "CALIBRATION_ONLY_NO_INDEPENDENT_EDGE"
    else:
        deployment_source = "MARKET_REFERENCE"
        historical_confidence = "NO_INDEPENDENT_EDGE"
        selection_status = "NO_INDEPENDENT_MODEL_EDGE"

    return {
        "status": "READY",
        "history_n": n,
        "independent_blocks": blocks_n,
        "walk_forward_n": int(len(y)),
        "folds": len(records),
        "metrics": metrics,
        "paired_comparisons": comparisons,
        "devig_history_n": int(data["market_reference_type"].eq("DEVIG_FAIR").sum()),
        "devig_history_pct": round(
            100.0 * float(data["market_reference_type"].eq("DEVIG_FAIR").mean()), 1
        ),
        "old_score_coefficient": round(old_score_coef, 5),
        "old_score_status": old_score_status,
        "hulk_score_adds_out_of_sample_value": hulk_mean_value,
        "hulk_score_confidence_supported": hulk_confidence,
        "market_recalibration_adds_out_of_sample_value": bool(calibration_adds_value),
        "historical_edge_confidence": historical_confidence,
        "selection_rule_status": selection_status,
        "deployment_probability_source": deployment_source,
    }


def fit_final_models(data, validation):
    Xm, Xs, Xf = feature_matrices(data)
    y = data["outcome"].astype(int).to_numpy()
    beta_m = fit_logistic(Xm, y, l2=1.5)
    beta_s = fit_logistic(Xs, y, l2=2.0)
    beta_f = fit_logistic(Xf, y, l2=2.0)

    return {
        "trained_at": now_iso(),
        "model_version": MODEL_VERSION,
        "history_n": int(len(data)),
        "sports": {
            sport: int((data["sport"] == sport).sum())
            for sport in SPORTS
        },
        "feature_spec": {
            "market_calibrated": ["intercept", "logit(market_reference_probability)"],
            "score_only": ["intercept", "(hulk_score-80)/10"],
            "market_plus_hulk": [
                "intercept",
                "logit(market_reference_probability)",
                "(hulk_score-80)/10",
            ],
        },
        "coefficients": {
            "market_calibrated": [round(float(x), 8) for x in beta_m],
            "score_only": [round(float(x), 8) for x in beta_s],
            "market_plus_hulk": [round(float(x), 8) for x in beta_f],
        },
        "deployment_probability_source": validation.get(
            "deployment_probability_source", "MARKET_CALIBRATED"
        ),
        "hulk_score_adds_out_of_sample_value": bool(
            validation.get("hulk_score_adds_out_of_sample_value", False)
        ),
        "hulk_score_confidence_supported": bool(
            validation.get("hulk_score_confidence_supported", False)
        ),
        "historical_edge_confidence": validation.get(
            "historical_edge_confidence", "WAITING"
        ),
        "selection_rule_status": validation.get(
            "selection_rule_status", "WAITING"
        ),
        "old_score_coefficient": validation.get("old_score_coefficient"),
        "old_score_status": validation.get("old_score_status", "WAITING"),
        "devig_history_n": validation.get("devig_history_n"),
        "devig_history_pct": validation.get("devig_history_pct"),
        "score_is_probability": False,
        "automatic_live_change": False,
    }


def current_schema(sport, frame):
    if sport == "NFL":
        return {
            "market": "market", "selection": "selection", "price": "line",
            "score": "hulk_market_score", "decision": "decision",
            "start": "start", "books": "sw_books",
            "away": None, "home": None, "side": None,
        }
    return {
        "market": "market_canonical", "selection": "selection_canonical",
        "price": "median_price_american", "score": "evidence_score",
        "decision": "decision", "start": "start_dt",
        "books": "sportsbook_count",
        "away": (
            "away_team" if "away_team" in frame.columns
            else "away_team_canonical" if "away_team_canonical" in frame.columns
            else None
        ),
        "home": (
            "home_team" if "home_team" in frame.columns
            else "home_team_canonical" if "home_team_canonical" in frame.columns
            else None
        ),
        "side": "selection_side" if "selection_side" in frame.columns else None,
    }


def infer_side(row, schema):
    if schema.get("side"):
        side = clean(row.get(schema["side"])).upper()
        if side in {"HOME", "AWAY"}:
            return side

    selection = clean(row.get(schema["selection"])).upper()
    away = clean(row.get(schema.get("away"))).upper() if schema.get("away") else ""
    home = clean(row.get(schema.get("home"))).upper() if schema.get("home") else ""
    if selection and away and selection == away:
        return "AWAY"
    if selection and home and selection == home:
        return "HOME"

    game_key = clean(row.get("game_key"))
    if game_key:
        matches = []
        prefix = f"{game_key}|"
        for key in game_devig_data().get("current", {}).get(
            clean(row.get("sport")).upper() or "NFL", {}
        ):
            if key.startswith(prefix):
                candidate = key.rsplit("|", 1)[-1].upper()
                if candidate in {"HOME", "AWAY"}:
                    matches.append(candidate)
        matches = sorted(set(matches))
        if len(matches) == 1:
            return matches[0]
    return None


def load_current_rows():
    all_rows = []
    all_moneylines = []

    for sport, path in CURRENT_FILES.items():
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False)
        if frame.empty:
            continue
        schema = current_schema(sport, frame)
        if schema["market"] not in frame.columns:
            continue

        money = frame[
            frame[schema["market"]].astype(str).str.upper().eq("MONEYLINE")
        ].copy()

        for _, row in money.iterrows():
            price = num(row.get(schema["price"]))
            score = num(row.get(schema["score"]))
            if price is None or score is None or abs(price) < 100:
                continue

            base = {
                "sport": sport,
                "game_key": clean(row.get("game_key")),
                "selection": clean(row.get(schema["selection"])),
                "side": infer_side(row, schema),
                "american_odds": price,
                "market_implied_probability": american_implied(price),
                "hulk_evidence_score": score,
                "decision_current": clean(row.get(schema["decision"])).upper(),
                "event_start": clean(row.get(schema["start"])),
                "book_count": int(num(row.get(schema["books"])) or 0),
            }
            all_moneylines.append(base)
            if base["decision_current"] in QUALIFIED:
                all_rows.append(base)

    def dedupe(rows):
        chosen = {}
        for row in rows:
            side_key = row.get("side") or row.get("selection")
            key = (row.get("sport"), row.get("game_key"), side_key)
            prior = chosen.get(key)
            if prior is None or int(row.get("book_count") or 0) > int(prior.get("book_count") or 0):
                chosen[key] = row
        return list(chosen.values())

    return dedupe(all_rows), dedupe(all_moneylines)


def fair_probabilities(all_moneylines):
    groups = {}
    for row in all_moneylines:
        key = (row["sport"], row["game_key"])
        groups.setdefault(key, []).append(row)

    fair = {}
    for key, rows in groups.items():
        # Prefer the highest-book-count row on each side.
        by_side = {}
        for row in rows:
            side = row.get("side")
            if side not in {"HOME", "AWAY"}:
                continue
            prior = by_side.get(side)
            if prior is None or row["book_count"] > prior["book_count"]:
                by_side[side] = row

        if set(by_side) != {"HOME", "AWAY"}:
            continue

        p_home = by_side["HOME"]["market_implied_probability"]
        p_away = by_side["AWAY"]["market_implied_probability"]
        total = p_home + p_away
        if not total:
            continue
        fair[(key[0], key[1], "HOME")] = p_home / total
        fair[(key[0], key[1], "AWAY")] = p_away / total
    return fair


def model_probability(model, row):
    p_ref = min(
        0.995,
        max(
            0.005,
            float(
                row.get("market_reference_probability")
                if row.get("market_reference_probability") is not None
                else row["market_implied_probability"]
            ),
        ),
    )
    mlogit = logit(p_ref)
    score_z = (row["hulk_evidence_score"] - 80.0) / 10.0

    beta_m = np.asarray(model["coefficients"]["market_calibrated"], dtype=float)
    beta_f = np.asarray(model["coefficients"]["market_plus_hulk"], dtype=float)
    p_market = float(sigmoid_array(np.array([[1.0, mlogit]]) @ beta_m)[0])
    p_full = float(sigmoid_array(np.array([[1.0, mlogit, score_z]]) @ beta_f)[0])

    source = model.get("deployment_probability_source", "MARKET_REFERENCE")
    if source == "MARKET_PLUS_HULK":
        p_deploy = p_full
    elif source == "MARKET_CALIBRATED":
        p_deploy = p_market
    else:
        p_deploy = p_ref
    return p_market, p_full, p_deploy


def quality_grade(book_count, fair_available):
    if book_count >= 10 and fair_available:
        return "A"
    if book_count >= 5:
        return "B"
    if book_count >= 3:
        return "C"
    return "D"


def build_current(model, validation, sport_models=None, sport_validations=None):
    sport_models = sport_models or {}
    sport_validations = sport_validations or {}
    current, all_moneylines = load_current_rows()
    fair = fair_probabilities(all_moneylines)

    market_board = []
    for row in all_moneylines:
        board_fair = fair.get((row["sport"], row["game_key"], row.get("side")))
        devig_fair, devig_books = current_fair_probability(
            row["sport"], row["game_key"], row.get("side")
        )
        fair_p = devig_fair if devig_fair is not None else board_fair
        reference_type = (
            "DEVIG_FAIR"
            if devig_fair is not None
            else "BOARD_PAIR_FAIR"
            if board_fair is not None
            else "RAW_FALLBACK"
        )
        reference_p = (
            fair_p if fair_p is not None else row["market_implied_probability"]
        )
        market_board.append({
            **row,
            "raw_market_implied_probability_pct": round(
                100 * row["market_implied_probability"], 2
            ),
            "market_fair_probability_pct": (
                None if fair_p is None else round(100 * fair_p, 2)
            ),
            "market_reference_probability_pct": round(100 * reference_p, 2),
            "market_reference_type": reference_type,
            "devig_paired_books": devig_books,
        })

    sides_by_game = {}
    for candidate in current:
        side = candidate.get("side")
        if side in {"HOME", "AWAY"}:
            sides_by_game.setdefault(
                (candidate.get("sport"), candidate.get("game_key")), set()
            ).add(side)
    conflicted_games = {
        key for key, sides in sides_by_game.items()
        if {"HOME", "AWAY"}.issubset(sides)
    }

    rows = []
    for row in current:
        sport = row["sport"]
        sport_model = sport_models.get(sport, {})
        sport_validation = sport_validations.get(sport, {})

        board_fair = fair.get((sport, row["game_key"], row.get("side")))
        devig_fair, devig_books = current_fair_probability(
            sport, row["game_key"], row.get("side")
        )
        if devig_fair is not None:
            fair_p = devig_fair
            reference_type = "DEVIG_FAIR"
        elif board_fair is not None:
            fair_p = board_fair
            reference_type = "BOARD_PAIR_FAIR"
        else:
            fair_p = None
            reference_type = "RAW_FALLBACK"
        reference_p = (
            fair_p if fair_p is not None else row["market_implied_probability"]
        )
        model_row = {
            **row,
            "market_reference_probability": reference_p,
        }
        source = sport_model.get(
            "deployment_probability_source", "MARKET_REFERENCE"
        )

        if (
            sport_validation.get("status") == "READY"
            and sport_model.get("coefficients")
        ):
            p_market_cal, p_full, p_model = model_probability(
                sport_model, model_row
            )
        else:
            p_market_cal = reference_p
            p_full = reference_p
            p_model = reference_p
            source = "MARKET_REFERENCE_INSUFFICIENT_SPORT_HISTORY"

        source_key = (
            "market_plus_hulk"
            if source == "MARKET_PLUS_HULK"
            else "market_calibrated"
            if source == "MARKET_CALIBRATED"
            else "market_reference"
        )
        ece_value = (
            sport_validation.get("metrics", {})
            .get(source_key, {})
            .get("ece")
        )
        buffer = max(0.03, min(0.09, float(ece_value or 0.06)))
        edge = p_model - reference_p
        profit = american_profit(row["american_odds"])
        ev = None if profit is None else (p_model * profit - (1 - p_model))
        conservative_p = max(0.0, p_model - buffer)
        conservative_ev = (
            None if profit is None
            else conservative_p * profit - (1 - conservative_p)
        )
        grade = quality_grade(row["book_count"], fair_p is not None)

        opposite_side_conflict = (sport, row["game_key"]) in conflicted_games

        if opposite_side_conflict:
            shadow = "PASS_CONTRADICTORY_GAME_SIDES"
        elif source != "MARKET_PLUS_HULK":
            shadow = "PASS_NO_PROVEN_INDEPENDENT_SPORT_EDGE"
        elif sport_model.get("historical_edge_confidence") != "SUPPORTED":
            shadow = "PASS_HISTORICAL_CONFIDENCE"
        elif not sport_model.get("hulk_score_confidence_supported", False):
            shadow = "PASS_HISTORICAL_CONFIDENCE"
        elif row["book_count"] < 3:
            shadow = "PASS_DATA_QUALITY"
        elif conservative_ev is None or conservative_ev <= 0.02:
            shadow = "PASS_PRICE"
        elif edge <= 0.02:
            shadow = "PASS_EDGE"
        else:
            shadow = "SHADOW_PLAY"

        rows.append({
            **row,
            "raw_market_implied_probability_pct": round(100 * row["market_implied_probability"], 2),
            "market_fair_probability_pct": None if fair_p is None else round(100 * fair_p, 2),
            "market_reference_probability_pct": round(100 * reference_p, 2),
            "market_reference_type": reference_type,
            "devig_paired_books": devig_books,
            "market_calibrated_probability_pct": round(100 * p_market_cal, 2),
            "market_plus_hulk_probability_pct": round(100 * p_full, 2),
            "calibrated_win_probability_pct": round(100 * p_model, 2),
            "probability_source": source,
            "sport_history_n": int(sport_model.get("history_n") or 0),
            "sport_validation_status": sport_validation.get("status", "INSUFFICIENT_HISTORY"),
            "historical_edge_confidence": sport_model.get(
                "historical_edge_confidence", "INSUFFICIENT_HISTORY"
            ),
            "selection_rule_status": sport_model.get(
                "selection_rule_status", "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY"
            ),
            "old_score_status": sport_model.get("old_score_status", "UNTRAINED"),
            "old_score_coefficient": sport_model.get("old_score_coefficient"),
            "edge_pct_points": round(100 * edge, 2),
            "expected_value_pct": None if ev is None else round(100 * ev, 2),
            "conservative_probability_pct": round(100 * conservative_p, 2),
            "conservative_expected_value_pct": (
                None if conservative_ev is None else round(100 * conservative_ev, 2)
            ),
            "uncertainty_buffer_pct_points": round(100 * buffer, 2),
            "data_quality_grade": grade,
            "opposite_side_conflict": opposite_side_conflict,
            "shadow_decision": shadow,
            "score_is_probability": False,
            "live_pick_changed": False,
        })

    return {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "status": "READY",
        "mode": "SHADOW_ONLY",
        "probability_source": "SPORT_SPECIFIC",
        "hulk_score_adds_out_of_sample_value": any(
            m.get("hulk_score_adds_out_of_sample_value", False)
            for m in sport_models.values()
        ),
        "uncertainty_buffer_pct_points": None,
        "summary": {
            "qualified_moneylines": len(rows),
            "shadow_plays": sum(r["shadow_decision"] == "SHADOW_PLAY" for r in rows),
            "passes": sum(r["shadow_decision"] != "SHADOW_PLAY" for r in rows),
            "fair_probability_available": sum(
                r["market_fair_probability_pct"] is not None for r in rows
            ),
            "market_board_moneylines": len(market_board),
            "by_sport": {
                sport: {
                    "candidates": sum(r["sport"] == sport for r in rows),
                    "shadow_plays": sum(
                        r["sport"] == sport and r["shadow_decision"] == "SHADOW_PLAY"
                        for r in rows
                    ),
                    "passes": sum(
                        r["sport"] == sport and r["shadow_decision"] != "SHADOW_PLAY"
                        for r in rows
                    ),
                    "probability_source": sport_models.get(sport, {}).get(
                        "deployment_probability_source",
                        "MARKET_REFERENCE_INSUFFICIENT_SPORT_HISTORY",
                    ),
                    "historical_edge_confidence": sport_models.get(sport, {}).get(
                        "historical_edge_confidence", "INSUFFICIENT_HISTORY"
                    ),
                    "selection_rule_status": sport_models.get(sport, {}).get(
                        "selection_rule_status", "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY"
                    ),
                    "history_n": int(sport_models.get(sport, {}).get("history_n") or 0),
                }
                for sport in SPORTS
            },
        },
        "picks": rows,
        "market_board": market_board,
        "rules": [
            "This layer is shadow-only and cannot alter current user-facing recommendations.",
            "HULK evidence score is not treated as a win probability.",
            "Each sport is validated separately; one league can never promote another league's model.",
            "The pooled model is retained only as a diagnostic benchmark and is never used for deployment.",
            "Probability source is chosen only from sport-specific walk-forward out-of-sample performance.",
            "Research training may use any valid pregame graded moneyline observation; official Best Bets performance remains qualified-only.",
            "Fair-market probability requires exact HOME/AWAY pairing and prefers same-book de-vigged prices with at least two paired sportsbooks.",
            "A HULK model must beat both the fair/reference market and its calibrated version, with positive paired game-block confidence, before PLAY eligibility.",
            "PLAY additionally requires positive conservative EV, positive edge, minimum data quality, and forward proof; no automatic promotion occurs.",
        ],
    }


def main():
    history = build_history()
    if history.empty:
        raise SystemExit("No valid historical moneyline calibration rows.")

    validation = walk_forward(history)
    model = fit_final_models(history, validation)

    sport_validations = {}
    sport_models = {}
    for sport in SPORTS:
        sport_history = history[history["sport"].eq(sport)].copy()
        sport_validation = walk_forward(sport_history)
        sport_validations[sport] = sport_validation
        if sport_validation.get("status") == "READY":
            sport_models[sport] = fit_final_models(sport_history, sport_validation)
        else:
            devig_n = int(
                sport_history["market_reference_type"].eq("DEVIG_FAIR").sum()
            ) if not sport_history.empty else 0
            sport_models[sport] = {
                "trained_at": now_iso(),
                "history_n": int(len(sport_history)),
                "independent_blocks": int(
                    sport_history["block_key"].nunique()
                ) if not sport_history.empty else 0,
                "sport": sport,
                "coefficients": {},
                "deployment_probability_source": "MARKET_REFERENCE_INSUFFICIENT_SPORT_HISTORY",
                "hulk_score_adds_out_of_sample_value": False,
                "hulk_score_confidence_supported": False,
                "historical_edge_confidence": "INSUFFICIENT_HISTORY",
                "selection_rule_status": "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY",
                "old_score_status": "UNTRAINED",
                "old_score_coefficient": None,
                "devig_history_n": devig_n,
                "devig_history_pct": (
                    round(100.0 * devig_n / len(sport_history), 1)
                    if len(sport_history) else 0.0
                ),
                "score_is_probability": False,
                "automatic_live_change": False,
            }

    model = {
        **model,
        "model_version": MODEL_VERSION,
        "deployment_scope": "SPORT_SPECIFIC",
        "pooled_model_is_diagnostic_only": True,
        "models_by_sport": sport_models,
    }
    current = build_current(model, validation, sport_models, sport_validations)

    research_counts = {
        sport: int((history["sport"] == sport).sum())
        for sport in SPORTS
    }
    official_counts = official_best_bet_history_counts()
    validation_payload = {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "history_rows": int(len(history)),
        "history_by_sport": research_counts,
        "research_training_history_rows": int(len(history)),
        "research_training_history_by_sport": research_counts,
        "official_best_bet_history_by_sport": official_counts,
        "method": "SPORT_SPECIFIC_FAIR_MARKET_ROLLING_ORIGIN_WITH_GAME_BLOCK_CONFIDENCE",
        "validation": validation,
        "pooled_validation_is_diagnostic_only": True,
        "by_sport": sport_validations,
        "fair_market_coverage": game_devig_data().get("coverage", {}),
        "data_policy": {
            "training_scope": "ALL_VALID_PRE_EVENT_GRADED_GAME_MONEYLINE_OBSERVATIONS",
            "official_record_scope": "QUALIFIED_RESEARCH_ONLY",
            "dedupe": "FIRST_PRE_EVENT_SNAPSHOT_PER_SPORT_GAME_SELECTION",
            "post_start_rows_rejected": True,
            "market_reference": "2PLUS_BOOK_SAME_BOOK_DEVIG_FAIR_THEN_BOARD_PAIR_FAIR_THEN_RAW_FALLBACK",
            "price_policy": "PUBLISH_TIME_AMERICAN_PRICE",
            "outcomes": "WIN_LOSS_ONLY",
            "official_record_never_rewritten_by_training_rows": True,
        },
    }

    for path, payload in [
        (MODEL_OUT, model),
        (VALIDATION_OUT, validation_payload),
        (CURRENT_OUT, current),
        (PUBLIC / "betting_v2_model.json", model),
        (PUBLIC / "betting_v2_current.json", current),
        (PUBLIC / "betting_v2_validation.json", validation_payload),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    if DIST.exists():
        (DIST / "betting_v2_model.json").write_text(json.dumps(model, indent=2))
        (DIST / "betting_v2_current.json").write_text(json.dumps(current, indent=2))
        (DIST / "betting_v2_validation.json").write_text(json.dumps(validation_payload, indent=2))

    print(json.dumps({
        "status": current["status"],
        "history_rows": len(history),
        "history_by_sport": validation_payload["history_by_sport"],
        "deployment_probability_source": model["deployment_probability_source"],
        "hulk_score_adds_value": model["hulk_score_adds_out_of_sample_value"],
        "validation": validation.get("metrics"),
        "current_summary": current["summary"],
    }, indent=2))


if __name__ == "__main__":
    main()
