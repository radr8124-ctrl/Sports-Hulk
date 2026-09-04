from pathlib import Path
import importlib.util, pandas as pd, numpy as np, tempfile

H=Path(__file__).resolve().parent
for name in ["statcast_backfill.py","statcast_season_runner.py","matchup_engine.py"]:
    assert (H/name).exists(), name

spec=importlib.util.spec_from_file_location("s",H/"statcast_backfill.py")
s=importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
assert list(s.daterange_chunks("2026-08-01","2026-08-08",3)) == [
 ("2026-08-01","2026-08-03"),("2026-08-04","2026-08-06"),("2026-08-07","2026-08-08")]

spec=importlib.util.spec_from_file_location("m",H/"matchup_engine.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

ars=pd.DataFrame({
 "pitcher":[10,10],"pitch_type":["FF","SL"],"usage_pct":[.6,.4],
 "whiff_per_swing":[.25,.35],"hard_hit_per_bip":[.35,.30],
 "xwoba_allowed":[.310,.280],"pitches":[300,200]
})
bat=pd.DataFrame({
 "batter":[1,1,2,2],"pitch_type":["FF","SL","FF","SL"],
 "avg_xwoba":[.300,.250,.310,.270],
 "whiff_per_swing":[.30,.35,.28,.32],
 "hard_hit_per_bip":[.35,.30,.34,.28],"barrel_per_bip":[.08,.06,.07,.05],
 "pitches":[50,30,45,25]
})
r=m.arsenal_vs_hitters(ars,bat,[1,2],10)
assert r["arsenal_sample_pitches"]==500
assert r["pitch_types_matched"]==2
assert np.isfinite(r["arsenal_matchup_score"])
print("SPORTS HULK BASEBALL MATCHUP ENGINE SELF-TEST: PASS")
