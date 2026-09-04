from pathlib import Path
import ast

HERE = Path(__file__).resolve().parent
files = [
    "comp_walkforward_calibration.py",
    "comp_intelligence_overlay.py",
    "comp_intelligence_report.py",
    "run_intelligence_build.py",
]
for f in files:
    p = HERE / f
    assert p.exists(), f"Missing {f}"
    ast.parse(p.read_text())

print("SPORTS HULK MLB INTELLIGENCE BUILD SELF-TEST: PASS")
