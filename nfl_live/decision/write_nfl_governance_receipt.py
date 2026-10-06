#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json

ROOT=Path("/home/ubuntu/sports-hulk")
OUT=ROOT/"nfl_live"/"decision"/"NFL_REFRESH_GOVERNANCE_RECEIPT.json"

ap=argparse.ArgumentParser()
ap.add_argument("--mode",required=True)
ap.add_argument("--window-active",choices=["true","false"],required=True)
ap.add_argument("--paid-market-refresh",choices=["true","false"],required=True)
ap.add_argument("--free-context-refresh",choices=["true","false"],required=True)
args=ap.parse_args()

receipt={
    "generated_at":datetime.now(timezone.utc).isoformat(),
    "mode":args.mode,
    "governed_window_active":args.window_active=="true",
    "paid_market_refresh":args.paid_market_refresh=="true",
    "free_context_refresh":args.free_context_refresh=="true",
}
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
print("NFL GOVERNANCE MODE:",receipt["mode"])
print("PAID MARKET REFRESH:",receipt["paid_market_refresh"])
print("FREE CONTEXT REFRESH:",receipt["free_context_refresh"])
