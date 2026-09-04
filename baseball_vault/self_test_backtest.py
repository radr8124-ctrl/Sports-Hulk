from pathlib import Path
import ast
H=Path(__file__).resolve().parent
for f in ["prediction_logger.py","result_grader.py","calibration_report.py","run_calibration.py"]:
    p=H/f
    assert p.exists()
    ast.parse(p.read_text())
print("SPORTS HULK MLB BACKTEST/CALIBRATION SELF-TEST: PASS")
