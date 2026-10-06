#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
OUT = OUT_DIR / "PROP_V2_MARKET_SEGMENTS.json"
PUBLIC = ROOT / "commercial_web" / "public" / "prop_v2_market_segments.json"
DIST = ROOT / "commercial_web" / "dist" / "prop_v2_market_segments.json"

if str(OUT_DIR) not in sys.path:
    sys.path.insert(0, str(OUT_DIR))
import build_prop_v2 as prop

MIN_ROWS = 40
MIN_BLOCKS = 10


def main():
    lanes = {}
    for lane_key, cfg in prop.LANES.items():
        frame = prop.build_history(cfg)
        segments = {}
        if not frame.empty and "market_subtype" in frame.columns:
            for market, group in frame.groupby("market_subtype"):
                blocks = int(group["block_key"].nunique())
                n = int(len(group))
                if n < MIN_ROWS or blocks < MIN_BLOCKS:
                    continue
                validation = prop.walk_forward(group.sort_values("time").reset_index(drop=True), cfg)
                segments[str(market)] = {
                    "rows": n,
                    "independent_blocks": blocks,
                    **validation,
                    "automatic_live_change": False,
                }
        lanes[lane_key] = {
            "history_n": int(len(frame)),
            "eligible_segment_count": len(segments),
            "segments": segments,
        }

    payload = {
        "status": "READY",
        "method": "MARKET_SUBTYPE_ROLLING_ORIGIN_RESEARCH",
        "minimum_rows": MIN_ROWS,
        "minimum_independent_blocks": MIN_BLOCKS,
        "lanes": lanes,
        "rules": [
            "Market-type models are research-only and never replace the parent lane automatically.",
            "Each subtype must have at least 40 historical decisions and 10 independent game blocks before testing.",
            "The same de-vigged market reference and paired confidence tests used by parent V2 are retained.",
            "Any promising subtype still requires its own forward sample before deployment review.",
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
            lane: {
                "eligible": data["eligible_segment_count"],
                "segments": {
                    market: {
                        "rows": val.get("rows"),
                        "blocks": val.get("independent_blocks"),
                        "source": val.get("deployment_probability_source"),
                        "confidence": val.get("historical_edge_confidence"),
                        "selection": val.get("selection_rule_status"),
                        "metrics": val.get("metrics", {}),
                    }
                    for market, val in data["segments"].items()
                },
            }
            for lane, data in lanes.items()
        },
    }, indent=2))


if __name__ == "__main__":
    main()
