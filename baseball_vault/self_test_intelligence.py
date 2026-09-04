from pathlib import Path
import importlib.util, pandas as pd
H=Path(__file__).resolve().parent
for name in ["statcast_backfill.py","mlb_game_master.py","weather.py"]:
    assert (H/name).exists()
spec=importlib.util.spec_from_file_location("s",H/"statcast_backfill.py"); s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
chunks=list(s.daterange_chunks("2026-08-01","2026-08-08",3))
assert chunks==[("2026-08-01","2026-08-03"),("2026-08-04","2026-08-06"),("2026-08-07","2026-08-08")]
assert not (H/".env").exists() and not (H/"app.py").exists()
print("SPORTS HULK BASEBALL INTELLIGENCE SELF-TEST: PASS")
