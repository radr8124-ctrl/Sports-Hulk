#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT=Path("/home/ubuntu/sports-hulk")
DFS=ROOT/"intelligence_warehouse"/"dfs"
SRC=DFS/"DFS_CONTEST_ARCHETYPES_CURRENT.csv"
OUT=DFS/"DFS_DK_LEVERAGE_CURRENT.csv"
RECEIPT=DFS/"DFS_DK_LEVERAGE_RECEIPT.json"
NOW=datetime.now(timezone.utc)

def num_series(s):
    return pd.to_numeric(s,errors="coerce")

def main():
    d=pd.read_csv(SRC,low_memory=False)
    d=d[
        d["sport"].astype(str).str.upper().eq("NFL")
        & d["platform"].astype(str).str.upper().eq("DRAFTKINGS")
    ].copy()
    d["projected_fantasy_points"]=num_series(d["projected_fantasy_points"])
    d["modelled_ownership_pct"]=num_series(d.get("modelled_ownership_pct"))
    d["audit_value_per_1000"]=num_series(d.get("audit_value_per_1000"))
    d["projection_percentile"]=num_series(d.get("projection_percentile"))
    d["value_percentile"]=num_series(d.get("value_percentile"))
    d=d[
        d["projected_fantasy_points"].notna()
        & d["modelled_ownership_pct"].notna()
    ].copy()

    if d.empty:
        pd.DataFrame().to_csv(OUT,index=False)
        RECEIPT.write_text(json.dumps({
            "generated_at":NOW.isoformat(),
            "rows":0,
            "modelled_ownership_used":True,
            "verified_ownership_available":False,
            "automatic_model_adjustment":False,
        },indent=2,sort_keys=True))
        return

    d["ownership_percentile"]=(
        d.groupby("position")["modelled_ownership_pct"]
        .rank(pct=True,method="average")*100
    ).round(1)

    # Descriptive leverage: projection/value strength relative to modelled ownership.
    d["leverage_research_score"]=(
        d["projection_percentile"].fillna(50)
        - d["ownership_percentile"].fillna(50)
        + 0.25*(d["value_percentile"].fillna(50)-50)
    ).round(2)

    def label(r):
        proj=r.get("projection_percentile")
        own=r.get("ownership_percentile")
        lev=r.get("leverage_research_score")
        if pd.isna(proj) or pd.isna(own) or pd.isna(lev):
            return "INSUFFICIENT"
        if proj>=80 and own>=80:
            return "CHALK_CORE"
        if lev>=35 and proj>=65:
            return "STRONG_LEVERAGE"
        if lev>=20 and proj>=55:
            return "LEVERAGE"
        if own<=25 and proj<45:
            return "LOW_OWN_LOW_PROJECTION"
        return "BALANCED"

    d["leverage_tier"]=d.apply(label,axis=1)
    d["ownership_is_modelled"]=True
    d["ownership_is_verified"]=False
    d["ownership_source"]="SHARKSNIP_HEURISTIC"
    d["leverage_score_is_probability"]=False
    d["automatic_model_adjustment"]=False
    d["generated_at"]=NOW.isoformat()

    keep=[
        "generated_at","sport","platform","slate_id","player","player_key",
        "position","team","opponent","salary","projected_fantasy_points",
        "audit_value_per_1000","projection_percentile","value_percentile",
        "modelled_ownership_pct","ownership_percentile","leverage_research_score",
        "leverage_tier","contest_archetype","context_signal","availability_status",
        "ownership_is_modelled","ownership_is_verified","ownership_source",
        "leverage_score_is_probability","automatic_model_adjustment",
    ]
    keep=[c for c in keep if c in d.columns]
    out=d[keep].sort_values(
        ["leverage_research_score","projected_fantasy_points"],
        ascending=[False,False],
    )
    out.to_csv(OUT,index=False)

    receipt={
        "generated_at":NOW.isoformat(),
        "rows":int(len(out)),
        "tier_counts":out["leverage_tier"].value_counts().to_dict(),
        "modelled_ownership_rows":int(out["modelled_ownership_pct"].notna().sum()),
        "modelled_ownership_used":True,
        "verified_ownership_available":False,
        "ownership_source":"SHARKSNIP_HEURISTIC",
        "score_is_probability":False,
        "automatic_model_adjustment":False,
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True))
    print(json.dumps(receipt,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
