from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))

import build_prop_v2 as prop_v2
import build_prop_v2_forward as forward

SEGMENT_LANE_KEY = "NHL_PRIZEPICKS_POINTS_SEGMENT"
SEGMENT_MARKET = "PLAYER_TOTAL_POINTS"
SEGMENT_VERSION = "NHL_PRIZEPICKS_POINTS_SEGMENT_V1"

SEGMENTS = OUT_DIR / "PROP_V2_MARKET_SEGMENTS.json"
CURRENT = OUT_DIR / "PROP_V2_POINTS_SEGMENT_CURRENT.json"
LEDGER = OUT_DIR / "PROP_V2_POINTS_SEGMENT_FORWARD_LEDGER.jsonl"
SUMMARY = OUT_DIR / "PROP_V2_POINTS_SEGMENT_FORWARD_SUMMARY.json"
PUBLIC = ROOT / "commercial_web" / "public" / "prop_v2_points_segment_forward.json"
DIST = ROOT / "commercial_web" / "dist" / "prop_v2_points_segment_forward.json"


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def build_current():
    segments = read_json(SEGMENTS)
    validation = (
        segments.get("lanes", {})
        .get("NHL_PRIZEPICKS", {})
        .get("segments", {})
        .get(SEGMENT_MARKET, {})
    )
    if validation.get("status") != "READY":
        return {
            "generated_at": forward.now_iso(),
            "status": "WAITING",
            "mode": "FORWARD_SHADOW",
            "model_version": SEGMENT_VERSION,
            "summary": {"candidates": 0},
            "picks": [],
        }

    cfg = prop_v2.LANES["NHL_PRIZEPICKS"]
    rows = prop_v2.build_current_lane(SEGMENT_LANE_KEY, cfg, validation)
    rows = [row for row in rows if row.get("market_subtype") == SEGMENT_MARKET]

    for row in rows:
        row["model_version"] = SEGMENT_VERSION
        row["segment_model"] = SEGMENT_MARKET
        row["segment_historical_edge_confidence"] = validation.get(
            "historical_edge_confidence"
        )
        row["segment_independent_blocks"] = validation.get("independent_blocks")
        row["segment_walk_forward_n"] = validation.get("walk_forward_n")
        row["live_pick_changed"] = False

    return {
        "generated_at": forward.now_iso(),
        "status": "READY",
        "mode": "FORWARD_SHADOW",
        "model_version": SEGMENT_VERSION,
        "lane_key": SEGMENT_LANE_KEY,
        "market_segment": SEGMENT_MARKET,
        "historical_status": {
            "history_n": validation.get("history_n"),
            "independent_blocks": validation.get("independent_blocks"),
            "walk_forward_n": validation.get("walk_forward_n"),
            "probability_source": validation.get("deployment_probability_source"),
            "historical_edge_confidence": validation.get(
                "historical_edge_confidence"
            ),
            "selection_rule_status": validation.get("selection_rule_status"),
            "core_vs_reference": (
                validation.get("paired_comparisons", {})
                .get("core_vs_reference", {})
            ),
        },
        "summary": {
            "candidates": len(rows),
            "fair_market_candidates": sum(
                row.get("market_reference_type") == "DEVIG_FAIR"
                for row in rows
            ),
            "three_plus_book_candidates": sum(
                int(row.get("devig_paired_books") or 0) >= 3
                for row in rows
            ),
            "shadow_monitors": sum(
                row.get("shadow_decision") == "SHADOW_MONITOR"
                for row in rows
            ),
        },
        "picks": rows,
        "rules": [
            "Research-only forward experiment for NHL PrizePicks Player Total Points.",
            "All eligible segment predictions are frozen; no cherry-picking after results.",
            "Same-book de-vig fair probability is the market reference.",
            "No live recommendation is changed by this experiment.",
            "Promotion requires the global forward-accountability confidence gates.",
        ],
    }


def main():
    current_payload = build_current()
    write_json(CURRENT, current_payload)

    # Reuse the production append-only capture/settlement engine with isolated files.
    forward.CURRENT = CURRENT
    forward.LEDGER = LEDGER
    forward.SUMMARY = SUMMARY
    forward.PUBLIC = PUBLIC
    forward.DIST = DIST

    cfg = prop_v2.LANES["NHL_PRIZEPICKS"]
    prop_v2.MODEL_VERSION = SEGMENT_VERSION
    prop_v2.LANES = {SEGMENT_LANE_KEY: cfg}

    if current_payload.get("status") == "READY":
        forward.main()
    else:
        write_json(SUMMARY, current_payload)
        write_json(PUBLIC, current_payload)
        if DIST.parent.exists():
            write_json(DIST, current_payload)
        print(json.dumps(current_payload, indent=2))


if __name__ == "__main__":
    main()
