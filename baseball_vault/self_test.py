from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("c", HERE / "collect_nightly.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

assert c.parse_innings_to_outs("1.2") == 5
assert c.parse_innings_to_outs("2.0") == 6

sample = [{
    "role":"reliever","team":"A","pitcher_id":1,"pitcher":"Test",
    "pitches":25,"outs":3,"battersFaced":4,"game_date":"2026-08-31"
},{
    "role":"reliever","team":"A","pitcher_id":1,"pitcher":"Test",
    "pitches":20,"outs":3,"battersFaced":4,"game_date":"2026-09-01"
}]
o = c.aggregate_bullpen(sample, None)
assert len(o) == 1
assert o[0]["pitches_last3"] == 45
assert o[0]["days_used_last3"] == 2
assert o[0]["HULK_bullpen_workload_score"] > 45

assert not (HERE / ".env").exists()
assert not (HERE / "app.py").exists()
print("SPORTS HULK BASEBALL LIVE VAULT SELF-TEST: PASS")
