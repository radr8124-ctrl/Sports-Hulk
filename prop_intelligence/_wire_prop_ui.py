
from pathlib import Path
from datetime import datetime
import ast, re, shutil, py_compile

ROOT=Path("/home/ubuntu/sports-hulk")
candidates=[ROOT/"hulk_final_ui.py", ROOT/"app.py"]
target=next((p for p in candidates if p.exists()), None)
if not target:
    raise SystemExit("Could not find hulk_final_ui.py or app.py")

stamp=datetime.now().strftime("%Y%m%d_%H%M%S")
backup=target.with_name(target.name+f".pre_prop_ui_{stamp}")
shutil.copy2(target, backup)
s=target.read_text()

import_line='from prop_intelligence.hulk_prop_ui import render_prop_intelligence\n'
if import_line not in s:
    # add after import block conservatively
    lines=s.splitlines(True)
    pos=0
    for i,line in enumerate(lines[:120]):
        if line.startswith(("import ","from ")):
            pos=i+1
    lines.insert(pos, import_line)
    s="".join(lines)

def inject_function(src, sport):
    tree=ast.parse(src)
    best=None
    for node in ast.walk(tree):
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            nm=node.name.lower()
            if sport.lower() in nm and "prop" in nm:
                best=node; break
    if not best or not getattr(best,"body",None):
        return src, False
    line=best.body[0].lineno-1
    lines=src.splitlines(True)
    indent=re.match(r'^\s*', lines[line]).group(0)
    call=f'{indent}render_prop_intelligence("{sport.upper()}")\n'
    # Avoid duplicate injection.
    window="".join(lines[line:line+8])
    if "render_prop_intelligence" in window:
        return src, True
    lines.insert(line, call)
    return "".join(lines), True

done=[]
for sport in ("MLB","NFL"):
    s,ok=inject_function(s,sport)
    done.append((sport,ok))

# Fallback: inject immediately after explicit page branch if function discovery failed.
for sport,ok in list(done):
    if ok: continue
    labels=[f'{sport} Player Props', f'{sport} PLAYER PROPS']
    for label in labels:
        pat=re.compile(r'^(?P<ind>\s*)(?:if|elif)\s+.*[="\']'+re.escape(label)+r'.*:\s*$',re.M)
        m=pat.search(s)
        if m:
            line_end=s.find("\n",m.end())+1
            ind=m.group("ind")+"    "
            s=s[:line_end]+f'{ind}render_prop_intelligence("{sport}")\n'+s[line_end:]
            done=[(a,True if a==sport else b) for a,b in done]
            break

target.write_text(s)
try:
    py_compile.compile(str(target), doraise=True)
except Exception:
    shutil.copy2(backup,target)
    raise

print("="*72)
print("SPORTS HULK PROP UI WIRING")
print("="*72)
print("TARGET:", target)
print("BACKUP:", backup)
for sport,ok in done:
    print(f"{sport} PLAYER PROPS WIRED:", "YES" if ok else "NO MATCH")
print("COMPILE: PASS")
print("RESULT: PASS")
