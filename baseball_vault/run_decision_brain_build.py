from pathlib import Path
import subprocess,sys
HERE=Path(__file__).resolve().parent
steps=[
 "schema_profiler.py",
 "comp_walkforward_calibration.py",
 "comp_intelligence_overlay.py",
 "decision_brain_research.py",
 "market_source_discovery.py",
 "decision_brain_report.py",
]
for s in steps:
    print("\n"+"="*72)
    print("RUNNING:",s)
    print("="*72)
    subprocess.run([sys.executable,str(HERE/s)],check=True)
print("\nSPORTS HULK MLB DECISION BRAIN BUILD: COMPLETE")
