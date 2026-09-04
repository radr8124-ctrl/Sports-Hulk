from pathlib import Path
import ast
H=Path(__file__).resolve().parent
for f in ["baseball_daily.py","result_refresh.py","result_grader.py"]:
    p=H/f
    assert p.exists()
    ast.parse(p.read_text())
print("SPORTS HULK BASEBALL AUTO RUNNER SELF-TEST: PASS")
