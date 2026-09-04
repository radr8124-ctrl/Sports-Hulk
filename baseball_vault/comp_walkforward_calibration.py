from pathlib import Path
import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"
DERIVED.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "home_pregame_rs_10",
    "home_pregame_ra_10",
    "home_pregame_winpct_10",
    "home_pregame_rdiff_10",
    "away_pregame_rs_10",
    "away_pregame_ra_10",
    "away_pregame_winpct_10",
    "away_pregame_rdiff_10",
    "park_run_factor",
    "home_days_since_last",
    "away_days_since_last",
]

def distance(pool, row, cols):
    acc = np.zeros(len(pool), dtype=float)
    used = 0
    for c in cols:
        if c not in pool.columns or c not in row.index or pd.isna(row[c]):
            continue
        s = pd.to_numeric(pool[c], errors="coerce")
        sd = s.std(ddof=0)
        if pd.isna(sd) or sd == 0:
            continue
        z = (s - float(row[c])) / sd
        z = z.fillna(2.5).clip(-4, 4)
        acc += z.to_numpy() ** 2
        used += 1
    return np.sqrt(acc / max(used, 1)), used

def bucket(x):
    if pd.isna(x):
        return "UNKNOWN"
    if x < 0.35:
        return "A_CLOSE"
    if x < 0.50:
        return "B_GOOD"
    if x < 0.70:
        return "C_FAIR"
    return "D_LOOSE"

def run(max_games=750, n_comps=25):
    f = DERIVED / "MLB_HISTORICAL_PREGAME_FEATURES.csv"
    if not f.exists():
        raise SystemExit("Missing MLB_HISTORICAL_PREGAME_FEATURES.csv")

    h = pd.read_csv(f, low_memory=False)
    h["officialDate"] = pd.to_datetime(h["officialDate"], errors="coerce", utc=True)
    h = h[
        h["officialDate"].notna()
        & h["home_win"].notna()
        & h["total_runs"].notna()
        & h["home_margin"].notna()
    ].copy().sort_values(["officialDate", "gamePk"])

    usable = h[h[FEATURES].notna().sum(axis=1) >= 9].copy()
    targets = usable.tail(max_games).copy()

    out = []
    for _, r in targets.iterrows():
        pool = usable[usable["officialDate"] < r["officialDate"]].copy()
        if len(pool) < 100:
            continue

        d, used = distance(pool, r, FEATURES)
        comps = pool.assign(comp_distance=d).sort_values("comp_distance").head(n_comps)
        if len(comps) < n_comps:
            continue

        p_home = pd.to_numeric(comps["home_win"], errors="coerce").mean()
        pred_total = pd.to_numeric(comps["total_runs"], errors="coerce").mean()
        pred_margin = pd.to_numeric(comps["home_margin"], errors="coerce").mean()
        med_dist = pd.to_numeric(comps["comp_distance"], errors="coerce").median()

        actual_home = float(r["home_win"])
        actual_total = float(r["total_runs"])
        actual_margin = float(r["home_margin"])

        out.append({
            "gamePk": r["gamePk"],
            "officialDate": r["officialDate"],
            "away_team": r["away_team"],
            "home_team": r["home_team"],
            "features_used": used,
            "comp_count": len(comps),
            "comp_median_distance": med_dist,
            "distance_bucket": bucket(med_dist),
            "pred_home_win_rate": p_home,
            "pred_home_side": 1 if p_home >= 0.5 else 0,
            "actual_home_win": actual_home,
            "winner_correct": int((p_home >= 0.5) == bool(actual_home)),
            "pred_total_runs": pred_total,
            "actual_total_runs": actual_total,
            "total_abs_error": abs(pred_total - actual_total),
            "pred_home_margin": pred_margin,
            "actual_home_margin": actual_margin,
            "margin_abs_error": abs(pred_margin - actual_margin),
        })

    d = pd.DataFrame(out)
    d.to_csv(DERIVED / "MLB_COMP_WALKFORWARD_RESULTS.csv", index=False)

    if d.empty:
        raise SystemExit("No walk-forward rows produced")

    rows = []
    for name, g in [("ALL", d)] + list(d.groupby("distance_bucket")):
        rows.append({
            "bucket": name,
            "samples": len(g),
            "winner_accuracy": g["winner_correct"].mean(),
            "total_mae": g["total_abs_error"].mean(),
            "margin_mae": g["margin_abs_error"].mean(),
            "avg_distance": g["comp_median_distance"].mean(),
            "avg_features_used": g["features_used"].mean(),
        })
    s = pd.DataFrame(rows)
    s.to_csv(DERIVED / "MLB_COMP_CALIBRATION_SUMMARY.csv", index=False)

    print(f"Walk-forward games graded: {len(d):,}")
    print(f"Overall winner accuracy: {d['winner_correct'].mean():.3f}")
    print(f"Overall total MAE: {d['total_abs_error'].mean():.3f}")
    print(f"Overall margin MAE: {d['margin_abs_error'].mean():.3f}")
    print("")
    print(s.to_string(index=False))
    print("")
    print("SPORTS HULK MLB COMP WALK-FORWARD CALIBRATION: DONE")

if __name__ == "__main__":
    run()
