#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="/home/ubuntu/sports-hulk"
DEC="$ROOT/nfl_live/decision"
GOOD="$DEC/last_good"
LOG="$DEC/logs"

cd "$ROOT"

mkdir -p "$GOOD" "$LOG"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOGFILE="$LOG/NFL_REFRESH_$STAMP.log"

exec > >(tee -a "$LOGFILE") 2>&1

exec 9>"$DEC/.refresh.lock"

if ! flock -n 9; then
    echo "Another NFL refresh is already running."
    exit 0
fi


restore_last_good() {

    echo
    echo "REFRESH FAILED — restoring last-good UI outputs."

    for f in "$GOOD"/*; do
        [ -f "$f" ] || continue
        cp "$f" "$DEC/$(basename "$f")"
    done
}


trap restore_last_good ERR


echo "=================================================="
echo "SPORTS HULK NFL GOVERNED REFRESH"
echo "UTC: $(date -u)"
echo "=================================================="


# --------------------------------------------------
# Only spend provider resources near NFL games.
# Window:
#   6 hours after kickoff
#   through 18 hours before kickoff
# --------------------------------------------------

WINDOW=$(
"$ROOT/.venv/bin/python" - <<'PY'
from datetime import datetime, timezone, timedelta
import requests

now = datetime.now(timezone.utc)

try:
    r = requests.get(
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard",
        timeout=15,
    )

    r.raise_for_status()

    events = r.json().get(
        "events",
        [],
    )

    active = False

    for e in events:

        start = e.get("date")

        if not start:
            continue

        dt = datetime.fromisoformat(
            start.replace(
                "Z",
                "+00:00",
            )
        )

        if (
            now - timedelta(hours=6)
            <= dt
            <= now + timedelta(hours=18)
        ):
            active = True
            break

    print(
        "YES"
        if active
        else "NO"
    )

except Exception:
    # Fail safe: don't spend provider
    # quota when schedule verification fails.
    print("NO")
PY
)


if [ "$WINDOW" != "YES" ]; then

    echo
    echo "No NFL game inside governed paid-market window."
    echo "Skipping paid/quota-sensitive market refresh."
    echo "Refreshing free NFL context and availability only."

    PLAYER_STATS="nfl_live/player_context/raw/player_stats.parquet"
    REFRESH_FREE="YES"

    if [ -f "$PLAYER_STATS" ]; then
        AGE=$(python3 -c 'from pathlib import Path; from time import time; p=Path("/home/ubuntu/sports-hulk/nfl_live/player_context/raw/player_stats.parquet"); print(int(time()-p.stat().st_mtime))')
        if [ "$AGE" -lt 21600 ]; then
            REFRESH_FREE="NO"
        fi
    fi

    if [ "$REFRESH_FREE" = "YES" ]; then
        SPORTS_LABEL=NFL-free-sources SPORTS_MAX_SECONDS=45 \
          "$ROOT/scripts/sports-safe-run.sh" \
          "$ROOT/.venv/bin/python" \
          nfl_live/player_context/build_free_player_sources.py \
          || echo "WARNING: free NFL source refresh failed; prior free context preserved."
    else
        echo "Free player sources are recent; reuse current cache."
    fi

    SPORTS_LABEL=NFL-free-status SPORTS_MAX_SECONDS=20 \
      "$ROOT/scripts/sports-safe-run.sh" \
      "$ROOT/.venv/bin/python" \
      nfl_live/decision/refresh_nfl_free_status.py \
      || echo "WARNING: free NFL injury refresh failed; prior injury file preserved."

    SPORTS_LABEL=NFL-free-context-v2 SPORTS_MAX_SECONDS=30 \
      "$ROOT/scripts/sports-safe-run.sh" \
      "$ROOT/.venv/bin/python" \
      nfl_live/fusion/build_nfl_player_context_v2.py \
      || echo "WARNING: free NFL player-context rebuild failed; prior context preserved."

    SPORTS_LABEL=NFL-free-fantasy SPORTS_MAX_SECONDS=20 \
      "$ROOT/scripts/sports-safe-run.sh" \
      "$ROOT/.venv/bin/python" \
      nfl_live/decision/build_nfl_fantasy_watchlist.py \
      || echo "WARNING: NFL fantasy refresh failed; prior fantasy output preserved."

    SPORTS_LABEL=NFL-survivor-results SPORTS_MAX_SECONDS=20 \
      "$ROOT/scripts/sports-safe-run.sh" \
      "$ROOT/.venv/bin/python" \
      nfl_live/refresh_survivor.py --mode results-only \
      || echo "WARNING: Survivor result refresh failed; prior Survivor state preserved."

    "$ROOT/.venv/bin/python" \
      nfl_live/decision/write_nfl_governance_receipt.py \
      --mode FREE_CONTEXT_ONLY \
      --window-active false \
      --paid-market-refresh false \
      --free-context-refresh true

    exit 0
fi


echo
echo "NFL game window ACTIVE."


# --------------------------------------------------
# Refresh free player context occasionally,
# not every hourly market refresh.
# --------------------------------------------------

PLAYER_STATS="nfl_live/player_context/raw/player_stats.parquet"

REFRESH_PLAYER="YES"

if [ -f "$PLAYER_STATS" ]; then

    AGE=$(
      python3 - <<'PY'
from pathlib import Path
from time import time

p = Path(
    "/home/ubuntu/sports-hulk/"
    "nfl_live/player_context/raw/"
    "player_stats.parquet"
)

print(
    int(
        time()
        - p.stat().st_mtime
    )
)
PY
    )

    if [ "$AGE" -lt 21600 ]; then
        REFRESH_PLAYER="NO"
    fi
fi


if [ "$REFRESH_PLAYER" = "YES" ]; then

    echo
    echo "=== FREE PLAYER CONTEXT ==="

    "$ROOT/.venv/bin/python" \
      nfl_live/player_context/build_free_player_sources.py
else

    echo
    echo "Free player context is recent; reuse current cache."
fi


echo
echo "=== PRIZEPICKS / DFS LIVE QUALITY ==="

"$ROOT/.venv/bin/python" \
  nfl_live/multisource/audit_nfl_multisource_quality.py


echo
echo "=== DFS FUSION ==="

"$ROOT/.venv/bin/python" \
  nfl_live/fusion/build_nfl_dfs_fusion.py


echo
echo "=== MULTI-BOOK PLAYER PROPS ==="

"$ROOT/.venv/bin/python" \
  nfl_live/fusion/build_nfl_multibook_props.py


echo
echo "=== PLAYER CONTEXT ==="

"$ROOT/.venv/bin/python" \
  nfl_live/fusion/build_nfl_player_context_v2.py


echo
echo "=== PLAYER IDENTITY LOCK ==="

"$ROOT/.venv/bin/python" \
  nfl_live/identity/build_player_identity_lock.py


echo
echo "=== GAME MARKET FUSION ==="

"$ROOT/.venv/bin/python" \
  nfl_live/game_fusion/build_nfl_game_betting_fusion.py


echo
echo "=== DECISION BRAIN ==="

"$ROOT/.venv/bin/python" \
  nfl_live/decision/build_nfl_decision_brain.py


echo
echo "=== SAMPLE / SANITY GATES ==="

"$ROOT/.venv/bin/python" \
  nfl_live/decision/apply_decision_sanity_gates.py


echo
echo "=== SURVIVOR GOVERNED REFRESH ==="

SPORTS_LABEL=NFL-survivor-full SPORTS_MAX_SECONDS=60 \
  "$ROOT/scripts/sports-safe-run.sh" \
  "$ROOT/.venv/bin/python" \
  nfl_live/refresh_survivor.py --mode full \
  || echo "WARNING: Survivor refresh failed; prior Survivor state preserved."


echo
echo "=== NFL FANTASY WATCHLIST ==="

SPORTS_LABEL=NFL-fantasy SPORTS_MAX_SECONDS=20 \
  "$ROOT/scripts/sports-safe-run.sh" \
  "$ROOT/.venv/bin/python" \
  nfl_live/decision/build_nfl_fantasy_watchlist.py \
  || echo "WARNING: NFL fantasy watchlist refresh failed; prior fantasy output preserved."

echo
echo "=== PARLAY ENGINE ==="

"$ROOT/.venv/bin/python" \
  nfl_live/decision/build_nfl_parlays.py


echo
echo "=== PRODUCTION OUTPUT VALIDATION ==="

"$ROOT/.venv/bin/python" - <<'PY'
from pathlib import Path
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "nfl_live/decision"

required = [
    "NFL_GAME_FINALISTS.csv",
    "NFL_PROP_FINALISTS.csv",
    "NFL_PRIZEPICKS_FINALISTS.csv",
    "NFL_FANTASY_WATCHLIST.csv",
    "NFL_PARLAYS_TODAY.csv",
]

for name in required:

    p = DEC / name

    if not p.exists():
        raise SystemExit(
            f"Missing production output: {name}"
        )


props = pd.read_csv(
    DEC / "NFL_PROP_FINALISTS.csv",
    low_memory=False,
)

parlays = pd.read_csv(
    DEC / "NFL_PARLAYS_TODAY.csv",
    low_memory=False,
)


if not props.empty:

    samples = pd.to_numeric(
        props[
            "meaningful_completed_games"
        ],
        errors="coerce",
    )

    if not samples.ge(2).all():
        raise SystemExit(
            "Prop sample gate violation."
        )


if not parlays.empty:

    if not (
        parlays[
            "correlation_status"
        ]
        .eq(
            "VERIFIED_DIFFERENT_GAMES"
        )
        .all()
    ):
        raise SystemExit(
            "Parlay correlation gate violation."
        )

    if (
        parlays[
            "leg1_event"
        ]
        .astype(str)
        .eq(
            parlays[
                "leg2_event"
            ]
            .astype(str)
        )
        .any()
    ):
        raise SystemExit(
            "Same-game qualified parlay detected."
        )


print(
    "GAME FINALISTS:",
    len(
        pd.read_csv(
            DEC
            / "NFL_GAME_FINALISTS.csv"
        )
    ),
)

print(
    "PROP FINALISTS:",
    len(props),
)

print(
    "PRIZEPICKS FINALISTS:",
    len(
        pd.read_csv(
            DEC
            / "NFL_PRIZEPICKS_FINALISTS.csv"
        )
    ),
)

print(
    "PARLAYS TODAY:",
    len(parlays),
)

print(
    "PRODUCTION VALIDATION: PASS"
)
PY


echo
echo "=== COMMIT LAST-GOOD OUTPUTS ==="

for f in \
  NFL_GAME_DECISIONS.csv \
  NFL_GAME_FINALISTS.csv \
  NFL_PROP_DECISIONS.csv \
  NFL_PROP_FINALISTS.csv \
  NFL_PRIZEPICKS_DECISIONS.csv \
  NFL_PRIZEPICKS_FINALISTS.csv \
  NFL_FANTASY_WATCHLIST.csv \
  NFL_PARLAY_CANDIDATES.csv \
  NFL_PARLAYS_TODAY.csv \
  NFL_PRIZEPICKS_CARDS.csv \
  NFL_DECISION_BRAIN_RECEIPT.json \
  NFL_DECISION_SANITY_RECEIPT.json \
  NFL_PARLAY_RECEIPT.json
do
    if [ -f "$DEC/$f" ]; then
        cp \
          "$DEC/$f" \
          "$GOOD/$f"
    fi
done


"$ROOT/.venv/bin/python" \
  nfl_live/decision/write_nfl_governance_receipt.py \
  --mode FULL_GOVERNED_REFRESH \
  --window-active true \
  --paid-market-refresh true \
  --free-context-refresh true

echo
echo "=================================================="
echo "NFL GOVERNED REFRESH: PASS"
echo "=================================================="
