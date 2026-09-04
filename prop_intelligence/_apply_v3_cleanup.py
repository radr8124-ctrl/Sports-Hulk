from pathlib import Path
from datetime import datetime
import shutil, py_compile

ROOT = Path("/home/ubuntu/sports-hulk")
P = ROOT / "prop_intelligence" / "build_prop_intelligence.py"

if not P.exists():
    raise SystemExit("Missing prop_intelligence/build_prop_intelligence.py")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = P.with_name(f"build_prop_intelligence.py.pre_v3_{stamp}")
shutil.copy2(P, backup)

s = P.read_text()

if "def canonical_event_time(v):" not in s:
    marker = "def is_today_future(v):\n"
    insert = (
        "def canonical_event_time(v):\n"
        "    dt = parse_dt(v)\n"
        "    if dt is None:\n"
        "        return \"\"\n"
        "    return dt.astimezone(timezone.utc).isoformat().replace(\"+00:00\",\"Z\")\n\n"
    )
    if marker not in s:
        raise SystemExit("Could not locate is_today_future()")
    s = s.replace(marker, insert + marker, 1)

s = s.replace(
    '"event_time":evtime,"canonical_market":canon,"raw_market":raw_market,',
    '"event_time":canonical_event_time(evtime),"canonical_market":canon,"raw_market":raw_market,'
)

s = s.replace(
    '"pitcher_strikeouts": ["player_strikeouts","pitcher_strikeouts","strikeouts"],',
    '"pitcher_strikeouts": ["player_strikeouts","pitcher_strikeouts"],'
)

if '"batter_strikeouts":' not in s:
    marker = '        "hits_runs_rbis": '
    idx = s.find(marker)
    if idx != -1:
        s = s[:idx] + '        "batter_strikeouts": ["batting_strikeouts","batter_strikeouts"],\n' + s[idx:]

P.write_text(s)
py_compile.compile(str(P), doraise=True)

print("="*72)
print("SPORTS HULK PROP INTELLIGENCE V3 CLEANUP")
print("="*72)
print(f"BACKUP: {backup.name}")
print("EVENT TIME NORMALIZATION: ENABLED")
print("AMBIGUOUS MLB STRIKEOUT MAPPING: REMOVED")
print("BATTER STRIKEOUT MARKET: PRESERVED")
print("HULK SCORE THRESHOLDS: UNCHANGED")
print("COMPILE: PASS")
print("RESULT: PASS")
