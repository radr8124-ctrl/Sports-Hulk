from pathlib import Path
from datetime import datetime, timezone
import hashlib
import pandas as pd

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"
HISTORY = HERE / "history"

HISTORY.mkdir(parents=True, exist_ok=True)

src = DERIVED / "MLB_DECISION_BRAIN_MARKET_RESEARCH.csv"

if not src.exists():
    raise SystemExit(
        "Missing MLB_DECISION_BRAIN_MARKET_RESEARCH.csv"
    )

d = pd.read_csv(src, low_memory=False)

if "gamePk" not in d.columns:
    raise SystemExit("Market research board has no gamePk")

# One game must appear exactly once.
if d["gamePk"].duplicated().any():
    raise SystemExit(
        "ERROR: duplicate gamePk rows in market research board"
    )

now = datetime.now(timezone.utc).isoformat()

d["market_research_timestamp_utc"] = now

# Research snapshot ID is independent of the official prediction ID.
payload = (
    d.to_csv(index=False) + now
).encode()

sid = hashlib.sha256(
    payload
).hexdigest()[:16]

d["market_research_snapshot_id"] = sid

out = HISTORY / "MLB_MARKET_RESEARCH_HISTORY.csv"

if out.exists():
    old = pd.read_csv(
        out,
        low_memory=False,
    )

    merged = pd.concat(
        [old, d],
        ignore_index=True,
        sort=False,
    )
else:
    merged = d.copy()

merged.to_csv(
    out,
    index=False,
)

snap = (
    HISTORY /
    f"MLB_MARKET_RESEARCH_SNAPSHOT_{sid}.csv"
)

d.to_csv(
    snap,
    index=False,
)

print(
    "SPORTS HULK MARKET RESEARCH SNAPSHOT: DONE"
)
print("Snapshot ID:", sid)
print("Rows saved:", len(d))
print(
    "Unique gamePk:",
    d["gamePk"].nunique()
)
print(
    "History rows:",
    len(merged)
)

print("\nAlignment saved:")
print(
    d["market_research_alignment"]
    .value_counts(dropna=False)
    .to_string()
)
