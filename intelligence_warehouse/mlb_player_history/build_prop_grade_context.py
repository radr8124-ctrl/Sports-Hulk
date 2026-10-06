#!/usr/bin/env python3
from pathlib import Path
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
FEATURES = ROOT / "intelligence_warehouse/mlb_player_history/MLB_PLAYER_PREGAME_FEATURES.csv"
GRADES = ROOT / "mlb_live/decision/history/MLB_GRADED_RECOMMENDATIONS.csv"
OUT = ROOT / "intelligence_warehouse/mlb_player_history/MLB_PROP_GRADE_CONTEXT.csv"

def main():
    h = pd.read_csv(FEATURES, low_memory=False)
    g = pd.read_csv(GRADES, low_memory=False)
    p = g[g["lane"].astype(str).str.upper().eq("PROP")].copy()
    if h.empty or p.empty:
        pd.DataFrame().to_csv(OUT, index=False)
        print("MLB_PROP_GRADE_CONTEXT rows: 0")
        return

    h["gamePk"] = pd.to_numeric(h["gamePk"], errors="coerce")
    h["player_id"] = pd.to_numeric(h["player_id"], errors="coerce")
    p["result_gamePk"] = pd.to_numeric(p["result_gamePk"], errors="coerce")
    p["player_id"] = pd.to_numeric(p["player_id"], errors="coerce")

    lookup = h[[
        "gamePk","player_id","group","pregame_games"
    ] + [c for c in h.columns if c.startswith("pregame_") and c != "pregame_games"]].copy()

    merged = p.merge(
        lookup,
        left_on=["result_gamePk","player_id"],
        right_on=["gamePk","player_id"],
        how="left",
        suffixes=("","_history"),
    )

    metric_map = {
        "hits_pg": "hits",
        "runs_pg": "runs",
        "rbi_pg": "rbi",
        "hrr_pg": "hrr",
        "singles_pg": "singles",
        "doubles_pg": "doubles",
        "home_runs_pg": "home_runs",
        "total_bases_pg": "total_bases",
        "stolen_bases_pg": "stolen_bases",
        "walks_pg": "walks",
        "strikeouts_pg": "pitcher_strikeouts",
        "outs_pg": "outs",
        "hits_allowed_pg": "hits_allowed",
        "earned_runs_pg": "earned_runs",
        "walks_allowed_pg": "walks_allowed",
    }

    def metric_value(row, suffix):
        metric = metric_map.get(str(row.get("metric") or ""))
        if not metric:
            return None
        col = f"pregame_{metric}_{suffix}"
        return row.get(col)

    for suffix in ("5","10","20","season"):
        merged[f"metric_pregame_{suffix}"] = merged.apply(
            lambda r: metric_value(r, suffix), axis=1
        )

    merged["history_match"] = merged["gamePk"].notna()
    games = pd.to_numeric(merged.get("pregame_games"), errors="coerce").fillna(0)
    merged["history_coverage"] = pd.cut(
        games,
        bins=[-1,0,4,9,19,float("inf")],
        labels=["NONE","THIN","BUILDING","MODERATE","STRONG"],
    ).astype(str)

    keep = [
        "snapshot_at","recommendation_key","result_gamePk","player_id","player",
        "metric","market","selection","line","decision","grade","actual_value",
        "pregame_games","metric_pregame_5","metric_pregame_10",
        "metric_pregame_20","metric_pregame_season",
        "history_match","history_coverage","context_status",
    ]
    keep = [c for c in keep if c in merged.columns]
    out = merged[keep].copy()
    out.to_csv(OUT, index=False)

    matched = int(out.get("history_match", pd.Series(dtype=bool)).fillna(False).sum())
    print(f"MLB_PROP_GRADE_CONTEXT rows: {len(out)}")
    print(f"HISTORY MATCHES: {matched}")
    print("RESULT: MLB_PROP_GRADE_CONTEXT_READY")

if __name__ == "__main__":
    main()
