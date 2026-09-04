
from pathlib import Path
from datetime import datetime
import shutil, py_compile, re

ROOT = Path("/home/ubuntu/sports-hulk")
APP = ROOT / "app.py"
if not APP.exists():
    raise SystemExit("Missing app.py")

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = APP.with_name(f"app.py.pre_prop_ui_{stamp}")
shutil.copy2(APP, backup)

s = APP.read_text()

import_line = "from prop_intelligence.hulk_prop_ui import render_prop_intelligence\n"
if import_line not in s:
    lines = s.splitlines(True)
    pos = 0
    for i, line in enumerate(lines[:120]):
        if line.startswith(("import ", "from ")):
            pos = i + 1
    lines.insert(pos, import_line)
    s = "".join(lines)

def inject_after_branch(src, label, sport):
    # Match exact elif page=="..." line and inject first statement inside branch.
    pat = re.compile(rf'^(?P<ind>\s*)elif\s+page\s*==\s*["\']{re.escape(label)}["\']\s*:\s*$', re.M)
    m = pat.search(src)
    if not m:
        return src, False, "branch not found"

    branch_start = src.find("\n", m.end()) + 1
    if branch_start <= 0:
        return src, False, "branch newline not found"

    indent = m.group("ind") + "    "
    call = f'{indent}render_prop_intelligence("{sport}")\n'

    # If already present in first 20 lines of branch, don't duplicate.
    branch_preview = src[branch_start:branch_start+1400]
    if f'render_prop_intelligence("{sport}")' in branch_preview:
        return src, True, "already wired"

    src = src[:branch_start] + call + src[branch_start:]
    return src, True, "wired"

results = []
s, ok, msg = inject_after_branch(s, "MLB Player Props", "MLB")
results.append(("MLB", ok, msg))
s, ok, msg = inject_after_branch(s, "NFL Player Props", "NFL")
results.append(("NFL", ok, msg))

if not all(ok for _, ok, _ in results):
    shutil.copy2(backup, APP)
    for sport, ok, msg in results:
        print(f"{sport}: {msg}")
    raise SystemExit("One or more Player Props branches were not found; original app.py restored")

APP.write_text(s)
try:
    py_compile.compile(str(APP), doraise=True)
except Exception:
    shutil.copy2(backup, APP)
    raise

print("="*72)
print("SPORTS HULK APP.PY PROP UI WIRING")
print("="*72)
print("BACKUP:", backup)
for sport, ok, msg in results:
    print(f"{sport} PLAYER PROPS:", msg.upper())
print("APP COMPILE: PASS")
print("RESULT: PASS")
