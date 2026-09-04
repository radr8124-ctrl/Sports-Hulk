from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def run():
    recon=pd.read_csv(DERIVED/"MLB_MARKET_RECONCILED_ROWS.csv",low_memory=False)
    hist=pd.read_csv(DERIVED/"MLB_HISTORICAL_CORE_WITH_MARKET.csv",low_memory=False)

    # Source/date coverage audit tells us whether we truly possess historical
    # market archives or only current-slate snapshots.
    recon["market_time"]=pd.to_datetime(recon["market_time"],errors="coerce",utc=True)
    dated=recon[recon["market_time"].notna()].copy()
    if len(dated):
        print("\n=== MARKET SOURCE DATE COVERAGE ===")
        for src,g in dated.groupby("source_file"):
            print(f"{src}: {g['market_time'].min()} -> {g['market_time'].max()} | rows={len(g)}")

    issues=[]

    dup=recon[recon.match_status=="MATCHED"].duplicated(
        subset=["source_file","source_event_id","book","market","side","market_time","gamePk"],
        keep=False
    )
    dup_count=int(dup.sum())

    ambiguous=int((recon.match_status=="AMBIGUOUS").sum())
    unmatched=int((recon.match_status=="UNMATCHED").sum())
    matched=int((recon.match_status=="MATCHED").sum())

    report=[
        ("market_rows_total",len(recon)),
        ("matched",matched),
        ("ambiguous",ambiguous),
        ("unmatched",unmatched),
        ("duplicate_matched_rows",dup_count),
        ("historical_games_total",len(hist)),
        ("historical_games_with_market",int(hist.historical_market_known.sum())),
    ]

    pd.DataFrame(report,columns=["metric","value"]).to_csv(DERIVED/"MLB_HISTORICAL_MARKET_QA.csv",index=False)

    print("=== MLB HISTORICAL MARKET QA ===")
    for k,v in report:
        print(f"{k}: {v}")

    sample_cols=[c for c in [
        "source_file","away_raw","home_raw","market_time","match_status","gamePk",
        "mlb_away_team","mlb_home_team"
    ] if c in recon.columns]
    print("\n=== MATCH SAMPLE ===")
    print(recon[sample_cols].head(20).to_string(index=False))

    if matched==0:
        raise SystemExit("QA FAIL: zero matched market rows")
    if ambiguous>matched:
        print("WARNING: ambiguous rows exceed matched rows")
    print("SPORTS HULK MLB HISTORICAL MARKET QA: DONE")

if __name__=="__main__":
    run()
