from pathlib import Path
import importlib.util, pandas as pd
H=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location("gm",H/"game_master.py"); gm=importlib.util.module_from_spec(s); s.loader.exec_module(gm)
pbp=pd.DataFrame({"game_id":["g1"]*4,"posteam":["A","A","B","B"],"defteam":["B","B","A","A"],
"play_type":["pass","run","pass","run"],"epa":[.2,.1,-.1,.3],"success":[1,1,0,1],
"yards_gained":[21,4,5,11],"sack":[0,0,0,0],"interception":[0,0,1,0],"fumble_lost":[0,0,0,0]})
o=gm.derive_team_games(pbp)
assert len(o)==2 and "def_epa_per_play" in o and "turnover_rate" in o
print("SPORTS HULK NFL GAME MASTER SELF-TEST: PASS")
