#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .mlb_forward_capture_identity import frozen_mlb_identity
except ImportError:
    from mlb_forward_capture_identity import frozen_mlb_identity

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

MODEL_OUT = OUT_DIR / "PROP_V2_MODELS.json"
VALIDATION_OUT = OUT_DIR / "PROP_V2_VALIDATION.json"
CURRENT_OUT = OUT_DIR / "PROP_V2_CURRENT.json"
DEVIG_OUT = OUT_DIR / "PROP_V2_DEVIG.json"
SEGMENT_OUT = OUT_DIR / "PROP_V2_MARKET_SEGMENTS.json"
MODEL_VERSION = "PROP_V2_PHASE4_SUBTYPE_VETO_2026_10_05"
_DEVIG_CACHE = None
_SEGMENT_CACHE = None

QUALIFIED_CURRENT = {
    "QUALIFIED_RESEARCH",
    "STRONG_RESEARCH",
    "HIGH_JUICE_WATCH",
    "HIGH_JUICE",
    "EARLY_MARKET_WATCH",
}

LANES = {
    "NFL_PRIZEPICKS": {
        "sport": "NFL",
        "lane": "PRIZEPICKS",
        "history": ROOT / "nfl_live" / "decision" / "history" / "NFL_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nfl_live" / "decision" / "NFL_PRIZEPICKS_DECISIONS.csv",
        "score_col": "hulk_prop_score",
        "price_col": None,
        "book_prob_cols": ["book_probability_median", "book_probability"],
        "features": [
            "context_signal",
            "dfs_line_advantage",
            "book_count_norm",
            "meaningful_games_norm",
        ],
        "current_map": {
            "start": "start",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "book_count",
            "context_direction": "context_direction",
            "dfs_line_advantage": "dfs_line_advantage",
            "meaningful_completed_games": "meaningful_completed_games",
        },
    },
    "NFL_PROP": {
        "sport": "NFL",
        "lane": "PROP",
        "history": ROOT / "nfl_live" / "decision" / "history" / "NFL_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nfl_live" / "decision" / "NFL_PROP_DECISIONS.csv",
        "score_col": "hulk_prop_score",
        "price_col": "price_median",
        "book_prob_cols": ["implied_probability_median_raw", "book_probability"],
        "features": [
            "context_signal",
            "dfs_line_advantage",
            "book_count_norm",
            "meaningful_games_norm",
        ],
        "current_map": {
            "start": "start_dfs",
            "player": "player_dfs",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "book_count",
            "context_direction": "context_direction",
            "dfs_line_advantage": "dfs_line_advantage",
            "meaningful_completed_games": "meaningful_completed_games",
        },
    },
    "NBA_PROP": {
        "sport": "NBA",
        "lane": "PROP",
        "history": ROOT / "nba_live" / "decision" / "history" / "NBA_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nba_live" / "decision" / "NBA_PROP_DECISIONS.csv",
        "score_col": "evidence_score",
        "price_col": "median_price_american",
        "book_prob_cols": [],
        "features": [
            "l3_centered",
            "l5_centered",
            "l10_centered",
            "context_signal",
            "context_edge_centered",
            "sample_games_norm",
            "minutes_norm",
            "book_count_norm",
        ],
        "current_map": {
            "start": "start_dt",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "book_count",
            "context_direction": "context_direction",
            "context_edge": "context_edge",
            "sample_games": "sample_games",
            "meaningful_games": "meaningful_games",
            "l3_hit_rate": "l3_hit_rate",
            "l5_hit_rate": "l5_hit_rate",
            "l10_hit_rate": "l10_hit_rate",
            "minutes_l5_avg": "minutes_l5_avg",
        },
    },
    "NBA_PRIZEPICKS": {
        "sport": "NBA",
        "lane": "PRIZEPICKS",
        "history": ROOT / "nba_live" / "decision" / "history" / "NBA_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nba_live" / "decision" / "NBA_PRIZEPICKS_DECISIONS.csv",
        "reference_current": ROOT / "nba_live" / "decision" / "NBA_PROP_DECISIONS.csv",
        "reference_price_col": "median_price_american",
        "score_col": "evidence_score",
        "price_col": None,
        "book_prob_cols": [],
        "features": [
            "l3_centered",
            "l5_centered",
            "l10_centered",
            "context_signal",
            "context_edge_centered",
            "sample_games_norm",
            "minutes_norm",
        ],
        "current_map": {
            "start": "start_dt",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "sportsbook_book_count",
            "context_direction": "context_direction",
            "context_edge": "context_edge",
            "sample_games": "sample_games",
            "meaningful_games": "meaningful_games",
            "l3_hit_rate": "l3_hit_rate",
            "l5_hit_rate": "l5_hit_rate",
            "l10_hit_rate": "l10_hit_rate",
            "minutes_l5_avg": "minutes_l5_avg",
        },
    },
    "NHL_PROP": {
        "sport": "NHL",
        "lane": "PROP",
        "history": ROOT / "nhl_live" / "decision" / "history" / "NHL_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nhl_live" / "decision" / "NHL_PROP_DECISIONS.csv",
        "score_col": "evidence_score",
        "price_cols": ["best_executable_price_american", "median_price_american"],
        "price_col": "median_price_american",
        "book_prob_cols": [],
        "direct_fair_prob_col": "market_fair_probability",
        "direct_paired_books_col": "paired_book_count",
        "features": [
            "l3_centered",
            "l5_centered",
            "l10_centered",
            "context_signal",
            "context_edge_centered",
            "sample_games_norm",
            "toi_norm",
            "book_count_norm",
        ],
        "current_map": {
            "start": "start_dt",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "book_count",
            "context_direction": "context_direction",
            "context_edge": "context_edge",
            "sample_games": "sample_games",
            "meaningful_games": "meaningful_games",
            "l3_hit_rate": "l3_hit_rate",
            "l5_hit_rate": "l5_hit_rate",
            "l10_hit_rate": "l10_hit_rate",
            "toi_l5_avg": "toi_l5_avg",
        },
    },
    "NHL_PRIZEPICKS": {
        "sport": "NHL",
        "lane": "PRIZEPICKS",
        "history": ROOT / "nhl_live" / "decision" / "history" / "NHL_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "nhl_live" / "decision" / "NHL_PRIZEPICKS_DECISIONS.csv",
        "reference_current": ROOT / "nhl_live" / "decision" / "NHL_PROP_DECISIONS.csv",
        "reference_price_cols": ["best_executable_price_american", "median_price_american"],
        "reference_price_col": "median_price_american",
        "score_col": "evidence_score",
        "price_cols": ["sportsbook_best_executable_price_american", "sportsbook_median_price_american"],
        "price_col": "sportsbook_median_price_american",
        "book_prob_cols": [],
        "direct_fair_prob_col": "sportsbook_fair_probability",
        "direct_paired_books_col": "sportsbook_paired_book_count",
        "features": [
            "l3_centered",
            "l5_centered",
            "l10_centered",
            "context_signal",
            "context_edge_centered",
            "sample_games_norm",
            "toi_norm",
        ],
        "current_map": {
            "start": "start_dt",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "sportsbook_book_count",
            "context_direction": "context_direction",
            "context_edge": "context_edge",
            "sample_games": "sample_games",
            "meaningful_games": "meaningful_games",
            "l3_hit_rate": "l3_hit_rate",
            "l5_hit_rate": "l5_hit_rate",
            "l10_hit_rate": "l10_hit_rate",
            "toi_l5_avg": "toi_l5_avg",
        },
    },
    "MLB_PROP": {
        "sport": "MLB",
        "lane": "PROP",
        "history": ROOT / "mlb_live" / "decision" / "history" / "MLB_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "mlb_live" / "decision" / "MLB_PROP_DECISIONS.csv",
        "score_col": "evidence_score",
        "price_col": "median_price_american",
        "book_prob_cols": [],
        "features": [
            "recent_edge",
            "season_edge",
            "normalized_recent_edge",
            "book_count_norm",
            "recent_games_norm",
            "season_games_norm",
        ],
        "current_map": {
            "start": "start",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "sportsbook_count",
            "recent_edge": "recent_edge",
            "season_edge": "season_edge",
            "normalized_recent_edge": "normalized_recent_edge",
            "recent_games": "recent_games",
            "season_games": "season_games",
        },
    },
    "MLB_PRIZEPICKS": {
        "sport": "MLB",
        "lane": "PRIZEPICKS",
        "history": ROOT / "mlb_live" / "decision" / "history" / "MLB_GRADED_RECOMMENDATIONS.csv",
        "current": ROOT / "mlb_live" / "decision" / "MLB_PRIZEPICKS_DECISIONS.csv",
        "score_col": "evidence_score",
        "price_col": "median_price_american",
        "book_prob_cols": [],
        "features": [
            "recent_edge",
            "season_edge",
            "normalized_recent_edge",
            "book_count_norm",
            "recent_games_norm",
            "season_games_norm",
        ],
        "current_map": {
            "start": "start",
            "player": "player",
            "market": "market_subtype",
            "side": "side",
            "line": "line",
            "decision": "decision",
            "book_count": "sportsbook_count",
            "recent_edge": "recent_edge",
            "season_edge": "season_edge",
            "normalized_recent_edge": "normalized_recent_edge",
            "recent_games": "recent_games",
            "season_games": "season_games",
        },
    },
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def text_value(value):
    return str(value or "").strip()


def parse_payload(value):
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


def devig_data():
    global _DEVIG_CACHE
    if _DEVIG_CACHE is None:
        try:
            _DEVIG_CACHE = json.loads(DEVIG_OUT.read_text())
        except Exception:
            _DEVIG_CACHE = {"history": {}, "current": {}, "coverage": {}}
    return _DEVIG_CACHE


def segment_data():
    global _SEGMENT_CACHE
    if _SEGMENT_CACHE is None:
        try:
            _SEGMENT_CACHE = json.loads(
                SEGMENT_OUT.read_text()
            )
        except Exception:
            _SEGMENT_CACHE = {
                "lanes": {}
            }
    return _SEGMENT_CACHE


def devig_identity(event_id, player, market, line, side):
    line = num(line)
    if line is None:
        return ""
    player = "".join(ch for ch in text_value(player).lower() if ch.isalnum())
    return "|".join([
        text_value(event_id),
        player,
        text_value(market).upper(),
        f"{line:.4f}",
        text_value(side).upper(),
    ])


def historical_devig(cfg, recommendation_key):
    record = (
        devig_data().get("history", {})
        .get(cfg["sport"], {})
        .get(text_value(recommendation_key), {})
    )
    p = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    if p is None or not (0 < p < 1) or books < 2:
        return None, books
    return p, books


def current_devig(cfg, row):
    minimum_books = int(
        num(
            devig_data().get(
                "minimum_paired_books_for_model"
            )
        )
        or 2
    )

    direct_probability_col = cfg.get(
        "direct_fair_prob_col"
    )
    direct_books_col = cfg.get(
        "direct_paired_books_col"
    )

    if (
        direct_probability_col
        and direct_probability_col in row.index
    ):
        direct_p = num(
            row.get(
                direct_probability_col
            )
        )
        direct_books = int(
            num(
                row.get(
                    direct_books_col
                )
            )
            or 0
        ) if direct_books_col else 0

        if (
            direct_p is not None
            and 0 < direct_p < 1
            and direct_books >= minimum_books
        ):
            return direct_p, direct_books

    mapping = cfg.get("current_map", {})
    key = devig_identity(
        row.get("event_id"),
        row.get(mapping.get("player")) if mapping.get("player") else row.get("player"),
        row.get(mapping.get("market")) if mapping.get("market") else row.get("market_subtype"),
        row.get(mapping.get("line")) if mapping.get("line") else row.get("line"),
        row.get(mapping.get("side")) if mapping.get("side") else row.get("side"),
    )
    record = devig_data().get("current", {}).get(cfg["sport"], {}).get(key, {})
    p = num(record.get("fair_probability"))
    books = int(num(record.get("paired_books")) or 0)
    if p is None or not (0 < p < 1) or books < minimum_books:
        return None, books
    return p, books


def american_implied(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return 100.0 / (odds + 100.0) if odds > 0 else abs(odds) / (abs(odds) + 100.0)


def american_profit(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def logit(p):
    p = min(0.995, max(0.005, float(p)))
    return math.log(p / (1.0 - p))


def sigmoid_array(z):
    z = np.clip(z, -35, 35)
    return 1.0 / (1.0 + np.exp(-z))


def fit_logistic(X, y, l2=4.0, max_iter=100):
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    beta = np.zeros(X.shape[1], dtype=float)
    m = min(0.99, max(0.01, float(np.mean(y))))
    beta[0] = math.log(m / (1.0 - m))
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
        nxt = beta - step
        if np.max(np.abs(nxt - beta)) < 1e-8:
            beta = nxt
            break
        beta = nxt
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
        mask = (p >= cuts[i]) & (p <= cuts[i + 1] if i == bins - 1 else p < cuts[i + 1])
        n = int(mask.sum())
        if not n:
            continue
        total += (n / len(y)) * abs(float(p[mask].mean()) - float(y[mask].mean()))
    return float(total)


def evaluate(y, p):
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
    n_blocks = len(keys)

    result = {
        "n": int(len(y)),
        "independent_blocks": n_blocks,
        "brier_advantage": round(float(np.mean(brier_adv)), 5),
        "logloss_advantage": round(float(np.mean(logloss_adv)), 5),
        "brier_lcb90": None,
        "logloss_lcb90": None,
        "brier_lcb95": None,
        "logloss_lcb95": None,
        "brier_ci95_low": None,
        "logloss_ci95_low": None,
        "minimum_independent_blocks_for_support": 30,
        "confidence_supported": False,
    }
    if n_blocks < 2:
        return result

    rng = np.random.default_rng(seed)
    boot_brier = []
    boot_logloss = []
    for _ in range(5000):
        sampled = rng.choice(keys, size=n_blocks, replace=True)
        indexes = np.concatenate([np.asarray(groups[str(k)], dtype=int) for k in sampled])
        boot_brier.append(float(np.mean(brier_adv[indexes])))
        boot_logloss.append(float(np.mean(logloss_adv[indexes])))

    # One-sided lower confidence bounds plus the lower edge of a two-sided 95% CI.
    result["brier_lcb90"] = round(float(np.percentile(boot_brier, 10)), 5)
    result["logloss_lcb90"] = round(float(np.percentile(boot_logloss, 10)), 5)
    result["brier_lcb95"] = round(float(np.percentile(boot_brier, 5)), 5)
    result["logloss_lcb95"] = round(float(np.percentile(boot_logloss, 5)), 5)
    result["brier_ci95_low"] = round(float(np.percentile(boot_brier, 2.5)), 5)
    result["logloss_ci95_low"] = round(float(np.percentile(boot_logloss, 2.5)), 5)
    result["confidence_supported"] = bool(
        n_blocks >= 30
        and result["brier_ci95_low"] > 0
        and result["logloss_ci95_low"] > 0
    )
    return result


def context_signal(value):
    value = text_value(value).upper()
    if value == "SUPPORT":
        return 1.0
    if value == "CONTRADICT":
        return -1.0
    return 0.0


def scaled_log(value, divisor):
    value = num(value)
    if value is None or value < 0:
        return 0.0
    return min(2.0, math.log1p(value) / divisor)


def history_value(row, payload, key):
    direct = row.get(key)
    if direct is not None and not (isinstance(direct, float) and math.isnan(direct)):
        return direct
    return payload.get(key)


def extract_market_probability(row, payload, cfg):
    for key in cfg.get("book_prob_cols", []):
        value = num(history_value(row, payload, key))
        if value is not None:
            return value / 100.0 if value > 1 else value
    price = num(history_value(row, payload, cfg.get("price_col"))) if cfg.get("price_col") else None
    if price is None:
        for key in ["median_price_american", "sportsbook_median_price_american"]:
            price = num(payload.get(key))
            if price is not None:
                break
    return american_implied(price)


def feature_values(source, score, market_prob):
    return {
        "market_logit": logit(market_prob),
        "score_z": ((score or 80.0) - 80.0) / 10.0,
        "context_signal": context_signal(source.get("context_direction")),
        "context_edge_centered": (num(source.get("context_edge")) or 0.5) - 0.5,
        "l3_centered": ((num(source.get("l3_hit_rate")) or 0.5) - 0.5) * 2.0,
        "l5_centered": ((num(source.get("l5_hit_rate")) or 0.5) - 0.5) * 2.0,
        "l10_centered": ((num(source.get("l10_hit_rate")) or 0.5) - 0.5) * 2.0,
        "toi_norm": ((num(source.get("toi_l5_avg")) or 18.0) - 18.0) / 10.0,
        "minutes_norm": ((num(source.get("minutes_l5_avg")) or 28.0) - 28.0) / 12.0,
        "sample_games_norm": scaled_log(source.get("sample_games"), 4.5),
        "meaningful_games_norm": scaled_log(source.get("meaningful_games") or source.get("meaningful_completed_games"), 4.0),
        "book_count_norm": ((num(source.get("book_count")) or num(source.get("sportsbook_count")) or 3.0) - 3.0) / 3.0,
        "dfs_line_advantage": num(source.get("dfs_line_advantage")) or 0.0,
        "recent_edge": num(source.get("recent_edge")) or 0.0,
        "season_edge": num(source.get("season_edge")) or 0.0,
        "normalized_recent_edge": num(source.get("normalized_recent_edge")) or 0.0,
        "recent_games_norm": scaled_log(source.get("recent_games"), 3.0),
        "season_games_norm": scaled_log(source.get("season_games"), 5.0),
    }


def build_history(cfg):
    path = cfg["history"]
    if not path.exists():
        return pd.DataFrame()
    d = pd.read_csv(path, low_memory=False)
    if d.empty or "lane" not in d.columns:
        return pd.DataFrame()
    d = d[
        d["lane"].astype(str).str.upper().eq(cfg["lane"])
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    if d.empty:
        return d

    d["_snapshot"] = pd.to_datetime(d.get("snapshot_at"), errors="coerce", utc=True)
    d = d.sort_values("_snapshot")
    if "recommendation_key" in d.columns:
        d = d.drop_duplicates("recommendation_key", keep="first")

    rows = []
    for _, row in d.iterrows():
        payload = parse_payload(row.get("payload_json"))
        start = parse_dt(row.get("start") or payload.get("start") or payload.get("start_dt"))
        snapshot = row.get("_snapshot")
        if start is not None and pd.notna(snapshot) and snapshot >= start:
            continue

        score = num(row.get("score"))
        market_raw_prob = extract_market_probability(row, payload, cfg)
        recommendation_key = text_value(row.get("recommendation_key"))
        fair_prob, fair_books = historical_devig(cfg, recommendation_key)
        market_prob = fair_prob if fair_prob is not None else market_raw_prob
        if score is None or market_prob is None:
            continue

        source = dict(payload)
        for key in [
            "context_direction", "context_edge", "l3_hit_rate", "l5_hit_rate",
            "l10_hit_rate", "toi_l5_avg", "minutes_l5_avg", "sample_games", "meaningful_games",
            "meaningful_completed_games", "book_count", "sportsbook_count",
            "dfs_line_advantage", "recent_edge", "season_edge",
            "normalized_recent_edge", "recent_games", "season_games",
        ]:
            if row.get(key) is not None and not (isinstance(row.get(key), float) and math.isnan(row.get(key))):
                source[key] = row.get(key)

        features = feature_values(source, score, market_prob)
        game_key = text_value(history_value(row, payload, "game_key"))
        event_id = text_value(history_value(row, payload, "event_id"))
        recommendation_key = recommendation_key or text_value(history_value(row, payload, "recommendation_key"))
        if game_key:
            block_key = f"{cfg['sport']}|{cfg['lane']}|game|{game_key}"
        elif event_id:
            block_key = f"{cfg['sport']}|{cfg['lane']}|event|{event_id}"
        elif start is not None:
            block_key = f"{cfg['sport']}|{cfg['lane']}|date|{start.date().isoformat()}"
        else:
            block_key = f"{cfg['sport']}|{cfg['lane']}|row|{recommendation_key or len(rows)}"

        rows.append({
            "outcome": 1 if text_value(row.get("grade")).upper() == "WIN" else 0,
            "market_subtype": text_value(
                history_value(row, payload, "market_subtype")
                or history_value(row, payload, "market")
            ).upper(),
            "market_probability": market_prob,
            "market_raw_probability": market_raw_prob if market_raw_prob is not None else market_prob,
            "devig_probability": fair_prob,
            "devig_paired_books": fair_books,
            "market_reference_type": "DEVIG_FAIR" if fair_prob is not None else "RAW_FALLBACK",
            "score": score,
            "time": snapshot if pd.notna(snapshot) else pd.Timestamp("1970-01-01", tz="UTC"),
            "block_key": block_key,
            **features,
        })

    return pd.DataFrame(rows).sort_values("time").reset_index(drop=True) if rows else pd.DataFrame()


def matrix(frame, feature_names, include_score=False):
    cols = [np.ones(len(frame)), frame["market_logit"].astype(float).to_numpy()]
    for name in feature_names:
        cols.append(frame[name].astype(float).fillna(0.0).to_numpy())
    if include_score:
        cols.append(frame["score_z"].astype(float).to_numpy())
    return np.column_stack(cols)


def walk_forward(frame, cfg):
    n = len(frame)
    if n < 40:
        return {"status": "INSUFFICIENT_HISTORY", "history_n": n}

    min_train = max(30, int(math.floor(n * 0.50)))
    step = max(8, int(math.ceil(n * 0.10)))
    feature_names = cfg["features"]
    records = []

    for test_start in range(min_train, n, step):
        test_end = min(n, test_start + step)
        train = frame.iloc[:test_start]
        test = frame.iloc[test_start:test_end]
        if test.empty:
            continue

        y_train = train["outcome"].astype(int).to_numpy()
        y_test = test["outcome"].astype(int).to_numpy()

        X_cal_train = matrix(train, [])
        X_cal_test = matrix(test, [])
        X_core_train = matrix(train, feature_names)
        X_core_test = matrix(test, feature_names)
        X_score_train = matrix(train, feature_names, include_score=True)
        X_score_test = matrix(test, feature_names, include_score=True)

        beta_cal = fit_logistic(X_cal_train, y_train, l2=3.0)
        beta_core = fit_logistic(X_core_train, y_train, l2=5.0)
        beta_score = fit_logistic(X_score_train, y_train, l2=5.0)

        records.append({
            "y": y_test,
            "block": test["block_key"].astype(str).to_numpy(),
            "market_raw": test["market_raw_probability"].astype(float).to_numpy(),
            "market_reference": test["market_probability"].astype(float).to_numpy(),
            "market_calibrated": predict(beta_cal, X_cal_test),
            "core_model": predict(beta_core, X_core_test),
            "core_plus_old_score": predict(beta_score, X_score_test),
        })

    if not records:
        return {"status": "NO_FOLDS", "history_n": n}

    y = np.concatenate([r["y"] for r in records])
    predictions = {
        key: np.concatenate([r[key] for r in records])
        for key in ["market_raw", "market_reference", "market_calibrated", "core_model", "core_plus_old_score"]
    }
    metrics = {key: evaluate(y, pred) for key, pred in predictions.items()}
    blocks = np.concatenate([r["block"] for r in records])
    comparisons = {
        "core_vs_reference": paired_block_comparison(
            y, predictions["core_model"], predictions["market_reference"], blocks, 1101
        ),
        "core_vs_calibrated": paired_block_comparison(
            y, predictions["core_model"], predictions["market_calibrated"], blocks, 1102
        ),
        "reference_vs_raw": paired_block_comparison(
            y, predictions["market_reference"], predictions["market_raw"], blocks, 1103
        ),
        "market_calibrated_vs_reference": paired_block_comparison(
            y, predictions["market_calibrated"], predictions["market_reference"], blocks, 1104
        ),
        "old_score_vs_core": paired_block_comparison(
            y, predictions["core_plus_old_score"], predictions["core_model"], blocks, 1105
        ),
    }

    raw = metrics["market_raw"]
    reference = metrics["market_reference"]
    core = metrics["core_model"]
    score = metrics["core_plus_old_score"]
    cal = metrics["market_calibrated"]

    core_beats_reference = (
        core["brier"] <= reference["brier"] - 0.001
        and core["log_loss"] <= reference["log_loss"] - 0.001
    )
    cal_beats_reference = (
        cal["brier"] <= reference["brier"] - 0.001
        and cal["log_loss"] <= reference["log_loss"] - 0.001
    )
    core_beats_calibrated = (
        core["brier"] <= cal["brier"] - 0.0005
        and core["log_loss"] <= cal["log_loss"] - 0.0005
    )
    score_beats_core = (
        score["brier"] <= core["brier"] - 0.0005
        and score["log_loss"] <= core["log_loss"] - 0.0005
    )

    full_core = matrix(frame, feature_names)
    full_score = matrix(frame, feature_names, include_score=True)
    y_full = frame["outcome"].astype(int).to_numpy()
    beta_core = fit_logistic(full_core, y_full, l2=5.0)
    beta_score = fit_logistic(full_score, y_full, l2=5.0)
    old_score_coef = float(beta_score[-1])

    if core_beats_reference and core_beats_calibrated:
        source = "LANE_CORE_MODEL"
    elif cal_beats_reference:
        source = "MARKET_CALIBRATED"
    else:
        source = "MARKET_REFERENCE"

    core_confidence_supported = bool(
        comparisons["core_vs_reference"]["confidence_supported"]
        and comparisons["core_vs_calibrated"]["confidence_supported"]
    )
    calibration_confidence_supported = bool(
        comparisons["market_calibrated_vs_reference"]["confidence_supported"]
    )
    old_score_confidence_supported = bool(
        comparisons["old_score_vs_core"]["confidence_supported"]
    )

    old_score_status = (
        "NEGATIVE_ORDERING_REJECTED"
        if old_score_coef < -0.02
        else "POSITIVE_BUT_NO_INCREMENTAL_VALUE"
        if old_score_coef > 0.02 and not score_beats_core
        else "POSITIVE_INCREMENTAL_VALUE"
        if old_score_coef > 0.02 and score_beats_core and old_score_confidence_supported
        else "POSITIVE_BUT_UNCERTAIN_INCREMENTAL_VALUE"
        if old_score_coef > 0.02 and score_beats_core
        else "FLAT_OR_UNPROVEN"
    )

    # We do not deploy the old score into probability if its learned direction is negative.
    if source == "LANE_CORE_MODEL" and old_score_status == "POSITIVE_INCREMENTAL_VALUE":
        source = "LANE_CORE_PLUS_OLD_SCORE"

    if source == "LANE_CORE_PLUS_OLD_SCORE":
        historical_edge_confidence = (
            "SUPPORTED"
            if core_confidence_supported and old_score_confidence_supported
            else "PROMISING_BUT_UNCERTAIN"
        )
    elif source == "LANE_CORE_MODEL":
        historical_edge_confidence = (
            "SUPPORTED" if core_confidence_supported else "PROMISING_BUT_UNCERTAIN"
        )
    elif source == "MARKET_CALIBRATED":
        historical_edge_confidence = (
            "CALIBRATION_SUPPORTED"
            if calibration_confidence_supported
            else "CALIBRATION_MEAN_ONLY"
        )
    else:
        historical_edge_confidence = "NO_INDEPENDENT_EDGE"

    return {
        "status": "READY",
        "history_n": n,
        "walk_forward_n": int(len(y)),
        "folds": len(records),
        "feature_names": feature_names,
        "metrics": metrics,
        "paired_comparisons": comparisons,
        "devig_history_n": int(frame["devig_probability"].notna().sum()) if "devig_probability" in frame else 0,
        "devig_history_pct": round(100.0 * float(frame["devig_probability"].notna().mean()), 1) if "devig_probability" in frame and len(frame) else 0.0,
        "core_beats_reference_market": bool(core_beats_reference),
        "core_beats_calibrated_market": bool(core_beats_calibrated),
        "core_confidence_supported": core_confidence_supported,
        "market_calibration_beats_reference": bool(cal_beats_reference),
        "calibration_confidence_supported": calibration_confidence_supported,
        "old_score_beats_core": bool(score_beats_core),
        "old_score_confidence_supported": old_score_confidence_supported,
        "old_score_coefficient": round(old_score_coef, 5),
        "old_score_status": old_score_status,
        "deployment_probability_source": source,
        "historical_edge_confidence": historical_edge_confidence,
        "selection_rule_status": (
            "FORWARD_VALIDATION_REQUIRED"
            if source.startswith("LANE_CORE") and historical_edge_confidence == "SUPPORTED"
            else "HISTORICAL_SIGNAL_UNCERTAIN_RESEARCH_ONLY"
            if source.startswith("LANE_CORE")
            else "CALIBRATION_ONLY_NO_INDEPENDENT_EDGE"
            if source == "MARKET_CALIBRATED"
            else "NO_INDEPENDENT_MODEL_EDGE"
        ),
        "coefficients": {
            "market_calibrated": [round(float(v), 8) for v in fit_logistic(matrix(frame, []), y_full, l2=3.0)],
            "core_model": [round(float(v), 8) for v in beta_core],
            "core_plus_old_score": [round(float(v), 8) for v in beta_score],
        },
    }


def current_source_dict(row, cfg):
    source = {}
    mapping = cfg["current_map"]
    for logical, col in mapping.items():
        if col and col in row.index:
            source[logical] = row.get(col)
    return source


def normalized_key(value):
    return "".join(ch for ch in text_value(value).lower() if ch.isalnum())


def current_identity_key(row):
    event_id = text_value(row.get("event_id"))
    player_key = normalized_key(
        row.get("player_key") or row.get("player") or row.get("player_dfs")
    )
    market = text_value(row.get("market_subtype") or row.get("market")).upper()
    side = text_value(row.get("side")).upper()
    line = num(row.get("line"))
    if not event_id or not player_key or not market or not side or line is None:
        return ""
    return f"{event_id}|{player_key}|{market}|{side}|{line:.4f}"


def build_reference_price_map(cfg):
    path = cfg.get("reference_current")
    price_cols = list(cfg.get("reference_price_cols") or [])
    fallback_col = cfg.get("reference_price_col")
    if fallback_col and fallback_col not in price_cols:
        price_cols.append(fallback_col)
    if not path or not price_cols or not path.exists():
        return {}
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return {}
    out = {}
    for _, row in d.iterrows():
        key = current_identity_key(row)
        if not key:
            continue
        for col in price_cols:
            if col not in row.index:
                continue
            price = num(row.get(col))
            if price is not None and abs(price) >= 100:
                out[key] = price
                break
    return out


def current_price(row, cfg, reference_prices=None):
    price_cols = list(cfg.get("price_cols") or [])
    fallback_col = cfg.get("price_col")
    if fallback_col and fallback_col not in price_cols:
        price_cols.append(fallback_col)
    for col in price_cols:
        if col and col in row.index:
            price = num(row.get(col))
            if price is not None and abs(price) >= 100:
                return price
    if reference_prices:
        return reference_prices.get(current_identity_key(row))
    return None


def current_market_probability(row, cfg, reference_prices=None):
    for col in cfg.get("book_prob_cols", []):
        if col in row.index:
            value = num(row.get(col))
            if value is not None:
                p = value / 100.0 if value > 1 else value
                if 0 < p < 1:
                    return p
    return american_implied(current_price(row, cfg, reference_prices))


def model_probability(validation, row_features, market_prob):
    source = validation["deployment_probability_source"]
    market_log = logit(market_prob)

    if source == "MARKET_REFERENCE":
        return market_prob
    if source == "MARKET_CALIBRATED":
        beta = validation["coefficients"]["market_calibrated"]
        X = np.array([[1.0, market_log]])
        return float(predict(beta, X)[0])

    vals = [1.0, market_log]
    for name in validation["feature_names"]:
        vals.append(float(row_features.get(name, 0.0)))
    if source == "LANE_CORE_PLUS_OLD_SCORE":
        vals.append(float(row_features.get("score_z", 0.0)))
        beta = validation["coefficients"]["core_plus_old_score"]
    else:
        beta = validation["coefficients"]["core_model"]
    return float(predict(beta, np.array([vals]))[0])


def data_quality(book_count, sample_games):
    book_count = int(num(book_count) or 0)
    sample_games = int(num(sample_games) or 0)
    if book_count >= 5 and sample_games >= 20:
        return "A"
    if book_count >= 3 and sample_games >= 10:
        return "B"
    if book_count >= 2:
        return "C"
    return "D"


def build_current_lane(lane_key, cfg, validation):
    path = cfg["current"]
    if not path.exists():
        return []

    validation_ready = validation.get("status") == "READY"
    reference_prices = build_reference_price_map(cfg)
    d = pd.read_csv(path, low_memory=False)
    rows = []
    for _, row in d.iterrows():
        mapping = cfg["current_map"]
        market_name = text_value(
            row.get(
                mapping.get(
                    "market"
                )
            )
        ).upper()
        decision = text_value(row.get(mapping["decision"])).upper()
        if decision not in QUALIFIED_CURRENT:
            continue

        start_col = mapping.get("start")
        event_start_value = row.get(start_col) if start_col else None
        event_start_dt = parse_dt(event_start_value)
        if event_start_dt is not None and event_start_dt.to_pydatetime() <= datetime.now(timezone.utc):
            continue

        market_raw_prob = current_market_probability(row, cfg, reference_prices)
        fair_prob, fair_books = current_devig(cfg, row)
        market_prob = fair_prob if fair_prob is not None else market_raw_prob
        score = num(row.get(cfg["score_col"]))
        if market_prob is None or score is None:
            continue

        source = current_source_dict(row, cfg)
        features = feature_values(source, score, market_prob)
        if validation_ready:
            p_model = model_probability(validation, features, market_prob)
        else:
            p_model = market_prob
        edge = p_model - market_prob

        chosen_metric = validation.get("metrics", {}).get(
            "core_plus_old_score"
            if validation.get("deployment_probability_source") == "LANE_CORE_PLUS_OLD_SCORE"
            else "core_model"
            if validation.get("deployment_probability_source") == "LANE_CORE_MODEL"
            else "market_calibrated"
            if validation.get("deployment_probability_source") == "MARKET_CALIBRATED"
            else "market_raw",
            {},
        )
        if validation_ready:
            buffer = max(0.03, min(0.09, float(chosen_metric.get("ece") or 0.05)))
            if validation.get("walk_forward_n", 0) < 100:
                buffer = min(0.10, buffer + 0.015)
        else:
            buffer = 0.10
        conservative_p = max(0.0, p_model - buffer)
        conservative_edge = conservative_p - market_prob

        segment_validation = (
            segment_data()
            .get(
                "lanes",
                {},
            )
            .get(
                lane_key,
                {},
            )
            .get(
                "segments",
                {},
            )
            .get(
                market_name,
                {},
            )
        )

        segment_probability = None
        segment_agreement_gap = None
        segment_source = text_value(
            segment_validation.get(
                "deployment_probability_source"
            )
        )
        segment_ready = (
            segment_validation.get(
                "status"
            ) == "READY"
        )
        segment_independent_edge = (
            segment_ready
            and segment_source.startswith(
                "LANE_CORE"
            )
        )
        agreement_probability = p_model
        agreement_conservative_p = conservative_p
        agreement_conservative_edge = conservative_edge
        segment_agreement_applied = False

        if segment_independent_edge:
            try:
                segment_probability = model_probability(
                    segment_validation,
                    features,
                    market_prob,
                )
            except Exception:
                segment_probability = None

        if (
            segment_probability is not None
            and 0 < segment_probability < 1
        ):
            # Agreement is conservative-only. It can reduce a monitor's
            # effective probability but can never increase it or shrink
            # the uncertainty buffer.
            segment_agreement_applied = True
            segment_agreement_gap = abs(
                p_model
                - segment_probability
            )
            agreement_probability = min(
                p_model,
                segment_probability,
            )
            agreement_conservative_p = max(
                0.0,
                agreement_probability
                - buffer,
            )
            agreement_conservative_edge = (
                agreement_conservative_p
                - market_prob
            )

        price = current_price(row, cfg, reference_prices)
        profit = american_profit(price)
        ev = None if profit is None else p_model * profit - (1 - p_model)
        conservative_ev = None if profit is None else conservative_p * profit - (1 - conservative_p)

        sample_games = source.get("sample_games") or source.get("meaningful_games") or source.get("meaningful_completed_games")
        quality_book_count = (
            fair_books
            if fair_prob is not None
            else int(num(source.get("book_count")) or 0)
        )
        quality = data_quality(quality_book_count, sample_games)
        devig_required_for_shadow = bool(
            text_value(validation.get("deployment_probability_source")).startswith("LANE_CORE")
            and float(validation.get("devig_history_pct") or 0.0) >= 80.0
        )

        if not validation_ready:
            shadow = "PASS_INSUFFICIENT_HISTORY"
        elif not text_value(validation.get("deployment_probability_source")).startswith("LANE_CORE"):
            shadow = "PASS_NO_PROVEN_MODEL_EDGE"
        elif devig_required_for_shadow and fair_prob is None:
            shadow = "PASS_NO_DEVIG_REFERENCE"
        elif quality not in {"A", "B"}:
            shadow = "PASS_DATA_QUALITY"
        elif (
            segment_ready
            and not segment_independent_edge
        ):
            # A subtype-specific model is stronger evidence about this
            # market than a broad lane model. If the subtype cannot beat
            # its market baseline, it vetoes the broad-lane monitor.
            shadow = "PASS_SEGMENT_NO_EDGE"
        elif (
            segment_agreement_gap is not None
            and segment_agreement_gap > 0.10
        ):
            shadow = "PASS_MODEL_DISAGREEMENT"
        elif cfg["lane"] == "PRIZEPICKS":
            # Historical confidence controls promotion, not observation.
            # Shadow Monitor exists specifically to collect independent
            # forward evidence while the historical signal is still uncertain.
            # When a subtype model exists, use the lower probability so
            # model disagreement can only downgrade a monitor.
            if (
                agreement_conservative_p >= 0.55
                and agreement_conservative_edge >= 0.02
            ):
                shadow = "SHADOW_MONITOR"
            elif validation.get("historical_edge_confidence") != "SUPPORTED":
                shadow = "PASS_HISTORICAL_CONFIDENCE"
            else:
                shadow = "PASS_LEG_EDGE"
        else:
            agreement_profit_ev = (
                None
                if profit is None
                else agreement_conservative_p
                * profit
                - (
                    1
                    - agreement_conservative_p
                )
            )
            if (
                agreement_profit_ev is not None
                and agreement_profit_ev >= 0.025
                and agreement_conservative_edge >= 0.02
            ):
                shadow = "SHADOW_MONITOR"
            elif validation.get("historical_edge_confidence") != "SUPPORTED":
                shadow = "PASS_HISTORICAL_CONFIDENCE"
            else:
                shadow = "PASS_PRICE_OR_EDGE"

        start_col = mapping.get("start")
        player_col = mapping.get("player")
        market_col = mapping.get("market")
        side_col = mapping.get("side")
        line_col = mapping.get("line")

        source_mlb_identity = (
            frozen_mlb_identity(row)
            if cfg["sport"] == "MLB" else {}
        )
        rows.append({
            **source_mlb_identity,
            "model_version": MODEL_VERSION,
            "lane_key": lane_key,
            "sport": cfg["sport"],
            "lane": cfg["lane"],
            "event_id": text_value(
                row.get("event_id")
                or row.get("event_id_dfs")
                or row.get("event_id_sportsbook")
            ),
            "game_key": text_value(row.get("game_key")),
            "player_key": text_value(row.get("player_key")),
            "player": text_value(row.get(player_col)) if player_col else "",
            "market_subtype": text_value(row.get(market_col)) if market_col else "",
            "side": text_value(row.get(side_col)).upper() if side_col else "",
            "line": num(row.get(line_col)) if line_col else None,
            "event_start": text_value(row.get(start_col)) if start_col else "",
            "old_hulk_score": score,
            "old_score_status": validation.get("old_score_status", "UNTRAINED"),
            "historical_edge_confidence": validation.get("historical_edge_confidence", "INSUFFICIENT_HISTORY"),
            "market_raw_probability_pct": None if market_raw_prob is None else round(100 * market_raw_prob, 2),
            "market_reference_probability_pct": round(100 * market_prob, 2),
            "market_reference_type": "DEVIG_FAIR" if fair_prob is not None else "RAW_FALLBACK",
            "devig_paired_books": fair_books,
            "devig_required_for_shadow": devig_required_for_shadow,
            "data_quality_book_count": quality_book_count,
            "v2_probability_pct": round(100 * p_model, 2),
            "edge_pct_points": round(100 * edge, 2),
            "conservative_probability_pct": round(100 * conservative_p, 2),
            "conservative_edge_pct_points": round(100 * conservative_edge, 2),
            "uncertainty_buffer_pct_points": round(100 * buffer, 2),
            "segment_agreement_applied": segment_agreement_applied,
            "segment_model_status": (
                None
                if not segment_ready
                else segment_source
            ),
            "segment_independent_edge": segment_independent_edge,
            "segment_independent_blocks": (
                segment_validation.get(
                    "independent_blocks"
                )
                if segment_ready
                else None
            ),
            "segment_historical_edge_confidence": (
                segment_validation.get(
                    "historical_edge_confidence"
                )
                if segment_ready
                else None
            ),
            "segment_model_probability_pct": (
                None
                if segment_probability is None
                else round(
                    100
                    * segment_probability,
                    2,
                )
            ),
            "model_agreement_gap_pct_points": (
                None
                if segment_agreement_gap is None
                else round(
                    100
                    * segment_agreement_gap,
                    2,
                )
            ),
            "agreement_probability_pct": round(
                100
                * agreement_probability,
                2,
            ),
            "agreement_conservative_probability_pct": round(
                100
                * agreement_conservative_p,
                2,
            ),
            "agreement_conservative_edge_pct_points": round(
                100
                * agreement_conservative_edge,
                2,
            ),
            "american_odds": price,
            "expected_value_pct": None if ev is None else round(100 * ev, 2),
            "conservative_expected_value_pct": None if conservative_ev is None else round(100 * conservative_ev, 2),
            "data_quality_grade": quality,
            "probability_source": validation.get("deployment_probability_source", "MARKET_REFERENCE_UNTRAINED"),
            "selection_rule_status": validation.get("selection_rule_status", "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY"),
            "shadow_decision": shadow,
            "live_pick_changed": False,
        })
    return rows


def main():
    validations = {}
    models = {}
    current_rows = []

    for lane_key, cfg in LANES.items():
        history = build_history(cfg)
        validation = walk_forward(history, cfg)
        if validation.get("status") != "READY":
            validation = {
                **validation,
                "feature_names": cfg.get("features", []),
                "metrics": {},
                "paired_comparisons": {},
                "deployment_probability_source": "MARKET_REFERENCE_UNTRAINED",
                "old_score_status": "UNTRAINED",
                "old_score_coefficient": None,
                "historical_edge_confidence": "INSUFFICIENT_HISTORY",
                "selection_rule_status": "INSUFFICIENT_HISTORY_FORWARD_TRACKING_ONLY",
                "coefficients": {},
            }
        validations[lane_key] = {
            "sport": cfg["sport"],
            "lane": cfg["lane"],
            **validation,
        }
        models[lane_key] = {
            "sport": cfg["sport"],
            "lane": cfg["lane"],
            "history_n": int(len(history)),
            "deployment_probability_source": validation.get("deployment_probability_source"),
            "old_score_status": validation.get("old_score_status"),
            "old_score_coefficient": validation.get("old_score_coefficient"),
            "historical_edge_confidence": validation.get("historical_edge_confidence"),
            "selection_rule_status": validation.get("selection_rule_status"),
            "feature_names": validation.get("feature_names", []),
            "coefficients": validation.get("coefficients", {}),
            "automatic_live_change": False,
        }
        current_rows.extend(build_current_lane(lane_key, cfg, validation))

    # Canonical player aliases can produce duplicate display rows for the same
    # event/player/market/side/line. Keep one best-evidence row per identity.
    deduped = {}
    quality_rank = {"A": 4, "B": 3, "C": 2, "D": 1}
    for row in current_rows:
        dedup_key = "|".join([
            text_value(row.get("lane_key")),
            text_value(row.get("event_id")),
            normalized_key(row.get("player_key") or row.get("player")),
            text_value(row.get("market_subtype")).upper(),
            text_value(row.get("side")).upper(),
            f"{num(row.get('line')):.4f}" if num(row.get("line")) is not None else "",
        ])
        rank = (
            int(num(row.get("devig_paired_books")) or 0),
            quality_rank.get(text_value(row.get("data_quality_grade")).upper(), 0),
            len(text_value(row.get("player"))),
        )
        prior = deduped.get(dedup_key)
        if prior is None or rank > prior[0]:
            deduped[dedup_key] = (rank, row)
    current_rows = [value[1] for value in deduped.values()]

    by_lane = {}
    for lane_key in LANES:
        rows = [r for r in current_rows if r["lane_key"] == lane_key]
        by_lane[lane_key] = {
            "candidates": len(rows),
            "shadow_plays": sum(r["shadow_decision"] in {"SHADOW_PLAY", "SHADOW_LEG"} for r in rows),
            "shadow_monitors": sum(r["shadow_decision"] == "SHADOW_MONITOR" for r in rows),
            "passes": sum(r["shadow_decision"] not in {"SHADOW_PLAY", "SHADOW_LEG", "SHADOW_MONITOR"} for r in rows),
            "probability_source": validations[lane_key].get("deployment_probability_source"),
            "old_score_status": validations[lane_key].get("old_score_status"),
            "selection_rule_status": validations[lane_key].get("selection_rule_status"),
        }

    validation_payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "method": "LANE_SPECIFIC_ROLLING_ORIGIN_WALK_FORWARD",
        "automatic_live_changes": False,
        "coverage": {
            "active_sports": ["NFL", "NBA", "NHL", "MLB"],
            "active_lane_count": len(LANES),
            "lane_design": "PROP_AND_PRIZEPICKS_SEPARATE_BY_SPORT",
            "college_status": "CFB_AND_CBB_HAVE_NO_PLAYER_PROP_PRIZEPICKS_DECISION_LANES_TO_VALIDATE_YET",
        },
        "lanes": validations,
        "rules": [
            "Each sport/lane is validated separately.",
            "Raw sportsbook/reference probability is the baseline to beat.",
            "Lane features must beat both raw and calibrated market baselines before they count as incremental signal.",
            "Historical improvements are checked with paired game-block bootstrap confidence intervals so correlated props do not overstate evidence.",
            "Lanes without enough settled history stay market-reference-only, freeze forward records, and cannot promote.",
            "PrizePicks may borrow an exact matching sportsbook prop price only as a market reference; it is never treated as PrizePicks payout odds.",
            "Old HULK score is excluded from probability when its learned direction is negative.",
            "No live recommendation changes occur from this layer.",
            "PrizePicks uses sportsbook reference probability and leg edge; no payout EV is claimed without entry-level payout economics.",
        ],
    }
    model_payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "models": models,
    }
    current_payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "mode": "SHADOW_ONLY",
        "summary": {
            "candidates": len(current_rows),
            "shadow_plays": sum(r["shadow_decision"] in {"SHADOW_PLAY", "SHADOW_LEG"} for r in current_rows),
            "shadow_monitors": sum(r["shadow_decision"] == "SHADOW_MONITOR" for r in current_rows),
            "passes": sum(r["shadow_decision"] not in {"SHADOW_PLAY", "SHADOW_LEG", "SHADOW_MONITOR"} for r in current_rows),
        },
        "by_lane": by_lane,
        "picks": current_rows,
    }

    for path, payload in [
        (MODEL_OUT, model_payload),
        (VALIDATION_OUT, validation_payload),
        (CURRENT_OUT, current_payload),
        (PUBLIC / "prop_v2_models.json", model_payload),
        (PUBLIC / "prop_v2_validation.json", validation_payload),
        (PUBLIC / "prop_v2_current.json", current_payload),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))

    if DIST.exists():
        (DIST / "prop_v2_models.json").write_text(json.dumps(model_payload, indent=2))
        (DIST / "prop_v2_validation.json").write_text(json.dumps(validation_payload, indent=2))
        (DIST / "prop_v2_current.json").write_text(json.dumps(current_payload, indent=2))

    print(json.dumps({
        "status": "READY",
        "summary": current_payload["summary"],
        "by_lane": by_lane,
        "validation": {
            lane: {
                "history_n": v.get("history_n"),
                "walk_forward_n": v.get("walk_forward_n"),
                "source": v.get("deployment_probability_source"),
                "old_score_status": v.get("old_score_status"),
                "old_score_coefficient": v.get("old_score_coefficient"),
                "metrics": v.get("metrics"),
            }
            for lane, v in validations.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
