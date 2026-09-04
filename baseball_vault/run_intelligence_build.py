from pathlib import Path
import subprocess, sys

HERE = Path(__file__).resolve().parent

steps = [
    "historical_pregame_features.py",
    "historical_comps.py",
    "build_full_matchup_board.py",
    "comp_walkforward_calibration.py",
    "comp_intelligence_overlay.py",
    "comp_intelligence_report.py",
]

for step in steps:
    print("")
    print("=" * 72)
    print("RUNNING:", step)
    print("=" * 72)
    subprocess.run([sys.executable, str(HERE / step)], check=True)

print("")
print("SPORTS HULK MLB INTELLIGENCE BUILD: COMPLETE")
