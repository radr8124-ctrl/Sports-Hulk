from pathlib import Path
from datetime import datetime
import json, os, sys
import requests
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "parlay_live" / "derived"
HIST = ROOT / "parlay_live" / "history"
OUT.mkdir(parents=True, exist_ok=True)
HIST.mkdir(parents=True, exist_ok=True)

SPORTS = {
    "NFL": ("americanfootball_nfl", "NFL_PARLAY_MARKET_RAW.csv", "nfl_props_raw"),
    "MLB": ("baseball_mlb", "MLB_PARLAY_MARKET_RAW.csv", "mlb_props_raw"),
}

def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            k,v=line.split("=",1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def fetch(label, limit=5000):
    load_env()
    key=os.getenv("PARLAY_API_KEY")
    if not key:
        raise SystemExit("PARLAY_API_KEY missing")
    sport_key, csv_name, stem = SPORTS[label]
    url=f"https://parlay-api.com/v1/sports/{sport_key}/props"
    r=requests.get(url, headers={"X-API-Key": key}, params={"limit": limit}, timeout=60)
    print(f"{label} HTTP: {r.status_code}")
    if r.status_code != 200:
        print(r.text[:1000])
        r.raise_for_status()
    data=r.json()
    if isinstance(data, dict):
        rows = data.get("data") or data.get("props") or data.get("results") or []
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file=HIST/f"{stem}_{stamp}.json"
    raw_file.write_text(json.dumps(data, indent=2))
    df=pd.json_normalize(rows)
    csv_file=OUT/csv_name
    df.to_csv(csv_file, index=False)
    print(f"{label} rows: {len(df):,}")
    print(f"{label} raw:  {raw_file}")
    print(f"{label} csv:  {csv_file}")
    return len(df)

if __name__=="__main__":
    args=[x.upper() for x in sys.argv[1:]]
    if not args:
        print("Usage: python parlay_live/build_parlay_props_governed.py MLB|NFL|ALL")
        raise SystemExit(0)
    labels=list(SPORTS) if "ALL" in args else args
    for label in labels:
        if label not in SPORTS:
            raise SystemExit(f"Unknown sport: {label}")
    print("="*72)
    print("SPORTS HULK — PARLAY MARKET COLLECTOR")
    print("="*72)
    print("NOTE: /props currently costs 3 credits per sport call.")
    for label in labels:
        fetch(label)
    print("RESULT: PASS")
