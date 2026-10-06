#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

LAB = OUT_DIR / "BETTING_V2_GAME_CHALLENGERS.json"
BASE_CURRENT = OUT_DIR / "BETTING_V2_ALL_MARKETS_CURRENT.json"
CURRENT_OUT = OUT_DIR / "BETTING_V2_GAME_CHALLENGER_CURRENT.json"
LEDGER = OUT_DIR / "BETTING_V2_GAME_CHALLENGER_FORWARD_LEDGER.jsonl"
SUMMARY = OUT_DIR / "BETTING_V2_GAME_CHALLENGER_FORWARD_SUMMARY.json"

LANE_KEY = "CFB_TOTAL"
SPORT = "CFB"
MARKET = "TOTAL"
MODEL_VERSION = "BETTING_V2_CFB_TOTAL_CHALLENGER_2026_10_05"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))

import build_betting_v2_game_challengers as lab
import build_betting_v2_all_markets as game
import build_betting_v2 as base


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def clean(v):
    return game.clean(v)


def num(v):
    return game.num(v)


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


def read_jsonl(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as h:
        h.write(json.dumps(row, separators=(",", ":")) + "\n")


def canonical():
    out = {}
    for e in read_jsonl(LEDGER):
        key = e.get("forward_key")
        if key:
            out[key] = {**out.get(key, {}), **e}
    return out


def chosen_spec(lane):
    counts = lane.get("choice_counts") or {}
    if not counts:
        return "RICH_ONLY", 5.0
    label = sorted(
        counts.items(),
        key=lambda kv: (kv[1], kv[0] == "RICH_ONLY"),
        reverse=True,
    )[0][0]
    l2 = 5.0
    if label.startswith("RICH_L2:"):
        try:
            l2 = float(label.split(":", 1)[1])
        except Exception:
            l2 = 5.0
    return label, l2


def features_for_label(groups, label):
    rich = []
    for feats in groups.values():
        rich.extend(feats)
    rich = list(dict.fromkeys(rich))
    if label == "RICH_PLUS_OLD_SCORE":
        return rich + ["old_score"]
    if label.startswith("DROP_GROUP:"):
        drop = label.split(":", 1)[1]
        return [
            f for f in rich
            if f not in (groups.get(drop) or [])
        ]
    return rich


def fit_full():
    payload = read_json(LAB, {})
    lane = (payload.get("lanes") or {}).get(LANE_KEY, {})
    if lane.get("status") not in {
        "PROMISING_NOT_PROVEN",
        "CHALLENGER_REVIEW_CANDIDATE",
    }:
        return None, lane

    frame = lab.enriched_history(SPORT, MARKET)
    groups, _ = lab.available_features(frame, LANE_KEY)
    label, l2 = chosen_spec(lane)
    features = features_for_label(groups, label)
    scaler = lab.fit_scaler(frame, features)
    X = lab.design(frame, features, scaler)
    y = frame["outcome"].astype(int).to_numpy()
    weights = game.block_weights(frame)
    beta = game.fit_logistic_weighted(
        X, y, weights, l2=l2
    )
    return {
        "frame": frame,
        "groups": groups,
        "label": label,
        "l2": l2,
        "features": features,
        "scaler": scaler,
        "beta": beta,
    }, lane


def current_payload(model, lane):
    if model is None:
        return {
            "generated_at": now_iso(),
            "status": "HOLD_NO_PROMISING_CHALLENGER",
            "model_version": MODEL_VERSION,
            "lane_key": LANE_KEY,
            "rows": [],
        }

    base_current = read_json(BASE_CURRENT, {})
    base_rows = [
        row for row in (base_current.get("picks") or [])
        if row.get("lane_key") == LANE_KEY
    ]
    if not base_rows:
        return {
            "generated_at": now_iso(),
            "status": "READY_NO_CURRENT_CANDIDATES",
            "model_version": MODEL_VERSION,
            "lane_key": LANE_KEY,
            "historical_status": lane.get("status"),
            "chosen_inner_consensus": model["label"],
            "chosen_l2": model["l2"],
            "features": model["features"],
            "rows": [],
        }

    raw = pd.read_csv(
        game.CURRENT_FILES[SPORT],
        low_memory=False,
    )
    rows = []
    for base_row in base_rows:
        matches = raw[
            raw["game_key"].astype(str).eq(clean(base_row.get("game_key")))
            & raw["market_canonical"].astype(str).str.upper().eq(MARKET)
            & raw["selection_canonical"].astype(str).str.upper().eq(
                clean(base_row.get("selection")).upper()
            )
            & pd.to_numeric(
                raw["line_group"], errors="coerce"
            ).round(4).eq(
                round(float(base_row.get("line")), 4)
            )
        ].copy()
        if matches.empty:
            continue
        source = matches.iloc[-1]
        rec = {
            "market_reference_probability": (
                num(base_row.get("market_reference_probability_pct")) or 50.0
            ) / 100.0,
            "raw_market_support": num(source.get("raw_market_support")),
            "sportsbook_count": num(source.get("sportsbook_count")),
            "line_value": num(source.get("line_group")),
            "selection_direction": (
                1.0
                if clean(source.get("selection_canonical")).upper() == "OVER"
                else -1.0
                if clean(source.get("selection_canonical")).upper() == "UNDER"
                else 0.0
            ),
            "old_score": num(source.get("evidence_score")),
        }
        frame = pd.DataFrame([rec])
        X = lab.design(
            frame, model["features"], model["scaler"]
        )
        p = float(game.predict(model["beta"], X)[0])
        market_p = rec["market_reference_probability"]
        rows.append({
            "model_version": MODEL_VERSION,
            "lane_key": LANE_KEY,
            "game_key": clean(base_row.get("game_key")),
            "selection": clean(base_row.get("selection")),
            "selection_key": clean(base_row.get("selection_key")),
            "line": num(base_row.get("line")),
            "event_start": clean(base_row.get("event_start")),
            "american_odds": num(base_row.get("american_odds")),
            "market_reference_probability_pct": round(100 * market_p, 3),
            "current_v2_probability_pct": num(
                base_row.get("calibrated_win_probability_pct")
            ),
            "challenger_probability_pct": round(100 * p, 3),
            "challenger_minus_market_pp": round(100 * (p - market_p), 3),
            "historical_status": lane.get("status"),
            "chosen_inner_consensus": model["label"],
            "chosen_l2": model["l2"],
            "features": model["features"],
            "shadow_decision": "RESEARCH_CHALLENGER_ONLY",
            "live_pick_changed": False,
        })

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "lane_key": LANE_KEY,
        "historical_status": lane.get("status"),
        "chosen_inner_consensus": model["label"],
        "chosen_l2": model["l2"],
        "features": model["features"],
        "rows": rows,
    }


def key_for(row):
    return "|".join([
        MODEL_VERSION,
        clean(row.get("game_key")),
        clean(row.get("selection")).upper(),
        f"{float(row.get('line')):.4f}",
    ])


def capture(current):
    existing = canonical()
    added = 0
    for row in current.get("rows") or []:
        start = pd.to_datetime(
            row.get("event_start"), errors="coerce", utc=True
        )
        if pd.isna(start) or start.to_pydatetime() <= now():
            continue
        key = key_for(row)
        if key in existing:
            continue
        event = {
            "event_type": "ENTRY",
            "forward_key": key,
            "model_version": MODEL_VERSION,
            "captured_at": now_iso(),
            **row,
            "status": "PENDING",
            "grade": "PENDING",
        }
        append_jsonl(LEDGER, event)
        existing[key] = event
        added += 1
    return {
        "entries_added": added,
        "ledger_unique": len(canonical()),
    }


def result_lookup():
    path = game.HISTORY_FILES[SPORT]
    if not path.exists():
        return {}
    d = pd.read_csv(path, low_memory=False)
    d = d[
        d["lane"].astype(str).str.upper().eq("GAME")
        & d["market"].astype(str).str.upper().eq(MARKET)
        & d["grade"].astype(str).str.upper().isin(["WIN", "LOSS"])
    ].copy()
    out = {}
    for _, row in d.iterrows():
        line = num(row.get("line"))
        if line is None:
            continue
        key = (
            clean(row.get("game_key")),
            clean(row.get("selection")).upper(),
            round(line, 4),
        )
        out[key] = {
            "grade": clean(row.get("grade")).upper(),
            "snapshot_at": clean(row.get("snapshot_at")),
        }
    return out


def settle():
    existing = canonical()
    results = result_lookup()
    settled = 0
    for key, row in existing.items():
        if clean(row.get("grade")).upper() in {"WIN", "LOSS"}:
            continue
        line = num(row.get("line"))
        if line is None:
            continue
        match = results.get((
            clean(row.get("game_key")),
            clean(row.get("selection")).upper(),
            round(line, 4),
        ))
        if not match:
            continue
        append_jsonl(LEDGER, {
            "event_type": "SETTLED",
            "forward_key": key,
            "status": "SETTLED",
            "grade": match["grade"],
            "settled_at": now_iso(),
            "grade_snapshot_at": match.get("snapshot_at"),
        })
        settled += 1
    return settled


def mean(vals):
    vals = [float(x) for x in vals if x is not None]
    return None if not vals else round(sum(vals) / len(vals), 6)


def brier(pct, y):
    p = num(pct)
    if p is None:
        return None
    p = min(0.999999, max(0.000001, p / 100.0))
    return (p - y) ** 2


def logloss(pct, y):
    p = num(pct)
    if p is None:
        return None
    p = min(0.999999, max(0.000001, p / 100.0))
    return -(y * math.log(p) + (1-y) * math.log(1-p))


def lcb90(vals):
    vals = [float(x) for x in vals if x is not None]
    if len(vals) < 2:
        return len(vals), None
    avg = sum(vals) / len(vals)
    var = sum((x-avg)**2 for x in vals) / (len(vals)-1)
    se = math.sqrt(max(0.0, var) / len(vals))
    return len(vals), round(avg - 1.645 * se, 6)


def summary(current, capture_result, settled_now):
    rows = list(canonical().values())
    settled = [
        row for row in rows
        if clean(row.get("grade")).upper() in {"WIN", "LOSS"}
    ]
    c_adv = []
    current_adv = []
    log_adv = []
    for row in settled:
        y = 1 if clean(row.get("grade")).upper() == "WIN" else 0
        mb = brier(row.get("market_reference_probability_pct"), y)
        cb = brier(row.get("challenger_probability_pct"), y)
        vb = brier(row.get("current_v2_probability_pct"), y)
        ml = logloss(row.get("market_reference_probability_pct"), y)
        cl = logloss(row.get("challenger_probability_pct"), y)
        if mb is not None and cb is not None:
            c_adv.append(mb-cb)
        if vb is not None and cb is not None:
            current_adv.append(vb-cb)
        if ml is not None and cl is not None:
            log_adv.append(ml-cl)

    n, brier_lcb = lcb90(c_adv)
    _, current_lcb = lcb90(current_adv)
    _, log_lcb = lcb90(log_adv)
    if len(settled) < 50 or n < 30:
        proof = "BUILDING_FORWARD_SAMPLE"
    elif (
        mean(c_adv) is not None and mean(c_adv) > 0
        and mean(current_adv) is not None and mean(current_adv) > 0
        and mean(log_adv) is not None and mean(log_adv) > 0
        and brier_lcb is not None and brier_lcb > 0
        and current_lcb is not None and current_lcb > 0
        and log_lcb is not None and log_lcb > 0
    ):
        proof = "CHALLENGER_REVIEW_CANDIDATE"
    else:
        proof = "CHALLENGER_NOT_PROVEN"

    return {
        "generated_at": now_iso(),
        "status": "READY",
        "model_version": MODEL_VERSION,
        "lane_key": LANE_KEY,
        "current": current,
        "capture": capture_result,
        "settled_now": settled_now,
        "forward": {
            "tracked": len(rows),
            "settled": len(settled),
            "wins": sum(
                clean(r.get("grade")).upper() == "WIN"
                for r in settled
            ),
            "losses": sum(
                clean(r.get("grade")).upper() == "LOSS"
                for r in settled
            ),
            "mean_brier_advantage_vs_market": mean(c_adv),
            "brier_advantage_vs_market_lcb90": brier_lcb,
            "mean_brier_advantage_vs_current_v2": mean(current_adv),
            "brier_advantage_vs_current_v2_lcb90": current_lcb,
            "mean_logloss_advantage_vs_market": mean(log_adv),
            "logloss_advantage_vs_market_lcb90": log_lcb,
            "proof_status": proof,
            "minimum_settled_for_review": 50,
            "minimum_independent_games_for_review": 30,
            "automatic_promotion": False,
        },
        "rules": [
            "This is a forward-only CFB Total challenger; it does not change live Best Bets.",
            "Historical feature/L2 choice was locked before forward tracking began.",
            "Only pregame qualifying CFB Total candidates are frozen.",
            "The challenger must beat both market reference and current V2 with positive lower-confidence Brier/log-loss evidence before review.",
            "No automatic promotion occurs.",
        ],
    }


def main():
    model, lane = fit_full()
    current = current_payload(model, lane)
    capture_result = capture(current)
    settled_now = settle()
    payload = summary(current, capture_result, settled_now)
    for path in (
        CURRENT_OUT,
        PUBLIC / "betting_v2_game_challenger_current.json",
    ):
        write_json(path, current)
    for path in (
        SUMMARY,
        PUBLIC / "betting_v2_game_challenger_forward.json",
    ):
        write_json(path, payload)
    if DIST.exists():
        write_json(
            DIST / "betting_v2_game_challenger_current.json",
            current,
        )
        write_json(
            DIST / "betting_v2_game_challenger_forward.json",
            payload,
        )
    print(json.dumps({
        "status": payload["status"],
        "current_status": current.get("status"),
        "current_rows": len(current.get("rows") or []),
        "capture": capture_result,
        "forward": payload["forward"],
    }, indent=2))


if __name__ == "__main__":
    main()
