from pathlib import Path
from datetime import date
import argparse, subprocess, sys

HERE=Path(__file__).resolve().parent

def season_window(year):
    return f"{year}-03-15", f"{year}-11-15"

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--years",nargs="+",type=int,required=True)
    a.add_argument("--chunk-days",type=int,default=3)
    a.add_argument("--retries",type=int,default=5)
    z=a.parse_args()
    for y in z.years:
        start,end=season_window(y)
        print(f"\n=== MLB STATCAST SEASON {y}: {start} through {end} ===")
        cmd=[sys.executable,str(HERE/"statcast_backfill.py"),
             "--start",start,"--end",end,
             "--chunk-days",str(z.chunk_days),"--retries",str(z.retries)]
        rc=subprocess.call(cmd)
        if rc!=0:
            print(f"Season {y} returned code {rc}; cached chunks remain and rerun will resume.")
            raise SystemExit(rc)
    print("\nSPORTS HULK MLB SEASON BACKFILL: DONE")
if __name__=="__main__": main()
