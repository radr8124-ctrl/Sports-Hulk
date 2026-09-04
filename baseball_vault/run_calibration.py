from pathlib import Path
import subprocess, sys

HERE=Path(__file__).resolve().parent

def run(name):
    rc=subprocess.call([sys.executable,str(HERE/name)])
    if rc!=0: raise SystemExit(rc)

if __name__=="__main__":
    run("result_grader.py")
    run("calibration_report.py")
    print("SPORTS HULK MLB BACKTEST/CALIBRATION RUN: DONE")
