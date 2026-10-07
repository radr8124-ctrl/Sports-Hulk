#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from nba_live.decision.nba_proof_source_digest import digest_csv as nba_grade_digest
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

DEVIG_OUT = OUT_DIR / "BETTING_V2_ALL_MARKET_DEVIG.json"
MODEL_OUT = OUT_DIR / "BETTING_V2_ALL_MARKETS_MODELS.json"
VALIDATION_OUT = OUT_DIR / "BETTING_V2_ALL_MARKETS_VALIDATION.json"
CURRENT_OUT = OUT_DIR / "BETTING_V2_ALL_MARKETS_CURRENT.json"

MODEL_VERSION = "BETTING_V2_ALL_MARKETS_2026_10_05"
SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
MARKETS = ("MONEYLINE", "SPREAD", "TOTAL")
QUALIFIED = {
    "QUALIFIED_RESEARCH",
    "STRONG_RESEARCH",
    "HIGH_JUICE",
    "HIGH_JUICE_WATCH",
}

HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" /
    f"{sport}_GRADED_RECOMMENDATIONS.csv"
    for sport in SPORTS
}
CURRENT_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" /
    f"{sport}_GAME_DECISIONS.csv"
    for sport in SPORTS
}

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_betting_v2 as base
from competition_regime import (
    normalize_competition_regime,
    proof_lane_key,
    proof_version,
)

_DEVIG = None


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


def norm(value):
    return re.sub(r"[^a-z0-9]+", "", clean(value).lower())


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def parse_dt(value):
    try:
        d = pd.to_datetime(value, errors="coerce", utc=True)
        return None if pd.isna(d) else d
    except Exception:
        return None


def parse_json(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def devig_data():
    global _DEVIG
    if _DEVIG is None:
        try:
            _DEVIG = json.loads(DEVIG_OUT.read_text())
        except Exception:
            _DEVIG = {
                "history": {},
                "current": {},
                "minimum_paired_books_for_model": 2,
            }
    return _DEVIG


def american_implied(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def american_profit(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def logit(p):
    p = min(0.995, max(0.005, float(p)))
    return math.log(p / (1.0 - p))


def sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -35, 35)
    return 1.0 / (1.0 + np.exp(-z))


def block_weights(frame):
    if frame.empty:
        return np.array([], dtype=float)
    counts = frame.groupby("block_key")["block_key"].transform("count").astype(float)
    raw = 1.0 / counts.to_numpy()
    scale = len(raw) / raw.sum() if raw.sum() else 1.0
    return raw * scale


def fit_logistic_weighted(X, y, weights, l2=2.0, max_iter=100):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if X.ndim != 2 or len(X) == 0:
        raise ValueError("No model rows.")
    if len(weights) != len(y):
        weights = np.ones(len(y), dtype=float)

    weighted_mean = float(
        np.average(y, weights=np.clip(weights, 1e-9, None))
    )
    weighted_mean = min(0.99, max(0.01, weighted_mean))
    beta = np.zeros(X.shape[1], dtype=float)
    beta[0] = math.log(weighted_mean / (1 - weighted_mean))
    penalty = np.eye(X.shape[1], dtype=float)
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        p = sigmoid(X @ beta)
        variance = np.clip(p * (1 - p), 1e-6, None)
        grad = X.T @ ((p - y) * weights) + l2 * (penalty @ beta)
        hw = variance * weights
        hess = X.T @ (X * hw[:, None]) + l2 * penalty
        try:
            step = np.linalg.solve(hess, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hess) @ grad
        nxt = beta - step
        if np.max(np.abs(nxt - beta)) < 1e-8:
            beta = nxt
            break
        beta = nxt
    return beta


def predict(beta, X):
    return sigmoid(np.asarray(X, dtype=float) @ np.asarray(beta, dtype=float))


def evaluate(y, p):
    return base.evaluate_predictions(
        np.asarray(y, dtype=float),
        np.asarray(p, dtype=float),
    )


def history_rec_key(sport, row):
    key = clean(row.get("recommendation_key"))
    if key:
        return key
    return "|".join([
        sport,
        clean(row.get("snapshot_at")),
        clean(row.get("game_key")),
        clean(row.get("market")),
        clean(row.get("selection")),
        clean(row.get("line")),
    ])


def history_devig(sport, rec_key):
    record = (
        devig_data().get("history", {})
        .get(sport, {})
        .get(clean(rec_key), {})
    )
    fair = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    odds = num(record.get("median_selected_odds"))
    minimum = int(
        num(devig_data().get("minimum_paired_books_for_model")) or 2
    )
    usable_fair = (
        fair
        if fair is not None and 0 < fair < 1 and books >= minimum
        else None
    )
    valid_odds = odds if odds is not None and abs(odds) >= 100 else None
    return usable_fair, books, valid_odds


def current_devig_key(game_key, market, selection_key, line):
    market = clean(market).upper()
    line_text = ""
    if market != "MONEYLINE":
        line = num(line)
        if line is None:
            return ""
        line_text = f"{line:.4f}"
    return "|".join([
        clean(game_key),
        market,
        clean(selection_key).upper(),
        line_text,
    ])


def current_devig(sport, game_key, market, selection_key, line):
    key = current_devig_key(
        game_key, market, selection_key, line
    )
    record = (
        devig_data().get("current", {})
        .get(sport, {})
        .get(key, {})
    )
    fair = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    odds = num(record.get("median_selected_odds"))
    minimum = int(
        num(devig_data().get("minimum_paired_books_for_model")) or 2
    )
    usable_fair = (
        fair
        if fair is not None and 0 < fair < 1 and books >= minimum
        else None
    )
    valid_odds = odds if odds is not None and abs(odds) >= 100 else None
    return usable_fair, books, valid_odds


def extract_history_price(row, devig_odds):
    payload = parse_json(row.get("payload_json"))
    for key in [
        "median_price_american",
        "price_median",
        "american_odds",
        "sportsbook_price",
    ]:
        value = num(payload.get(key))
        if value is not None and abs(value) >= 100:
            return value
    market = clean(row.get("market")).upper()
    if market == "MONEYLINE":
        value = num(row.get("line"))
        if value is not None and abs(value) >= 100:
            return value
    return devig_odds


def history_line(row):
    payload = parse_json(row.get("payload_json"))
    market = clean(row.get("market")).upper()
    if market == "MONEYLINE":
        return None
    for value in [
        row.get("line"),
        payload.get("line_group"),
        payload.get("line"),
    ]:
        x = num(value)
        if x is not None and abs(x) < 1000:
            return x
    return None


def history_start(row):
    payload = parse_json(row.get("payload_json"))
    for value in [
        row.get("start"),
        payload.get("start_dt"),
        payload.get("start"),
    ]:
        dt = parse_dt(value)
        if dt is not None:
            return dt
    return None


def build_history(sport, market):
    path = HISTORY_FILES[sport]
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if (
        d.empty
        or "lane" not in d.columns
        or "grade" not in d.columns
        or "market" not in d.columns
    ):
        return pd.DataFrame()

    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["market"].astype(str).str.upper().eq(market)
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    if d.empty:
        return d

    d["_snapshot"] = pd.to_datetime(
        d.get("snapshot_at"), errors="coerce", utc=True
    )
    d = d.sort_values("_snapshot")
    rows = []

    for _, row in d.iterrows():
        start = history_start(row)
        snapshot = row.get("_snapshot")
        if start is not None and pd.notna(snapshot) and snapshot >= start:
            continue
        score = num(row.get("score"))
        if score is None:
            continue

        rec_key = history_rec_key(sport, row)
        fair_p, fair_books, devig_odds = history_devig(
            sport, rec_key
        )
        price = extract_history_price(row, devig_odds)
        raw_p = american_implied(price)
        if raw_p is None:
            continue
        ref_p = fair_p if fair_p is not None else raw_p
        line = history_line(row)
        selection = clean(row.get("selection"))
        game_key = clean(row.get("game_key"))
        if not game_key or not selection:
            continue

        explicit_regime = ""
        for regime_field in (
            "season_type",
            "competition_regime",
            "season_phase",
            "competition_phase",
        ):
            candidate_regime = row.get(regime_field)
            if clean(candidate_regime):
                explicit_regime = candidate_regime
                break
        competition_regime = normalize_competition_regime(
            explicit_regime,
            sport,
        )
        lane_key = f"{sport}_{market}"

        rows.append({
            "sport": sport,
            "market": market,
            "lane_key": lane_key,
            "competition_regime": competition_regime,
            "proof_lane_key": proof_lane_key(
                sport,
                market,
                competition_regime,
            ),
            "game_key": game_key,
            "selection": selection,
            "line": line,
            "recommendation_key": rec_key,
            "score": score,
            "american_odds": price,
            "market_raw_probability": raw_p,
            "market_reference_probability": ref_p,
            "market_reference_type": (
                "DEVIG_FAIR" if fair_p is not None
                else "RAW_FALLBACK"
            ),
            "devig_paired_books": fair_books,
            "outcome": (
                1 if clean(row.get("grade")).upper() == "WIN"
                else 0
            ),
            "snapshot_at": snapshot,
            "event_start": start,
            "block_key": f"{sport}|{game_key}",
        })

    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["_time"] = pd.to_datetime(
        frame["snapshot_at"], errors="coerce", utc=True
    )
    frame["_time"] = frame["_time"].fillna(
        pd.to_datetime(
            frame["event_start"], errors="coerce", utc=True
        )
    )
    frame["_time"] = frame["_time"].fillna(
        pd.Timestamp("1970-01-01", tz="UTC")
    )
    # Freeze the first pregame decision snapshot for each game.
    first_time = frame.groupby(
        "game_key", dropna=False
    )["_time"].transform("min")
    frame = frame[frame["_time"].eq(first_time)].copy()
    if frame.empty:
        return frame

    # From that frozen snapshot keep one canonical line per selection:
    # the valid market price closest to 50/50, with broader de-vig
    # coverage as the tie-breaker. Alternate lines do not multiply history.
    frame["_price_distance"] = (
        frame["market_raw_probability"].astype(float) - 0.5
    ).abs()
    frame = (
        frame.sort_values(
            [
                "game_key",
                "selection",
                "_price_distance",
                "devig_paired_books",
            ],
            ascending=[True, True, True, False],
        )
        .drop_duplicates(
            ["sport", "market", "game_key", "selection"],
            keep="first",
        )
        .sort_values("_time")
        .reset_index(drop=True)
    )
    return frame


def partition_proof_frames(frame):
    if frame.empty or "proof_lane_key" not in frame.columns:
        return {}
    return {
        str(key): group.copy().reset_index(drop=True)
        for key, group in frame.groupby(
            "proof_lane_key",
            dropna=False,
            sort=True,
        )
    }


def matrices(frame):
    p = frame["market_reference_probability"].astype(float).clip(
        0.005, 0.995
    )
    market_logit = np.log(p / (1 - p)).to_numpy()
    score_z = (
        (frame["score"].astype(float) - 80.0) / 10.0
    ).to_numpy()
    market = np.column_stack([
        np.ones(len(frame)), market_logit
    ])
    score = np.column_stack([
        np.ones(len(frame)), score_z
    ])
    full = np.column_stack([
        np.ones(len(frame)), market_logit, score_z
    ])
    return market, score, full


def ordered_blocks(frame):
    b = (
        frame.groupby("block_key", as_index=False)["_time"]
        .min()
        .sort_values("_time")
    )
    return b["block_key"].astype(str).tolist()


def walk_forward(frame):
    n = len(frame)
    blocks = ordered_blocks(frame) if not frame.empty else []
    block_n = len(blocks)
    if n < 50 or block_n < 25:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "history_n": n,
            "independent_blocks": block_n,
            "minimum_rows": 50,
            "minimum_independent_blocks": 25,
        }

    min_train_blocks = max(
        20, int(math.floor(block_n * 0.50))
    )
    step_blocks = max(
        5, int(math.ceil(block_n * 0.10))
    )
    records = []

    for start in range(
        min_train_blocks, block_n, step_blocks
    ):
        end = min(block_n, start + step_blocks)
        train_blocks = set(blocks[:start])
        test_blocks = set(blocks[start:end])
        train = frame[
            frame["block_key"].astype(str).isin(train_blocks)
        ].copy()
        test = frame[
            frame["block_key"].astype(str).isin(test_blocks)
        ].copy()
        if train.empty or test.empty:
            continue
        y_train = train["outcome"].astype(int).to_numpy()
        y_test = test["outcome"].astype(int).to_numpy()
        if len(set(y_train.tolist())) < 2:
            continue

        Xm_tr, Xs_tr, Xf_tr = matrices(train)
        Xm_te, Xs_te, Xf_te = matrices(test)
        weights = block_weights(train)

        bm = fit_logistic_weighted(
            Xm_tr, y_train, weights, l2=2.0
        )
        bs = fit_logistic_weighted(
            Xs_tr, y_train, weights, l2=3.0
        )
        bf = fit_logistic_weighted(
            Xf_tr, y_train, weights, l2=3.0
        )

        records.append({
            "y": y_test,
            "block": test["block_key"].astype(str).to_numpy(),
            "market_raw": test[
                "market_raw_probability"
            ].astype(float).to_numpy(),
            "market_reference": test[
                "market_reference_probability"
            ].astype(float).to_numpy(),
            "market_calibrated": predict(bm, Xm_te),
            "score_only": predict(bs, Xs_te),
            "market_plus_hulk": predict(bf, Xf_te),
        })

    if not records:
        return {
            "status": "NO_FOLDS",
            "history_n": n,
            "independent_blocks": block_n,
        }

    y = np.concatenate([r["y"] for r in records])
    test_blocks = np.concatenate([
        r["block"] for r in records
    ])
    preds = {
        key: np.concatenate([r[key] for r in records])
        for key in [
            "market_raw",
            "market_reference",
            "market_calibrated",
            "score_only",
            "market_plus_hulk",
        ]
    }
    metrics = {
        key: evaluate(y, pred)
        for key, pred in preds.items()
    }
    comparisons = {
        "hulk_vs_reference": base.paired_block_comparison(
            y, preds["market_plus_hulk"],
            preds["market_reference"], test_blocks, 3101
        ),
        "hulk_vs_calibrated": base.paired_block_comparison(
            y, preds["market_plus_hulk"],
            preds["market_calibrated"], test_blocks, 3102
        ),
        "calibrated_vs_reference": base.paired_block_comparison(
            y, preds["market_calibrated"],
            preds["market_reference"], test_blocks, 3103
        ),
        "reference_vs_raw": base.paired_block_comparison(
            y, preds["market_reference"],
            preds["market_raw"], test_blocks, 3104
        ),
    }

    ref = metrics["market_reference"]
    cal = metrics["market_calibrated"]
    full = metrics["market_plus_hulk"]

    hulk_beats_ref = (
        full["brier"] <= ref["brier"] - 0.001
        and full["log_loss"] <= ref["log_loss"] - 0.001
    )
    hulk_beats_cal = (
        full["brier"] <= cal["brier"] - 0.0005
        and full["log_loss"] <= cal["log_loss"] - 0.0005
    )
    calibration_adds = (
        cal["brier"] <= ref["brier"] - 0.001
        and cal["log_loss"] <= ref["log_loss"] - 0.001
    )

    Xm, Xs, Xf = matrices(frame)
    y_full = frame["outcome"].astype(int).to_numpy()
    weights = block_weights(frame)
    bf = fit_logistic_weighted(
        Xf, y_full, weights, l2=3.0
    )
    old_coef = float(bf[-1])
    old_status = (
        "NEGATIVE_ORDERING_REJECTED"
        if old_coef < -0.02
        else "POSITIVE_INCREMENTAL_SIGNAL"
        if old_coef > 0.02 and hulk_beats_ref and hulk_beats_cal
        else "POSITIVE_BUT_NO_INCREMENTAL_VALUE"
        if old_coef > 0.02
        else "FLAT_OR_UNPROVEN"
    )
    hulk_mean = bool(
        hulk_beats_ref
        and hulk_beats_cal
        and old_status == "POSITIVE_INCREMENTAL_SIGNAL"
    )
    hulk_conf = bool(
        hulk_mean
        and comparisons["hulk_vs_reference"][
            "confidence_supported"
        ]
        and comparisons["hulk_vs_calibrated"][
            "confidence_supported"
        ]
    )

    if hulk_mean:
        source = "MARKET_PLUS_HULK"
        hist_conf = (
            "SUPPORTED" if hulk_conf
            else "PROMISING_BUT_UNCERTAIN"
        )
        selection_status = (
            "FORWARD_VALIDATION_REQUIRED"
            if hulk_conf
            else "HISTORICAL_SIGNAL_UNCERTAIN_RESEARCH_ONLY"
        )
    elif calibration_adds:
        source = "MARKET_CALIBRATED"
        hist_conf = (
            "CALIBRATION_SUPPORTED"
            if comparisons["calibrated_vs_reference"][
                "confidence_supported"
            ]
            else "CALIBRATION_MEAN_ONLY"
        )
        selection_status = (
            "CALIBRATION_ONLY_NO_INDEPENDENT_EDGE"
        )
    else:
        source = "MARKET_REFERENCE"
        hist_conf = "NO_INDEPENDENT_EDGE"
        selection_status = "NO_INDEPENDENT_MODEL_EDGE"

    return {
        "status": "READY",
        "history_n": n,
        "independent_blocks": block_n,
        "walk_forward_n": int(len(y)),
        "walk_forward_blocks": int(len(set(test_blocks.tolist()))),
        "folds": len(records),
        "metrics": metrics,
        "paired_comparisons": comparisons,
        "devig_history_n": int(
            frame["market_reference_type"].eq(
                "DEVIG_FAIR"
            ).sum()
        ),
        "devig_history_pct": round(
            100 * float(
                frame["market_reference_type"].eq(
                    "DEVIG_FAIR"
                ).mean()
            ),
            1,
        ),
        "old_score_coefficient": round(old_coef, 5),
        "old_score_status": old_status,
        "hulk_score_adds_out_of_sample_value": hulk_mean,
        "hulk_score_confidence_supported": hulk_conf,
        "market_recalibration_adds_out_of_sample_value": bool(
            calibration_adds
        ),
        "historical_edge_confidence": hist_conf,
        "selection_rule_status": selection_status,
        "deployment_probability_source": source,
    }


def fit_final(frame, validation):
    Xm, Xs, Xf = matrices(frame)
    y = frame["outcome"].astype(int).to_numpy()
    weights = block_weights(frame)
    return {
        "trained_at": now_iso(),
        "model_version": MODEL_VERSION,
        "history_n": int(len(frame)),
        "independent_blocks": int(
            frame["block_key"].nunique()
        ),
        "coefficients": {
            "market_calibrated": [
                round(float(v), 8)
                for v in fit_logistic_weighted(
                    Xm, y, weights, l2=2.0
                )
            ],
            "score_only": [
                round(float(v), 8)
                for v in fit_logistic_weighted(
                    Xs, y, weights, l2=3.0
                )
            ],
            "market_plus_hulk": [
                round(float(v), 8)
                for v in fit_logistic_weighted(
                    Xf, y, weights, l2=3.0
                )
            ],
        },
        "deployment_probability_source": validation.get(
            "deployment_probability_source",
            "MARKET_REFERENCE",
        ),
        "historical_edge_confidence": validation.get(
            "historical_edge_confidence", "WAITING"
        ),
        "selection_rule_status": validation.get(
            "selection_rule_status", "WAITING"
        ),
        "hulk_score_adds_out_of_sample_value": bool(
            validation.get(
                "hulk_score_adds_out_of_sample_value",
                False,
            )
        ),
        "hulk_score_confidence_supported": bool(
            validation.get(
                "hulk_score_confidence_supported",
                False,
            )
        ),
        "old_score_status": validation.get(
            "old_score_status", "WAITING"
        ),
        "old_score_coefficient": validation.get(
            "old_score_coefficient"
        ),
        "automatic_live_change": False,
    }


REGIME_SOURCE_COLUMNS = (
    "season_type",
    "competition_regime",
    "season_phase",
    "competition_phase",
)


def explicit_regime_value(row, columns):
    for column in REGIME_SOURCE_COLUMNS:
        if column in columns and clean(row.get(column)):
            return row.get(column)
    return None


def current_schema(sport, frame):
    regime_column = next(
        (
            column
            for column in (
                "season_type",
                "competition_regime",
                "season_phase",
                "competition_phase",
            )
            if column in frame.columns
        ),
        None,
    )
    if sport == "NFL":
        return {
            "market": "market",
            "selection": "selection",
            "line": "line",
            "price": None,
            "score": "hulk_market_score",
            "decision": "decision",
            "start": "start",
            "books": "sw_books",
            "away": None,
            "home": None,
            "side": None,
            "regime": regime_column,
        }
    return {
        "market": "market_canonical",
        "selection": "selection_canonical",
        "line": (
            "line_group" if "line_group" in frame.columns
            else "line"
        ),
        "price": "median_price_american",
        "score": "evidence_score",
        "decision": "decision",
        "start": "start_dt",
        "books": "sportsbook_count",
        "away": (
            "away_team" if "away_team" in frame.columns
            else "away_team_canonical"
            if "away_team_canonical" in frame.columns
            else None
        ),
        "home": (
            "home_team" if "home_team" in frame.columns
            else "home_team_canonical"
            if "home_team_canonical" in frame.columns
            else None
        ),
        "side": (
            "selection_side"
            if "selection_side" in frame.columns
            else None
        ),
        "regime": regime_column,
    }


def infer_selection_key(sport, row, schema, market, line):
    selection = clean(row.get(schema["selection"])).upper()
    if market == "TOTAL":
        return (
            selection
            if selection in {"OVER", "UNDER"}
            else None
        )

    if schema.get("side"):
        side = clean(row.get(schema["side"])).upper()
        if side in {"HOME", "AWAY"}:
            return side

    away = (
        clean(row.get(schema.get("away"))).upper()
        if schema.get("away")
        else ""
    )
    home = (
        clean(row.get(schema.get("home"))).upper()
        if schema.get("home")
        else ""
    )
    if selection and away and selection == away:
        return "AWAY"
    if selection and home and selection == home:
        return "HOME"

    # NFL rows use full names while the game key uses abbreviations.
    prefix = "|".join([
        clean(row.get("game_key")),
        market,
    ]) + "|"
    suffix = (
        "|"
        if market == "MONEYLINE"
        else f"|{float(line):.4f}"
        if line is not None
        else "|"
    )
    matches = []
    for key in devig_data().get("current", {}).get(
        sport, {}
    ):
        if key.startswith(prefix) and key.endswith(suffix):
            parts = key.split("|")
            if len(parts) >= 3:
                candidate = parts[2].upper()
                if candidate in {"HOME", "AWAY"}:
                    matches.append(candidate)
    matches = sorted(set(matches))
    return matches[0] if len(matches) == 1 else None


def model_probability(model, ref_p, score):
    ref_p = min(0.995, max(0.005, float(ref_p)))
    mlogit = logit(ref_p)
    score_z = (float(score) - 80.0) / 10.0
    bm = np.asarray(
        model["coefficients"]["market_calibrated"],
        dtype=float,
    )
    bf = np.asarray(
        model["coefficients"]["market_plus_hulk"],
        dtype=float,
    )
    p_cal = float(
        predict(bm, np.array([[1.0, mlogit]]))[0]
    )
    p_full = float(
        predict(
            bf,
            np.array([[1.0, mlogit, score_z]]),
        )[0]
    )
    source = model.get(
        "deployment_probability_source",
        "MARKET_REFERENCE",
    )
    if source == "MARKET_PLUS_HULK":
        return p_cal, p_full, p_full
    if source == "MARKET_CALIBRATED":
        return p_cal, p_full, p_cal
    return p_cal, p_full, ref_p


def quality_grade(book_count, fair):
    if book_count >= 10 and fair:
        return "A"
    if book_count >= 5:
        return "B"
    if book_count >= 3:
        return "C"
    return "D"


def build_current(models, validations):
    rows = []

    for sport in SPORTS:
        path = CURRENT_FILES[sport]
        if not path.exists():
            continue
        frame = pd.read_csv(path, low_memory=False)
        if frame.empty:
            continue
        schema = current_schema(sport, frame)

        for _, row in frame.iterrows():
            market = clean(row.get(schema["market"])).upper()
            if market not in MARKETS:
                continue
            decision = clean(
                row.get(schema["decision"])
            ).upper()
            if decision not in QUALIFIED:
                continue
            score = num(row.get(schema["score"]))
            if score is None:
                continue
            line = (
                None
                if market == "MONEYLINE"
                else num(row.get(schema["line"]))
            )
            selection_key = infer_selection_key(
                sport, row, schema, market, line
            )
            if not selection_key:
                continue

            fair_p, devig_books, devig_odds = current_devig(
                sport,
                clean(row.get("game_key")),
                market,
                selection_key,
                line,
            )
            price = (
                num(row.get(schema["price"]))
                if schema.get("price")
                else None
            )
            if price is None or abs(price) < 100:
                price = devig_odds
            raw_p = american_implied(price)
            if raw_p is None:
                # No valid American price means no probability or EV claim.
                continue
            ref_p = fair_p if fair_p is not None else raw_p

            lane_key = f"{sport}_{market}"
            explicit_regime = explicit_regime_value(
                row,
                frame.columns,
            )
            competition_regime = normalize_competition_regime(
                explicit_regime,
                sport,
            )
            current_proof_lane_key = proof_lane_key(
                sport,
                market,
                competition_regime,
            )
            current_proof_version = proof_version(
                MODEL_VERSION,
                sport,
                competition_regime,
            )
            validation = validations.get(
                current_proof_lane_key,
                {},
            )
            model = models.get(
                current_proof_lane_key,
                {},
            )
            source = model.get(
                "deployment_probability_source",
                "MARKET_REFERENCE_INSUFFICIENT_HISTORY",
            )
            if (
                validation.get("status") == "READY"
                and model.get("coefficients")
            ):
                p_cal, p_full, p_model = model_probability(
                    model, ref_p, score
                )
            else:
                p_cal = ref_p
                p_full = ref_p
                p_model = ref_p
                source = (
                    "MARKET_REFERENCE_INSUFFICIENT_HISTORY"
                )

            source_key = (
                "market_plus_hulk"
                if source == "MARKET_PLUS_HULK"
                else "market_calibrated"
                if source == "MARKET_CALIBRATED"
                else "market_reference"
            )
            ece = (
                validation.get("metrics", {})
                .get(source_key, {})
                .get("ece")
            )
            buffer = max(
                0.03,
                min(0.09, float(ece or 0.06)),
            )
            edge = p_model - ref_p
            profit = american_profit(price)
            ev = (
                None if profit is None
                else p_model * profit - (1 - p_model)
            )
            conservative_p = max(
                0.0, p_model - buffer
            )
            conservative_ev = (
                None if profit is None
                else conservative_p * profit
                - (1 - conservative_p)
            )
            books = int(
                num(row.get(schema["books"])) or 0
            )
            grade = quality_grade(
                books, fair_p is not None
            )

            if source != "MARKET_PLUS_HULK":
                provisional = (
                    "PASS_NO_PROVEN_INDEPENDENT_LANE_EDGE"
                )
            elif model.get(
                "historical_edge_confidence"
            ) != "SUPPORTED":
                provisional = "PASS_HISTORICAL_CONFIDENCE"
            elif not model.get(
                "hulk_score_confidence_supported",
                False,
            ):
                provisional = "PASS_HISTORICAL_CONFIDENCE"
            elif books < 3:
                provisional = "PASS_DATA_QUALITY"
            elif (
                conservative_ev is None
                or conservative_ev <= 0.02
            ):
                provisional = "PASS_PRICE"
            elif edge <= 0.02:
                provisional = "PASS_EDGE"
            else:
                provisional = "SHADOW_PLAY"

            rows.append({
                "model_version": MODEL_VERSION,
                "lane_key": lane_key,
                "proof_lane_key": current_proof_lane_key,
                "competition_regime": competition_regime,
                "proof_version": current_proof_version,
                "sport": sport,
                "market": market,
                "game_key": clean(row.get("game_key")),
                "selection": clean(
                    row.get(schema["selection"])
                ),
                "selection_key": selection_key,
                "line": line,
                "american_odds": price,
                "event_start": clean(
                    row.get(schema["start"])
                ),
                "book_count": books,
                "hulk_evidence_score": score,
                "decision_current": decision,
                "raw_market_implied_probability_pct": round(
                    100 * raw_p, 2
                ),
                "market_fair_probability_pct": (
                    None if fair_p is None
                    else round(100 * fair_p, 2)
                ),
                "market_reference_probability_pct": round(
                    100 * ref_p, 2
                ),
                "market_reference_type": (
                    "DEVIG_FAIR"
                    if fair_p is not None
                    else "RAW_FALLBACK"
                ),
                "devig_paired_books": devig_books,
                "market_calibrated_probability_pct": round(
                    100 * p_cal, 2
                ),
                "market_plus_hulk_probability_pct": round(
                    100 * p_full, 2
                ),
                "calibrated_win_probability_pct": round(
                    100 * p_model, 2
                ),
                "probability_source": source,
                "historical_edge_confidence": model.get(
                    "historical_edge_confidence",
                    "INSUFFICIENT_HISTORY",
                ),
                "selection_rule_status": model.get(
                    "selection_rule_status",
                    "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY",
                ),
                "old_score_status": model.get(
                    "old_score_status", "UNTRAINED"
                ),
                "old_score_coefficient": model.get(
                    "old_score_coefficient"
                ),
                "lane_history_n": int(
                    model.get("history_n") or 0
                ),
                "edge_pct_points": round(
                    100 * edge, 2
                ),
                "expected_value_pct": (
                    None if ev is None
                    else round(100 * ev, 2)
                ),
                "conservative_probability_pct": round(
                    100 * conservative_p, 2
                ),
                "conservative_expected_value_pct": (
                    None
                    if conservative_ev is None
                    else round(100 * conservative_ev, 2)
                ),
                "uncertainty_buffer_pct_points": round(
                    100 * buffer, 2
                ),
                "data_quality_grade": grade,
                "provisional_shadow_decision": provisional,
                "shadow_decision": provisional,
                "opposite_side_conflict": False,
                "duplicate_line_variant": False,
                "same_game_exposure_block": False,
                "live_pick_changed": False,
            })

    # Exact opposite-side conflict gate.
    groups = {}
    for idx, row in enumerate(rows):
        line_key = (
            ""
            if row["market"] == "MONEYLINE"
            else f"{abs(float(row['line'])):.4f}"
            if row.get("line") is not None
            else ""
        )
        key = (
            row["sport"],
            row["game_key"],
            row["market"],
            line_key,
        )
        groups.setdefault(key, []).append(idx)

    for indexes in groups.values():
        selections = {
            rows[i]["selection_key"]
            for i in indexes
        }
        market = rows[indexes[0]]["market"]
        required = (
            {"OVER", "UNDER"}
            if market == "TOTAL"
            else {"HOME", "AWAY"}
        )
        if required.issubset(selections):
            for i in indexes:
                rows[i]["opposite_side_conflict"] = True
                rows[i]["shadow_decision"] = (
                    "PASS_CONTRADICTORY_GAME_SIDES"
                )

    # If several alternate lines for the same side would qualify,
    # only the strongest can survive.
    variants = {}
    for idx, row in enumerate(rows):
        key = (
            row["sport"],
            row["game_key"],
            row["market"],
            row["selection_key"],
        )
        variants.setdefault(key, []).append(idx)

    for indexes in variants.values():
        if len(indexes) <= 1:
            continue
        for i in indexes:
            rows[i]["duplicate_line_variant"] = True
        shadow_indexes = [
            i for i in indexes
            if rows[i]["shadow_decision"] == "SHADOW_PLAY"
        ]
        if len(shadow_indexes) > 1:
            best = max(
                shadow_indexes,
                key=lambda i: (
                    num(
                        rows[i].get(
                            "conservative_expected_value_pct"
                        )
                    )
                    or -999,
                    int(rows[i].get("book_count") or 0),
                ),
            )
            for i in shadow_indexes:
                if i != best:
                    rows[i]["shadow_decision"] = (
                        "PASS_DUPLICATE_LINE_VARIANT"
                    )

    # Portfolio guard: at most one SHADOW_PLAY per game.
    by_game = {}
    for idx, row in enumerate(rows):
        by_game.setdefault(
            (row["sport"], row["game_key"]), []
        ).append(idx)
    for indexes in by_game.values():
        shadow_indexes = [
            i for i in indexes
            if rows[i]["shadow_decision"] == "SHADOW_PLAY"
        ]
        if len(shadow_indexes) > 1:
            best = max(
                shadow_indexes,
                key=lambda i: (
                    num(
                        rows[i].get(
                            "conservative_expected_value_pct"
                        )
                    )
                    or -999,
                    num(rows[i].get("edge_pct_points"))
                    or -999,
                    int(rows[i].get("book_count") or 0),
                ),
            )
            for i in shadow_indexes:
                if i != best:
                    rows[i]["same_game_exposure_block"] = True
                    rows[i]["shadow_decision"] = (
                        "PASS_SAME_GAME_EXPOSURE"
                    )

    return rows


def main():
    # One immutable view of the NBA result evidence for this validation run.
    # Rewrites of identical data do not invalidate model proof; material
    # changes are detected using a canonical source fingerprint.
    nba_input_digest = nba_grade_digest(HISTORY_FILES["NBA"])
    validations = {}
    models = {}

    for sport in SPORTS:
        for market in MARKETS:
            lane_key = f"{sport}_{market}"
            frame = build_history(sport, market)
            proof_frames = partition_proof_frames(frame)
            if not proof_frames:
                unknown_key = proof_lane_key(
                    sport,
                    market,
                    "UNKNOWN",
                )
                proof_frames = {unknown_key: frame}

            for proof_key, proof_frame in proof_frames.items():
                regimes = sorted({
                    clean(value).upper()
                    for value in (
                        proof_frame.get(
                            "competition_regime",
                            pd.Series(dtype=str),
                        )
                    )
                    if clean(value)
                })
                competition_regime = (
                    regimes[0] if len(regimes) == 1
                    else "UNKNOWN"
                )
                validation = walk_forward(proof_frame)
                validations[proof_key] = {
                    "sport": sport,
                    "market": market,
                    "lane_key": lane_key,
                    "proof_lane_key": proof_key,
                    "competition_regime": competition_regime,
                    "proof_version": proof_version(
                        MODEL_VERSION,
                        sport,
                        competition_regime,
                    ),
                    **validation,
                }
                if validation.get("status") == "READY":
                    model = fit_final(proof_frame, validation)
                else:
                    model = {
                        "trained_at": now_iso(),
                        "model_version": MODEL_VERSION,
                        "history_n": int(len(proof_frame)),
                        "independent_blocks": (
                            int(proof_frame["block_key"].nunique())
                            if not proof_frame.empty else 0
                        ),
                        "coefficients": {},
                        "deployment_probability_source": (
                            "MARKET_REFERENCE_INSUFFICIENT_HISTORY"
                        ),
                        "historical_edge_confidence": (
                            "INSUFFICIENT_HISTORY"
                        ),
                        "selection_rule_status": (
                            "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY"
                        ),
                        "hulk_score_adds_out_of_sample_value": False,
                        "hulk_score_confidence_supported": False,
                        "old_score_status": "UNTRAINED",
                        "old_score_coefficient": None,
                        "automatic_live_change": False,
                    }
                models[proof_key] = {
                    "sport": sport,
                    "market": market,
                    "lane_key": lane_key,
                    "proof_lane_key": proof_key,
                    "competition_regime": competition_regime,
                    "proof_version": proof_version(
                        MODEL_VERSION,
                        sport,
                        competition_regime,
                    ),
                    **model,
                }

    current_rows = build_current(models, validations)
    by_proof_lane = {}
    proof_keys = set(validations)
    proof_keys.update(
        clean(row.get("proof_lane_key"))
        for row in current_rows
        if clean(row.get("proof_lane_key"))
    )
    for proof_key in sorted(proof_keys):
        proof_rows = [
            r for r in current_rows
            if r.get("proof_lane_key") == proof_key
        ]
        model = models.get(proof_key, {})
        current_example = proof_rows[0] if proof_rows else {}
        by_proof_lane[proof_key] = {
            "lane_key": (
                model.get("lane_key")
                or current_example.get("lane_key")
            ),
            "competition_regime": (
                model.get("competition_regime")
                or current_example.get("competition_regime")
            ),
            "proof_version": (
                model.get("proof_version")
                or current_example.get("proof_version")
            ),
            "candidates": len(proof_rows),
            "shadow_plays": sum(
                r["shadow_decision"] == "SHADOW_PLAY"
                for r in proof_rows
            ),
            "passes": sum(
                r["shadow_decision"] != "SHADOW_PLAY"
                for r in proof_rows
            ),
            "history_n": int(model.get("history_n") or 0),
            "independent_blocks": int(
                model.get("independent_blocks") or 0
            ),
            "probability_source": (
                model.get("deployment_probability_source")
                or current_example.get("probability_source")
            ),
            "historical_edge_confidence": (
                model.get("historical_edge_confidence")
                or current_example.get("historical_edge_confidence")
            ),
            "selection_rule_status": (
                model.get("selection_rule_status")
                or current_example.get("selection_rule_status")
            ),
        }

    by_lane = {}
    for sport in SPORTS:
        for market in MARKETS:
            lane_key = f"{sport}_{market}"
            lane_rows = [
                r for r in current_rows
                if r["lane_key"] == lane_key
            ]
            proof_models = [
                model for model in models.values()
                if model.get("lane_key") == lane_key
            ]
            probability_sources = {
                model.get("deployment_probability_source")
                for model in proof_models
                if model.get("deployment_probability_source")
            }
            confidence_states = {
                model.get("historical_edge_confidence")
                for model in proof_models
                if model.get("historical_edge_confidence")
            }
            rule_states = {
                model.get("selection_rule_status")
                for model in proof_models
                if model.get("selection_rule_status")
            }
            by_lane[lane_key] = {
                "candidates": len(lane_rows),
                "shadow_plays": sum(
                    r["shadow_decision"] == "SHADOW_PLAY"
                    for r in lane_rows
                ),
                "passes": sum(
                    r["shadow_decision"] != "SHADOW_PLAY"
                    for r in lane_rows
                ),
                "history_n": sum(
                    int(model.get("history_n") or 0)
                    for model in proof_models
                ),
                "independent_blocks": sum(
                    int(model.get("independent_blocks") or 0)
                    for model in proof_models
                ),
                "probability_source": (
                    next(iter(probability_sources))
                    if len(probability_sources) == 1
                    else "MULTIPLE_REGIME_PROOF"
                    if probability_sources
                    else None
                ),
                "historical_edge_confidence": (
                    next(iter(confidence_states))
                    if len(confidence_states) == 1
                    else "MULTIPLE_REGIME_PROOF"
                    if confidence_states
                    else None
                ),
                "selection_rule_status": (
                    next(iter(rule_states))
                    if len(rule_states) == 1
                    else "MULTIPLE_REGIME_PROOF"
                    if rule_states
                    else None
                ),
            }

    if nba_grade_digest(HISTORY_FILES["NBA"]) != nba_input_digest:
        raise RuntimeError("NBA graded history changed during proof build; retry")

    validation_payload = {
        "generated_at": now_iso(),
        "source_fingerprints": {
            "nba_game_grades_sha256": nba_input_digest,
        },
        "model_version": MODEL_VERSION,
        "status": "READY",
        "method": (
            "SPORT_AND_MARKET_SPECIFIC_BLOCKED_"
            "ROLLING_ORIGIN_WALK_FORWARD"
        ),
        "lanes": validations,
        "rules": [
            "Moneyline, spread and total are separate model lanes inside each sport.",
            "Training folds are split by whole games so the same game cannot leak between train and test.",
            "Training is block-balanced so a game with many alternate lines cannot dominate model fitting.",
            "A HULK model must beat both fair/reference market and calibrated market out of sample.",
            "Paired game-block confidence must support the improvement before historical edge is called proven.",
            "No model or lane changes live recommendations automatically.",
        ],
    }
    model_payload = {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "status": "READY",
        "models": models,
    }
    current_payload = {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "status": "READY",
        "mode": "SHADOW_ONLY",
        "summary": {
            "candidates": len(current_rows),
            "shadow_plays": sum(
                r["shadow_decision"] == "SHADOW_PLAY"
                for r in current_rows
            ),
            "passes": sum(
                r["shadow_decision"] != "SHADOW_PLAY"
                for r in current_rows
            ),
            "opposite_side_conflicts": sum(
                bool(r.get("opposite_side_conflict"))
                for r in current_rows
            ),
            "duplicate_line_variants": sum(
                bool(r.get("duplicate_line_variant"))
                for r in current_rows
            ),
            "same_game_exposure_blocks": sum(
                bool(r.get("same_game_exposure_block"))
                for r in current_rows
            ),
        },
        "by_lane": by_lane,
        "by_proof_lane": by_proof_lane,
        "picks": current_rows,
        "rules": [
            "No point spread or total number can enter odds math; American price must be valid and at least plus/minus 100.",
            "Opposite sides of the same exact market cannot both become SHADOW_PLAY.",
            "Only one alternate line per game/market/side can survive shadow selection.",
            "At most one SHADOW_PLAY per game survives the portfolio exposure gate.",
            "Lanes without enough sport-and-market-specific history remain market-reference-only.",
        ],
    }

    outputs = [
        (VALIDATION_OUT, validation_payload),
        (MODEL_OUT, model_payload),
        (CURRENT_OUT, current_payload),
        (
            PUBLIC / "betting_v2_all_markets_validation.json",
            validation_payload,
        ),
        (
            PUBLIC / "betting_v2_all_markets_models.json",
            model_payload,
        ),
        (
            PUBLIC / "betting_v2_all_markets_current.json",
            current_payload,
        ),
    ]
    for path, payload in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))
    if DIST.exists():
        (
            DIST / "betting_v2_all_markets_validation.json"
        ).write_text(json.dumps(validation_payload, indent=2))
        (
            DIST / "betting_v2_all_markets_models.json"
        ).write_text(json.dumps(model_payload, indent=2))
        (
            DIST / "betting_v2_all_markets_current.json"
        ).write_text(json.dumps(current_payload, indent=2))

    print(json.dumps({
        "status": "READY",
        "summary": current_payload["summary"],
        "active_lanes": {
            key: value
            for key, value in by_lane.items()
            if value["history_n"] or value["candidates"]
        },
    }, indent=2))


if __name__ == "__main__":
    main()
