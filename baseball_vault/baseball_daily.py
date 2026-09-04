from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import subprocess, sys, json
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
LATEST = HERE / "latest"
HISTORY = HERE / "history"
LOGS = HERE / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
HISTORY.mkdir(parents=True, exist_ok=True)

TZ = ZoneInfo("America/New_York")

def log(msg):
    stamp = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"[{stamp}] {msg}"
    print(line)
    lf = LOGS / f"baseball_daily_{datetime.now(TZ).date().isoformat()}.log"
    with lf.open("a") as f:
        f.write(line + "\n")

def run(script, required=True):
    log(f"RUN {script}")
    rc = subprocess.call([sys.executable, str(HERE / script)], cwd=str(ROOT))
    if rc != 0 and required:
        raise SystemExit(f"{script} failed with code {rc}")
    return rc

def mtime(path):
    p = Path(path)
    return p.stat().st_mtime if p.exists() else 0

def slate_signature(board):
    ids = sorted(str(x) for x in board["gamePk"].dropna().tolist()) if "gamePk" in board else []
    return "|".join(ids)

def already_saved_today(board):
    hist = HISTORY / "MLB_PREDICTION_HISTORY.csv"
    if not hist.exists():
        return False
    try:
        h = pd.read_csv(hist, low_memory=False)
    except Exception:
        return False
    if "prediction_timestamp_utc" not in h.columns or "gamePk" not in h.columns:
        return False
    ts = pd.to_datetime(h["prediction_timestamp_utc"], errors="coerce", utc=True)
    local_dates = ts.dt.tz_convert(TZ).dt.date
    today = datetime.now(TZ).date()
    h = h[local_dates == today].copy()
    if h.empty:
        return False
    target = slate_signature(board)
    if "snapshot_id" in h.columns:
        for sid, g in h.groupby("snapshot_id"):
            if slate_signature(g) == target:
                return True
    return False

def main():
    log("=== SPORTS HULK BASEBALL DAILY START ===")

    market_files = [
        LATEST / "MLB_SGO_MARKETS.csv",
        LATEST / "MLB_ODDS_API_MARKETS.csv",
    ]
    before = {str(f): mtime(f) for f in market_files}

    run("collect_nightly.py")

    schedule = LATEST / "MLB_SCHEDULE.csv"
    if not schedule.exists():
        raise SystemExit("Collector did not create MLB_SCHEDULE.csv")

    after = {str(f): mtime(f) for f in market_files}
    refreshed = [f for f in market_files if after[str(f)] > before[str(f)]]

    if not refreshed:
        log("WARNING: neither live odds file refreshed. Snapshot will NOT be saved.")
        run("result_refresh.py", required=False)
        run("result_grader.py", required=False)
        run("calibration_report.py", required=False)
        log("=== DAILY END — NO PREGAME SNAPSHOT DUE TO STALE ODDS ===")
        return

    log("Live odds refresh detected: " + ", ".join(f.name for f in refreshed))

    run("matchup_engine.py")

    boardf = HERE / "derived" / "MLB_MATCHUP_BOARD.csv"
    board = pd.read_csv(boardf, low_memory=False)

    if already_saved_today(board):
        log("Official prediction snapshot already exists for today's current slate; duplicate save skipped.")
    else:
        run("prediction_logger.py")
        log("Official prediction snapshot saved.")

    # Build the richer research layers only after the official pregame snapshot is protected.
    # These layers are optional so a research/reporting issue cannot corrupt the core daily logger.
    run("run_intelligence_build.py", required=False)
    run("run_decision_brain_build.py", required=False)

    # Market movement research layer.
    # Runs only after the official prediction snapshot is protected.
    # This research does NOT alter the production prediction or decision.
    run("market_history_builder.py", required=False)
    run("core_market_builder.py", required=False)
    run("dedup_core_market_builder.py", required=False)
    run("market_consensus_builder.py", required=False)
    run("market_signal_builder.py", required=False)
    run("market_signal_overlay.py", required=False)
    run("market_research_logger.py", required=False)
    run("market_research_grader.py", required=False)

    run("run_market_context_build.py", required=False)

    run("result_refresh.py", required=False)
    run("result_grader.py", required=False)
    run("calibration_report.py", required=False)

    log("=== SPORTS HULK BASEBALL DAILY DONE ===")

if __name__ == "__main__":
    main()
