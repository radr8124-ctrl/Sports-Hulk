from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent
steps=[
    "market_history_builder.py",
    "high_conviction_backtest.py",
    "high_conviction_research.py",
    "market_context_report.py",
]
for s in steps:
    print("\n"+"="*72)
    print("RUNNING:",s)
    print("="*72)
    subprocess.run([sys.executable,str(HERE/s)],check=True)
print("\nSPORTS HULK MLB MARKET CONTEXT BUILD: COMPLETE")
