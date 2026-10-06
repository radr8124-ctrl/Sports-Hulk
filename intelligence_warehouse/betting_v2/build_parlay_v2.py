#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

CURRENT_OUT = OUT_DIR / "PARLAY_V2_CURRENT.json"
VALIDATION_OUT = OUT_DIR / "PARLAY_V2_VALIDATION.json"
MODEL_VERSION = "PARLAY_V2_SOURCE_PROOF_2026_10_05"

PROP_CURRENT = OUT_DIR / "PROP_V2_CURRENT.json"
PROP_FORWARD = OUT_DIR / "PROP_V2_FORWARD_SUMMARY.json"
GAME_CURRENT = OUT_DIR / "BETTING_V2_ALL_MARKETS_CURRENT.json"
GAME_FORWARD = OUT_DIR / "BETTING_V2_ALL_MARKETS_FORWARD_SUMMARY.json"

SPORTS = ("NFL", "CFB", "CBB", "MLB", "NBA", "NHL")
SETTLED = {"WIN", "LOSS"}

CURRENT_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" /
    f"{sport}_PARLAYS_TODAY.csv"
    for sport in SPORTS
}
HISTORY_FILES = {
    sport: ROOT / f"{sport.lower()}_live" / "decision" / "history" /
    f"{sport}_GRADED_RECOMMENDATIONS.csv"
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


def norm(value):
    text = unicodedata.normalize(
        "NFKD", clean(value)
    ).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def parse_json(value):
    try:
        return json.loads(value or "{}")
    except Exception:
        return {}


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


def american_profit(odds):
    odds = num(odds)
    if odds is None or abs(odds) < 100:
        return None
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def clamp_p(pct):
    value = num(pct)
    if value is None:
        return None
    return max(0.01, min(99.99, value))


def probability_product(values):
    vals = [clamp_p(v) for v in values]
    if any(v is None for v in vals) or not vals:
        return None
    p = 1.0
    for value in vals:
        p *= value / 100.0
    return round(100 * p, 4)


def brier(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2)) if len(y) else None


def log_loss(y, p):
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return float(
        -np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))
    ) if len(y) else None


def sigmoid(z):
    z = np.clip(np.asarray(z, dtype=float), -35, 35)
    return 1.0 / (1.0 + np.exp(-z))


def fit_score_model(score, outcome, l2=4.0):
    score = np.asarray(score, dtype=float)
    y = np.asarray(outcome, dtype=float)
    X = np.column_stack([
        np.ones(len(score)),
        (score - 80.0) / 10.0,
    ])
    beta = np.zeros(2, dtype=float)
    m = min(0.99, max(0.01, float(np.mean(y))))
    beta[0] = math.log(m / (1 - m))
    penalty = np.diag([0.0, l2])
    for _ in range(100):
        p = sigmoid(X @ beta)
        w = np.clip(p * (1 - p), 1e-6, None)
        grad = X.T @ (p - y) + penalty @ beta
        hess = X.T @ (X * w[:, None]) + penalty
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


def legacy_walk_forward(frame):
    n = len(frame)
    if n < 50:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "history_n": n,
            "minimum_required": 50,
        }

    frame = frame.sort_values("_time").reset_index(drop=True)
    min_train = max(30, int(math.floor(n * 0.50)))
    step = max(10, int(math.ceil(n * 0.10)))
    records = []

    for start in range(min_train, n, step):
        end = min(n, start + step)
        train = frame.iloc[:start]
        test = frame.iloc[start:end]
        if test.empty:
            continue
        y_train = train["outcome"].astype(int).to_numpy()
        if len(set(y_train.tolist())) < 2:
            continue
        beta = fit_score_model(
            train["score"].astype(float).to_numpy(),
            y_train,
        )
        base = float(np.mean(y_train))
        X_test = np.column_stack([
            np.ones(len(test)),
            (
                test["score"].astype(float).to_numpy() - 80.0
            ) / 10.0,
        ])
        records.append({
            "y": test["outcome"].astype(int).to_numpy(),
            "base": np.full(len(test), base),
            "score_model": sigmoid(X_test @ beta),
        })

    if not records:
        return {
            "status": "NO_FOLDS",
            "history_n": n,
        }

    y = np.concatenate([r["y"] for r in records])
    base = np.concatenate([r["base"] for r in records])
    score_model = np.concatenate([
        r["score_model"] for r in records
    ])
    metrics = {
        "base_rate": {
            "n": int(len(y)),
            "brier": round(brier(y, base), 5),
            "log_loss": round(log_loss(y, base), 5),
        },
        "old_score_calibrated": {
            "n": int(len(y)),
            "brier": round(brier(y, score_model), 5),
            "log_loss": round(log_loss(y, score_model), 5),
        },
    }
    score_beats = (
        metrics["old_score_calibrated"]["brier"]
        <= metrics["base_rate"]["brier"] - 0.001
        and metrics["old_score_calibrated"]["log_loss"]
        <= metrics["base_rate"]["log_loss"] - 0.001
    )
    return {
        "status": "READY",
        "history_n": n,
        "walk_forward_n": int(len(y)),
        "metrics": metrics,
        "old_score_beats_base_rate": bool(score_beats),
        "deployment_use": "DIAGNOSTIC_ONLY",
    }


def normalize_line(value):
    x = num(value)
    if x is None:
        return None
    return round(float(x), 4)


def metric_market_map():
    path = (
        ROOT / "mlb_live" / "decision" /
        "MLB_PROP_DECISIONS.csv"
    )
    out = {}
    if not path.exists():
        return out
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return out
    if "metric" not in d.columns or "market_subtype" not in d.columns:
        return out
    for metric, group in d.groupby("metric"):
        values = [
            clean(v).upper()
            for v in group["market_subtype"].dropna().unique()
            if clean(v)
        ]
        if len(set(values)) == 1:
            out[clean(metric).lower()] = values[0]
    return out


MLB_METRIC_TO_MARKET = metric_market_map()


def canonical_prop_market(sport, market):
    text = clean(market)
    if sport == "MLB":
        mapped = MLB_METRIC_TO_MARKET.get(text.lower())
        if mapped:
            return mapped
    return text.upper()


def leg_from_mapping(mapping, index, sport):
    prefix = f"leg{index}_"
    kind = clean(
        mapping.get(prefix + "kind")
        or mapping.get(prefix + "lane")
    ).upper()
    event = clean(
        mapping.get(prefix + "event")
        or mapping.get(prefix + "game")
    )
    player = clean(
        mapping.get(prefix + "player")
        or mapping.get(prefix + "subject")
    )
    market = clean(mapping.get(prefix + "market")).upper()
    selection = clean(
        mapping.get(prefix + "selection")
    ).upper()
    line = normalize_line(mapping.get(prefix + "line"))
    score = num(mapping.get(prefix + "score"))

    if kind == "GAME_ML":
        kind = "GAME"
        market = "MONEYLINE"
    if not kind:
        if player:
            kind = "PROP"
        elif market in {"MONEYLINE", "SPREAD", "TOTAL"}:
            kind = "GAME"

    if sport == "CFB" and market in {
        "MONEYLINE", "SPREAD", "TOTAL"
    }:
        kind = "GAME"
    if sport == "CBB" and market in {
        "MONEYLINE", "SPREAD", "TOTAL"
    }:
        kind = "GAME"

    return {
        "kind": kind,
        "event": event,
        "player": player,
        "player_key": norm(player),
        "market": canonical_prop_market(
            sport, market
        ) if kind in {"PROP", "PRIZEPICKS"} else market,
        "selection": selection,
        "line": line,
        "legacy_score": score,
    }


def leg_signature(leg):
    line = (
        "" if leg.get("line") is None
        else f"{float(leg['line']):.4f}"
    )
    return "|".join([
        clean(leg.get("kind")).upper(),
        clean(leg.get("event")),
        norm(leg.get("player")),
        clean(leg.get("market")).upper(),
        clean(leg.get("selection")).upper(),
        line,
    ])


def combo_signature(legs):
    return "||".join(sorted(
        leg_signature(leg) for leg in legs
    ))


def game_source_index():
    payload = read_json(GAME_CURRENT, {})
    by_base = {}
    for row in payload.get("picks") or []:
        sport = clean(row.get("sport")).upper()
        market = clean(row.get("market")).upper()
        game = clean(row.get("game_key"))
        line = normalize_line(row.get("line"))
        key = (sport, game, market, line)
        by_base.setdefault(key, []).append(row)
    return by_base


def prop_source_rows():
    payload = read_json(PROP_CURRENT, {})
    return payload.get("picks") or []


def resolve_game_leg(sport, leg, index):
    key = (
        sport,
        clean(leg.get("event")),
        clean(leg.get("market")).upper(),
        normalize_line(leg.get("line")),
    )
    candidates = list(index.get(key, []))
    if not candidates:
        return None

    selection_norm = norm(leg.get("selection"))
    exact = [
        row for row in candidates
        if norm(row.get("selection")) == selection_norm
    ]
    if len(exact) == 1:
        row = exact[0]
        mode = "EXACT_SELECTION"
    elif len(candidates) == 1:
        row = candidates[0]
        mode = "UNIQUE_MARKET_LINE"
    else:
        return None

    return {
        "resolution_mode": mode,
        "source_family": "GAME_V2",
        "source_lane": row.get("lane_key"),
        "source_probability_pct": num(
            row.get("calibrated_win_probability_pct")
        ),
        "source_reference_probability_pct": num(
            row.get("market_reference_probability_pct")
        ),
        "source_conservative_probability_pct": num(
            row.get("conservative_probability_pct")
        ),
        "source_probability_source": row.get(
            "probability_source"
        ),
        "source_historical_confidence": row.get(
            "historical_edge_confidence"
        ),
        "source_selection_status": row.get(
            "selection_rule_status"
        ),
        "source_shadow_decision": row.get(
            "shadow_decision"
        ),
        "source_exact_line": row.get("line"),
        "source_exact_selection": row.get("selection"),
        "source_game_key": row.get("game_key"),
    }


def resolve_prop_leg(sport, leg, rows):
    market = clean(leg.get("market")).upper()
    player = norm(leg.get("player"))
    selection = clean(leg.get("selection")).upper()
    line = normalize_line(leg.get("line"))
    kind = clean(leg.get("kind")).upper()
    event = clean(leg.get("event"))

    candidates = []
    for row in rows:
        if clean(row.get("sport")).upper() != sport:
            continue
        lane = clean(row.get("lane")).upper()
        if kind == "PRIZEPICKS" and lane != "PRIZEPICKS":
            continue
        if kind == "PROP" and lane != "PROP":
            continue
        if norm(
            row.get("player_key") or row.get("player")
        ) != player:
            continue
        if clean(
            row.get("market_subtype")
        ).upper() != market:
            continue
        if clean(row.get("side")).upper() != selection:
            continue
        if normalize_line(row.get("line")) != line:
            continue
        candidates.append(row)

    if not candidates:
        return None

    event_exact = [
        row for row in candidates
        if event and event in {
            clean(row.get("event_id")),
            clean(row.get("game_key")),
        }
    ]
    if len(event_exact) == 1:
        row = event_exact[0]
        mode = "EXACT_EVENT"
    elif len(candidates) == 1:
        row = candidates[0]
        mode = "UNIQUE_PLAYER_MARKET_LINE"
    else:
        return None

    return {
        "resolution_mode": mode,
        "source_family": "PROP_V2",
        "source_lane": row.get("lane_key"),
        "source_probability_pct": num(
            row.get("v2_probability_pct")
        ),
        "source_reference_probability_pct": num(
            row.get("market_reference_probability_pct")
        ),
        "source_conservative_probability_pct": num(
            row.get("conservative_probability_pct")
        ),
        "source_probability_source": row.get(
            "probability_source"
        ),
        "source_historical_confidence": row.get(
            "historical_edge_confidence"
        ),
        "source_selection_status": row.get(
            "selection_rule_status"
        ),
        "source_shadow_decision": row.get(
            "shadow_decision"
        ),
        "source_exact_line": row.get("line"),
        "source_exact_selection": row.get("side"),
        "source_event_id": row.get("event_id"),
        "source_game_key": row.get("game_key"),
        "source_event_start": row.get("event_start"),
    }


def promotion_maps():
    prop = read_json(PROP_FORWARD, {})
    game = read_json(GAME_FORWARD, {})
    out = {}
    for lane, value in (
        prop.get("by_lane") or {}
    ).items():
        out[lane] = (
            value.get("promotion") or {}
        ).get("recommendation")
    for lane, value in (
        game.get("by_lane") or {}
    ).items():
        out[lane] = (
            value.get("promotion") or {}
        ).get("recommendation")
    return out


def source_proof_ready(resolution, promotions):
    if not resolution:
        return False
    lane = clean(resolution.get("source_lane"))
    promotion = promotions.get(lane)
    if promotion != "MANUAL_REVIEW_CANDIDATE":
        return False
    decision = clean(
        resolution.get("source_shadow_decision")
    ).upper()
    return decision in {
        "SHADOW_PLAY",
        "SHADOW_MONITOR",
        "SHADOW_LEG",
    }


def extract_parlay_price(row):
    for key in [
        "american_odds",
        "price_american",
        "parlay_odds",
        "combined_american_odds",
    ]:
        value = num(row.get(key))
        if value is not None and abs(value) >= 100:
            return value
    return None


def current_rows():
    game_index = game_source_index()
    prop_rows = prop_source_rows()
    promotions = promotion_maps()
    candidates = []

    for sport in SPORTS:
        path = CURRENT_FILES[sport]
        if not path.exists():
            continue
        try:
            d = pd.read_csv(path, low_memory=False)
        except Exception:
            continue
        if d.empty:
            continue

        for _, row in d.iterrows():
            mapping = row.to_dict()
            legs = [
                leg_from_mapping(mapping, 1, sport),
                leg_from_mapping(mapping, 2, sport),
            ]
            if any(
                not clean(leg.get("market"))
                or not clean(leg.get("selection"))
                for leg in legs
            ):
                continue

            resolutions = []
            for leg in legs:
                if leg["kind"] == "GAME":
                    resolution = resolve_game_leg(
                        sport, leg, game_index
                    )
                elif leg["kind"] in {
                    "PROP", "PRIZEPICKS"
                }:
                    resolution = resolve_prop_leg(
                        sport, leg, prop_rows
                    )
                else:
                    resolution = None
                resolutions.append(resolution)

            for leg, resolution in zip(
                legs, resolutions
            ):
                if resolution:
                    leg.update(resolution)
                    leg["forward_promotion"] = promotions.get(
                        clean(resolution.get("source_lane"))
                    )
                    leg["source_proof_ready"] = (
                        source_proof_ready(
                            resolution, promotions
                        )
                    )
                else:
                    leg["resolution_mode"] = "UNRESOLVED"
                    leg["source_proof_ready"] = False

            events = [
                clean(
                    leg.get("source_game_key")
                    or leg.get("source_event_id")
                    or leg.get("event")
                )
                for leg in legs
            ]
            different_events = (
                bool(events[0])
                and bool(events[1])
                and events[0] != events[1]
            )
            correlation_status = (
                "CROSS_GAME_RESEARCH_INDEPENDENCE"
                if different_events
                else "CORRELATION_MODEL_REQUIRED"
            )

            resolved = all(
                leg.get("resolution_mode")
                != "UNRESOLVED"
                for leg in legs
            )
            joint_v2 = (
                probability_product([
                    leg.get("source_probability_pct")
                    for leg in legs
                ])
                if resolved and different_events
                else None
            )
            joint_ref = (
                probability_product([
                    leg.get(
                        "source_reference_probability_pct"
                    )
                    for leg in legs
                ])
                if resolved and different_events
                else None
            )
            joint_cons = (
                probability_product([
                    leg.get(
                        "source_conservative_probability_pct"
                    )
                    for leg in legs
                ])
                if resolved and different_events
                else None
            )

            edge = (
                None
                if joint_v2 is None or joint_ref is None
                else round(joint_v2 - joint_ref, 4)
            )
            price = extract_parlay_price(mapping)
            profit = american_profit(price)
            ev = (
                None
                if profit is None or joint_v2 is None
                else round(
                    100 * (
                        (joint_v2 / 100.0) * profit
                        - (1 - joint_v2 / 100.0)
                    ),
                    4,
                )
            )
            cons_ev = (
                None
                if profit is None or joint_cons is None
                else round(
                    100 * (
                        (joint_cons / 100.0) * profit
                        - (1 - joint_cons / 100.0)
                    ),
                    4,
                )
            )

            all_leg_proof = all(
                bool(leg.get("source_proof_ready"))
                for leg in legs
            )

            if not resolved:
                decision = "PASS_UNRESOLVED_V2_LEG"
            elif not different_events:
                decision = (
                    "PASS_CORRELATION_MODEL_REQUIRED"
                )
            elif not all_leg_proof:
                decision = "PASS_UNPROVEN_SOURCE_LEG"
            elif price is None:
                decision = "PASS_NO_CAPTURED_PARLAY_PRICE"
            elif joint_v2 is None:
                decision = "PASS_NO_JOINT_PROBABILITY"
            elif cons_ev is None or cons_ev <= 3.0:
                decision = "PASS_PARLAY_PRICE"
            elif edge is None or edge <= 1.5:
                decision = "PASS_PARLAY_EDGE"
            else:
                decision = "SHADOW_MONITOR"

            signature = combo_signature(legs)
            legacy_score = num(
                mapping.get("parlay_score")
                or mapping.get("evidence_score")
            )
            candidates.append({
                "model_version": MODEL_VERSION,
                "sport": sport,
                "combo_signature": signature,
                "legacy_parlay_score": legacy_score,
                "legacy_status": clean(
                    mapping.get("status")
                ),
                "legacy_probability_claim": clean(
                    mapping.get("probability_claim")
                    or mapping.get("probability_status")
                ),
                "legacy_payout_claim": clean(
                    mapping.get("payout_claim")
                    or mapping.get("payout_status")
                ),
                "leg_count": 2,
                "legs": legs,
                "resolved_legs": sum(
                    leg.get("resolution_mode")
                    != "UNRESOLVED"
                    for leg in legs
                ),
                "all_source_legs_forward_proven": all_leg_proof,
                "correlation_status": correlation_status,
                "joint_probability_method": (
                    "INDEPENDENCE_PRODUCT_RESEARCH_ONLY"
                    if joint_v2 is not None
                    else "NOT_CALCULATED"
                ),
                "joint_v2_probability_pct": joint_v2,
                "joint_reference_probability_pct": joint_ref,
                "joint_conservative_probability_pct": joint_cons,
                "joint_edge_pct_points": edge,
                "captured_parlay_american_odds": price,
                "expected_value_pct": ev,
                "conservative_expected_value_pct": cons_ev,
                "payout_status": (
                    "CAPTURED_PRICE"
                    if price is not None
                    else "NO_CAPTURED_PARLAY_PRICE"
                ),
                "shadow_decision": decision,
                "duplicate_combo_count": 1,
                "shared_leg_exposure_block": False,
                "shared_event_exposure_block": False,
                "probability_claim": False,
                "payout_claim": False,
                "live_pick_changed": False,
            })

    # Reverse-order and repeated combinations collapse into one record.
    grouped = {}
    for row in candidates:
        grouped.setdefault(
            (row["sport"], row["combo_signature"]),
            [],
        ).append(row)

    deduped = []
    for _, rows in grouped.items():
        best = max(
            rows,
            key=lambda r: (
                int(r.get("resolved_legs") or 0),
                num(r.get("legacy_parlay_score")) or -999,
            ),
        )
        best["duplicate_combo_count"] = len(rows)
        deduped.append(best)

    # Exposure cap for anything that ever crosses the monitor gate.
    monitors = [
        row for row in deduped
        if row["shadow_decision"] == "SHADOW_MONITOR"
    ]
    monitors.sort(
        key=lambda r: (
            num(r.get("conservative_expected_value_pct"))
            or -999,
            num(r.get("joint_edge_pct_points"))
            or -999,
        ),
        reverse=True,
    )
    used_legs = set()
    used_events = set()
    for row in monitors:
        leg_sigs = {
            leg_signature(leg) for leg in row["legs"]
        }
        events = {
            clean(
                leg.get("source_game_key")
                or leg.get("source_event_id")
                or leg.get("event")
            )
            for leg in row["legs"]
            if clean(
                leg.get("source_game_key")
                or leg.get("source_event_id")
                or leg.get("event")
            )
        }
        if leg_sigs & used_legs:
            row["shared_leg_exposure_block"] = True
            row["shadow_decision"] = (
                "PASS_SHARED_LEG_EXPOSURE"
            )
            continue
        if events & used_events:
            row["shared_event_exposure_block"] = True
            row["shadow_decision"] = (
                "PASS_SHARED_EVENT_EXPOSURE"
            )
            continue
        used_legs |= leg_sigs
        used_events |= events

    return deduped


def historical_frame(sport):
    path = HISTORY_FILES[sport]
    if not path.exists():
        return pd.DataFrame()
    try:
        d = pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()
    if d.empty or "lane" not in d.columns:
        return pd.DataFrame()
    d = d[
        d["lane"].astype(str).str.upper().eq("PARLAY")
        & d["grade"].astype(str).str.upper().isin(SETTLED)
    ].copy()
    if d.empty:
        return d

    rows = []
    for _, row in d.iterrows():
        payload = parse_json(row.get("payload_json"))
        mapping = dict(payload)
        # Row columns backfill older payload variants.
        for key in [
            "game_key", "selection", "score",
            "leg1_grade", "leg2_grade",
        ]:
            if key not in mapping and key in row.index:
                mapping[key] = row.get(key)
        legs = [
            leg_from_mapping(mapping, 1, sport),
            leg_from_mapping(mapping, 2, sport),
        ]
        signature = combo_signature(legs)
        if not signature:
            continue
        score = num(
            row.get("score")
            or payload.get("parlay_score")
            or payload.get("evidence_score")
        )
        if score is None:
            continue
        snapshot = pd.to_datetime(
            row.get("snapshot_at"),
            errors="coerce",
            utc=True,
        )
        rows.append({
            "sport": sport,
            "combo_signature": signature,
            "score": score,
            "outcome": (
                1
                if clean(row.get("grade")).upper() == "WIN"
                else 0
            ),
            "_time": (
                snapshot
                if pd.notna(snapshot)
                else pd.Timestamp(
                    "1970-01-01", tz="UTC"
                )
            ),
        })

    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    return (
        frame.sort_values("_time")
        .drop_duplicates(
            ["sport", "combo_signature"],
            keep="first",
        )
        .reset_index(drop=True)
    )


def historical_validation():
    by_sport = {}
    total_rows = 0
    for sport in SPORTS:
        frame = historical_frame(sport)
        total_rows += len(frame)
        wins = int(frame["outcome"].sum()) if not frame.empty else 0
        n = int(len(frame))
        by_sport[sport] = {
            "settled_unique_combos": n,
            "wins": wins,
            "losses": n - wins,
            "hit_rate_pct": (
                None if n == 0
                else round(100 * wins / n, 1)
            ),
            "legacy_score_diagnostic": (
                legacy_walk_forward(frame)
                if not frame.empty
                else {
                    "status": "INSUFFICIENT_HISTORY",
                    "history_n": 0,
                }
            ),
        }
    return {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "status": "READY",
        "history_rows": total_rows,
        "by_sport": by_sport,
        "rules": [
            "Legacy parlay score is diagnostic only and is never treated as probability.",
            "Historical parlay outcomes cannot retroactively validate V2 leg probabilities that did not exist at prediction time.",
            "Parlay V2 performance proof therefore begins with the versioned forward ledger.",
        ],
    }


def main():
    rows = current_rows()
    validation = historical_validation()
    by_sport = {}
    for sport in SPORTS:
        sport_rows = [
            r for r in rows if r["sport"] == sport
        ]
        reason_counts = Counter(
            r["shadow_decision"]
            for r in sport_rows
        )
        by_sport[sport] = {
            "candidates": len(sport_rows),
            "resolved_all_legs": sum(
                r["resolved_legs"] == r["leg_count"]
                for r in sport_rows
            ),
            "all_source_legs_forward_proven": sum(
                bool(r["all_source_legs_forward_proven"])
                for r in sport_rows
            ),
            "research_joint_probability_available": sum(
                r["joint_v2_probability_pct"] is not None
                for r in sport_rows
            ),
            "captured_parlay_price": sum(
                r["captured_parlay_american_odds"]
                is not None
                for r in sport_rows
            ),
            "shadow_monitors": sum(
                r["shadow_decision"] == "SHADOW_MONITOR"
                for r in sport_rows
            ),
            "decision_counts": dict(reason_counts),
        }

    payload = {
        "generated_at": now_iso(),
        "model_version": MODEL_VERSION,
        "status": "READY",
        "mode": "SHADOW_ONLY",
        "summary": {
            "candidates": len(rows),
            "resolved_all_legs": sum(
                r["resolved_legs"] == r["leg_count"]
                for r in rows
            ),
            "all_source_legs_forward_proven": sum(
                bool(r["all_source_legs_forward_proven"])
                for r in rows
            ),
            "research_joint_probability_available": sum(
                r["joint_v2_probability_pct"] is not None
                for r in rows
            ),
            "captured_parlay_price": sum(
                r["captured_parlay_american_odds"]
                is not None
                for r in rows
            ),
            "shadow_monitors": sum(
                r["shadow_decision"] == "SHADOW_MONITOR"
                for r in rows
            ),
            "passes": sum(
                r["shadow_decision"] != "SHADOW_MONITOR"
                for r in rows
            ),
        },
        "by_sport": by_sport,
        "picks": rows,
        "rules": [
            "Every leg must resolve to an exact current V2 source record.",
            "An underlying leg must earn its own lane forward proof before a parlay can advance.",
            "Same-game combinations receive no independence probability; a correlation model is required.",
            "Cross-game probability multiplication is research-only until forward parlay calibration proves it.",
            "No EV or ROI claim is allowed without a captured combined parlay price or platform payout.",
            "Reverse-order duplicates collapse to one canonical combination.",
            "Shadow selection cannot reuse the same exact leg or underlying event across simultaneous parlays.",
            "No live parlay promotion occurs automatically.",
        ],
    }

    for path, content in [
        (CURRENT_OUT, payload),
        (VALIDATION_OUT, validation),
        (PUBLIC / "parlay_v2_current.json", payload),
        (PUBLIC / "parlay_v2_validation.json", validation),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, indent=2))
    if DIST.exists():
        (DIST / "parlay_v2_current.json").write_text(
            json.dumps(payload, indent=2)
        )
        (DIST / "parlay_v2_validation.json").write_text(
            json.dumps(validation, indent=2)
        )

    print(json.dumps({
        "status": "READY",
        "summary": payload["summary"],
        "by_sport": by_sport,
        "legacy_validation": validation["by_sport"],
    }, indent=2))


if __name__ == "__main__":
    main()
