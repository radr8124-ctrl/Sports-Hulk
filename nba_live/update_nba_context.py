#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timedelta, timezone
import subprocess


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

PY = (
    ROOT
    / ".venv"
    / "bin"
    / "python"
)

SCRIPT = (
    ROOT
    / "nba_live"
    / "build_nba_history.py"
)


today = datetime.now(
    timezone.utc
).date()


start = (
    today
    - timedelta(
        days=3
    )
)


subprocess.run(
    [
        str(
            PY
        ),
        str(
            SCRIPT
        ),
        "--start",
        start.isoformat(),
        "--end",
        today.isoformat(),
        "--no-resume",
    ],
    check=True,
)
