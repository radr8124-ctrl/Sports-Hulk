from pathlib import Path
import subprocess, sys

HERE=Path(__file__).resolve().parent
steps=[
    "market_reconcile_historical.py",
    "market_history_reconciled.py",
    "historical_core_with_market.py",
    "historical_market_qa.py",
]
for s in steps:
    print("\n"+"="*72)
    print("RUNNING:",s)
    print("="*72)
    subprocess.run([sys.executable,str(HERE/s)],check=True)
print("\nSPORTS HULK MLB HISTORICAL MARKET RECON BUILD: COMPLETE")
