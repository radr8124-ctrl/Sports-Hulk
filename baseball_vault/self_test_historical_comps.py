from pathlib import Path
import ast
H=Path(__file__).resolve().parent
for f in ["historical_pregame_features.py","historical_comps.py","build_full_matchup_board.py"]:
    q=H/f
    assert q.exists()
    ast.parse(q.read_text())
print("SPORTS HULK MLB HISTORICAL COMPS SELF-TEST: PASS")
