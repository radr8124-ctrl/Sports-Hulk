from pathlib import Path
import pandas as pd
import numpy as np
import re

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def choose_edge_column(d):
    preferred=[
        "home_edge","edge_score","matchup_edge","HULK_edge",
        "home_matchup_edge","matchup_score","hulk_score",
        "home_score_edge","home_projection_edge","model_edge"
    ]
    for c in preferred:
        if c in d.columns and pd.to_numeric(d[c],errors="coerce").notna().sum() >= max(5,len(d)//4):
            return c
    candidates=[]
    for c in d.columns:
        lc=c.lower()
        if any(k in lc for k in ["edge","score","lean","projection"]) and c not in [
            "away_score","home_score","comp_avg_home_margin","comp_avg_total_runs"
        ]:
            n=pd.to_numeric(d[c],errors="coerce")
            if n.notna().sum() >= max(5,len(d)//4) and n.nunique(dropna=True)>2:
                candidates.append((c,int(n.notna().sum()),float(n.std(skipna=True) or 0)))
    candidates.sort(key=lambda x:(x[1],x[2]),reverse=True)
    return candidates[0][0] if candidates else None

def comp_reliability(row):
    # Empirical 750-game walk-forward showed B was strongest.
    grade=str(row.get("comp_quality_grade",""))
    hist_acc=pd.to_numeric(pd.Series([row.get("comp_bucket_hist_accuracy")]),errors="coerce").iloc[0]
    samples=pd.to_numeric(pd.Series([row.get("comp_bucket_hist_samples")]),errors="coerce").iloc[0]
    if pd.isna(hist_acc) or pd.isna(samples) or samples < 50:
        return 0.0
    # Only reward signal above chance; cap to prevent comps dominating.
    lift=max(0.0,float(hist_acc)-0.50)
    return min(1.0,lift/0.10)

def run():
    f=DERIVED/"MLB_MATCHUP_BOARD_INTELLIGENCE.csv"
    if not f.exists(): raise SystemExit("Missing MLB_MATCHUP_BOARD_INTELLIGENCE.csv")
    d=pd.read_csv(f,low_memory=False)

    edge_col=choose_edge_column(d)
    d["decision_brain_edge_column"]=edge_col if edge_col else "NONE"

    # Model side is derived only if a credible numeric edge-like field exists.
    if edge_col:
        edge=pd.to_numeric(d[edge_col],errors="coerce")
        d["hulk_model_side"]=np.where(edge>0,"HOME",np.where(edge<0,"AWAY","NEUTRAL"))
        mag=edge.abs()
        denom=mag.quantile(.90)
        if pd.isna(denom) or denom==0: denom=1.0
        d["model_strength_0_1"]=(mag/denom).clip(0,1)
    else:
        d["hulk_model_side"]="UNKNOWN"
        d["model_strength_0_1"]=np.nan

    d["comp_reliability_0_1"]=d.apply(comp_reliability,axis=1)
    p=pd.to_numeric(d.get("comp_home_win_rate"),errors="coerce")
    d["comp_direction_strength_0_1"]=((p-0.5).abs()*2).clip(0,1)
    d["comp_effective_strength_0_1"]=d["comp_reliability_0_1"]*d["comp_direction_strength_0_1"]

    d["comp_side"]=np.select([p>=0.60,p<=0.40],["HOME","AWAY"],default="NEUTRAL")

    if edge_col:
        d["comp_alignment"]=np.where(
            d["comp_side"]=="NEUTRAL","NEUTRAL",
            np.where(d["comp_side"]==d["hulk_model_side"],"SUPPORT","CONFLICT")
        )
        d["research_consensus_score"]=(
            d["model_strength_0_1"].fillna(0)*0.85
            + np.where(d["comp_alignment"]=="SUPPORT",1,
                np.where(d["comp_alignment"]=="CONFLICT",-1,0))
              * d["comp_effective_strength_0_1"]*0.15
        )
    else:
        d["comp_alignment"]="UNSCORED"
        d["research_consensus_score"]=np.nan

    # Research recommendation intentionally cannot upgrade PASS to BET.
    base=d.get("decision",pd.Series(["PASS"]*len(d))).astype(str)
    d["research_guardrail"]=np.select(
        [
            (base=="WATCH") & (d["comp_alignment"]=="SUPPORT") & (d["comp_reliability_0_1"]>=0.5),
            (base=="WATCH") & (d["comp_alignment"]=="CONFLICT") & (d["comp_reliability_0_1"]>=0.5),
            (base=="PASS") & (d["comp_alignment"]=="SUPPORT") & (d["comp_reliability_0_1"]>=0.5),
        ],
        ["WATCH_PLUS","WATCH_DOWN","PASS_WITH_SUPPORT"],
        default=base
    )

    d.to_csv(DERIVED/"MLB_DECISION_BRAIN_RESEARCH.csv",index=False)
    d.to_parquet(DERIVED/"MLB_DECISION_BRAIN_RESEARCH.parquet",index=False)

    print("Detected edge column:", edge_col or "NONE")
    print("Research guardrail counts:",d["research_guardrail"].value_counts(dropna=False).to_dict())
    print("Alignment counts:",d["comp_alignment"].value_counts(dropna=False).to_dict())
    print("SPORTS HULK MLB DECISION BRAIN RESEARCH: DONE")
if __name__=="__main__":
    run()
