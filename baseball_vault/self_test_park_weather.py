from pathlib import Path
import ast
H=Path(__file__).resolve().parent
for f in ["park_factors.py","weather_features.py","park_weather_enrich.py"]:
    q=H/f
    assert q.exists()
    ast.parse(q.read_text())
print("SPORTS HULK PARK + WEATHER SELF-TEST: PASS")
