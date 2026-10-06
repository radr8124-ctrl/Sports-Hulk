#!/usr/bin/env python3
from pathlib import Path
import argparse
import subprocess
import sys

ROOT=Path("/home/ubuntu/sports-hulk")

parser=argparse.ArgumentParser()
parser.add_argument("--mode",choices=["full","results-only"],default="full")
args=parser.parse_args()

full_steps=[
    "nfl_live/build_survivor_board_from_decisions.py",
    "nfl_live/build_nfl_context.py",
    "nfl_live/build_nfl_weather.py",
    "nfl_live/build_hulk_survivor_context.py",
    "nfl_live/build_hulk_survivor_decision.py",
    "nfl_live/build_survivor_future_value.py",
]
result_steps=[
    "nfl_live/update_survivor_entry_results.py",
    "nfl_live/update_survivor_current_week.py",
]

# The Week 3 pool finalizer is a one-time migration from the imported
# double-pick sheet to final Week 3 status. Do not rerun it every week.
pool_summary=ROOT/"nfl_live/survivor_pool/derived/LATEST_OFFICIAL_POOL.json"
needs_week3_finalize=False
if pool_summary.exists():
    try:
        import json
        meta=json.loads(pool_summary.read_text())
        needs_week3_finalize=(
            int(meta.get("pool_week",3) or 3) <= 3
            or not bool(meta.get("week3_finalized"))
        )
    except Exception:
        needs_week3_finalize=False

if needs_week3_finalize:
    result_steps.insert(0,"nfl_live/build_survivor_pool_status.py")

steps=(full_steps+result_steps) if args.mode=="full" else result_steps

for rel in steps:
    print(f"=== SURVIVOR STEP: {rel} ===",flush=True)
    subprocess.run(
        [sys.executable,str(ROOT/rel)],
        cwd=ROOT,
        check=True,
    )

print(f"RESULT: SURVIVOR_REFRESH_READY mode={args.mode}")
