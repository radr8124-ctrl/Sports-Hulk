from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
for f in ["schema_profiler.py","decision_brain_research.py","market_source_discovery.py","decision_brain_report.py","run_decision_brain_build.py"]:
    p=HERE/f
    assert p.exists()
    ast.parse(p.read_text())
print("SPORTS HULK MLB DECISION BRAIN BUILD SELF-TEST: PASS")
