from pathlib import Path
import importlib.util, pandas as pd, numpy as np
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("b",H/"build_blended_profiles.py")
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
x=pd.DataFrame({
 "_source_year":[2025,2026],"pitcher":[1,1],"batter":[10,10],"pitch_type":["FF","FF"],
 "player_name":["Test","Test"],"release_speed":[90,100],"release_spin_rate":[2000,2200],
 "pfx_x":[0,0],"pfx_z":[1,1],"launch_speed":[90,100],"launch_angle":[10,28],
 "estimated_woba_using_speedangle":[.4,.2],"description":["hit_into_play","swinging_strike"]
})
y=b.prep(x,{2025:.5,2026:1.0})
pp=b.pitcher_profiles(y); bp=b.batter_profiles(y)
assert len(pp)==1 and len(bp)==1
assert abs(pp.iloc[0].avg_velocity-((90*.5+100)/1.5))<.001
print("SPORTS HULK BLENDED PROFILES SELF-TEST: PASS")
