from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
m=json.loads((HERE/"source_manifest.json").read_text())
required={"players","pbp","rosters","weekly_rosters","injuries","depth_charts","snap_counts","ngs_passing","ngs_receiving","ngs_rushing"}
assert required <= set(m["datasets"])
assert m["datasets"]["pbp"]["min_season"]==1999
assert m["datasets"]["injuries"]["min_season"]==2009
assert m["datasets"]["depth_charts"]["min_season"]==2001
assert m["datasets"]["snap_counts"]["min_season"]==2012
assert not (HERE/"app.py").exists()
assert not (HERE/".env").exists()
print("SPORTS HULK NFL DATA VAULT SELF-TEST: PASS")
