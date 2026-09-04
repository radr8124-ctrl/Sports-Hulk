from pathlib import Path
import ast
HERE=Path(__file__).resolve().parent
for f in [
    "team_normalization.py",
    "market_reconcile_historical.py",
    "market_history_reconciled.py",
    "historical_core_with_market.py",
    "historical_market_qa.py",
    "run_historical_market_recon_build.py",
]:
    p=HERE/f
    assert p.exists(),f
    ast.parse(p.read_text())
print("SPORTS HULK MLB HISTORICAL MARKET RECON SELF-TEST: PASS")
