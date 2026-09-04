from pathlib import Path
import importlib.util, pandas as pd
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("m",H/"matchup_engine.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
df=pd.DataFrame({"team":["A","A","B"],"HULK_bullpen_workload_score":[10,20,30]})
x=m.bullpen_map(df)
assert x["A"]==15.0 and x["B"]==30.0
assert m.confidence(900,8,True,False)=="MEDIUM"
assert m.confidence(900,8,True,True)=="HIGH"
print("SPORTS HULK BULLPEN + CONFIDENCE HOTFIX SELF-TEST: PASS")
