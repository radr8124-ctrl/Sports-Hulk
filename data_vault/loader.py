from pathlib import Path
import argparse, hashlib, json, urllib.request
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
RAW=HERE/"raw"
META=HERE/"meta"
MANIFEST=json.loads((HERE/"source_manifest.json").read_text())

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def targets(name,seasons):
    cfg=MANIFEST["datasets"][name]
    if cfg["kind"]=="single":
        return [(None,cfg["url"])]
    if not seasons:
        raise SystemExit(f"{name} requires --seasons YEAR [YEAR ...]")
    out=[]
    for s in seasons:
        if s < cfg.get("min_season",0):
            raise SystemExit(f"{name}: {s} is before supported minimum {cfg['min_season']}")
        out.append((s,cfg["url_template"].format(season=s)))
    return out

def dest_for(name,season):
    return RAW/name/(f"{name}.parquet" if season is None else f"{name}_{season}.parquet")

def fetch(url,dest,force=False):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists() and dest.stat().st_size>0 and not force:
        return {"status":"cached","bytes":dest.stat().st_size,"sha256":sha256_file(dest)}
    tmp=dest.with_suffix(dest.suffix+".part")
    if tmp.exists(): tmp.unlink()
    req=urllib.request.Request(url,headers={"User-Agent":"Sports-HULK-Data-Vault/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=90) as r, open(tmp,"wb") as f:
            while True:
                b=r.read(1024*1024)
                if not b: break
                f.write(b)
        tmp.replace(dest)
    except Exception:
        if tmp.exists(): tmp.unlink()
        raise
    return {"status":"downloaded","bytes":dest.stat().st_size,"sha256":sha256_file(dest)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--list",action="store_true")
    p.add_argument("--dataset",action="append")
    p.add_argument("--seasons",nargs="+",type=int)
    p.add_argument("--force",action="store_true")
    a=p.parse_args()
    if a.list:
        for k,v in MANIFEST["datasets"].items():
            print(f"{k:18} {v['description']}")
        return
    if not a.dataset:
        p.error("Use --list or --dataset")
    for name in a.dataset:
        if name not in MANIFEST["datasets"]:
            raise SystemExit(f"Unknown dataset: {name}")
        recs=[]
        print(f"\n=== {name} ===")
        for season,url in targets(name,a.seasons):
            dest=dest_for(name,season)
            rec=fetch(url,dest,a.force)
            rec.update({"season":season,"url":url,"path":str(dest)})
            print(f"{season or 'all'}: {rec['status']} ({rec['bytes']:,} bytes)")
            recs.append(rec)
        META.mkdir(parents=True,exist_ok=True)
        (META/f"{name}_last_run.json").write_text(json.dumps({
            "dataset":name,
            "run_at_utc":datetime.now(timezone.utc).isoformat(),
            "records":recs
        },indent=2))
    print("\nSPORTS HULK NFL DATA VAULT: DONE")

if __name__=="__main__":
    main()
