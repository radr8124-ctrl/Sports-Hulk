from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
for f in ["market_history_builder.py","high_conviction_research.py","high_conviction_backtest.py","market_context_report.py","run_market_context_build.py"]:
    p=HERE/f
    assert p.exists()
    ast.parse(p.read_text())
print("SPORTS HULK MLB MARKET CONTEXT BUILD SELF-TEST: PASS")
