from pathlib import Path
import json
from datetime import datetime, timezone
DATA=Path(__file__).with_name("data"); DATA.mkdir(exist_ok=True)
def save_json(name,payload):
    w={"saved_at":datetime.now(timezone.utc).isoformat(),"payload":payload}
    (DATA/f"{name}.json").write_text(json.dumps(w,indent=2),encoding="utf-8"); return w
def load_json(name):
    p=DATA/f"{name}.json"
    if not p.exists(): return None
    try: return json.loads(p.read_text(encoding="utf-8"))
    except: return None
