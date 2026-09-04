from pathlib import Path

import pandas as pd
import numpy as np

HERE = Path(__file__).resolve().parent
DERIVED = HERE / "derived"
LATEST = HERE / "latest"
RAW = HERE / "raw"
HISTORY = HERE / "history"

DERIVED.mkdir(parents=True, exist_ok=True)


def load_candidates():
    files = []

    # Primary source: permanent historical market snapshots.
    history_files = [
        HISTORY / "MLB_ODDS_API_MARKET_HISTORY.csv",
        HISTORY / "MLB_SGO_MARKET_HISTORY.csv",
    ]

    for p in history_files:
        if p.exists() and p.stat().st_size > 0:
            files.append(p)

    # Fallback only if no permanent history exists yet.
    if not files:
        for p in [
            LATEST / "MLB_ODDS_API_MARKETS.csv",
            LATEST / "MLB_SGO_MARKETS.csv",
        ]:
            if p.exists():
                files.append(p)

    return files

def first_existing(d, aliases):
    cols = {str(c).lower(): c for c in d.columns}

    for alias in aliases:
        if alias.lower() in cols:
            return d[cols[alias.lower()]]

    return pd.Series(np.nan, index=d.index)


def normalize(p):
    try:
        d = pd.read_csv(p, low_memory=False)
    except Exception as e:
        print(f"Skipping {p}: {e}")
        return pd.DataFrame()

    out = pd.DataFrame(index=d.index)

    out["gamePk"] = first_existing(
        d,
        ["gamePk", "event_id", "eventID", "eventid", "id"],
    )

    # Scheduled game start time.
    # Kept separate from the timestamp when we observed the odds.
    out["game_start"] = first_existing(
        d,
        ["commence_time", "start", "game_start", "start_time"],
    )

    out["book"] = first_existing(
        d,
        ["book", "bookmaker", "sportsbook", "provider"],
    )

    out["market"] = first_existing(
        d,
        ["market", "market_type", "bet_type", "betTypeID", "type"],
    )

    out["side"] = first_existing(
        d,
        ["side", "outcome", "selection", "sideID", "name", "label"],
    )

    out["price"] = first_existing(
        d,
        ["price", "odds", "american_odds", "decimal_odds"],
    )

    # Normal line/point field.
    out["point"] = first_existing(
        d,
        ["point", "line", "spread", "total"],
    )

    # SGO totals often stores the total separately in overUnder.
    over_under = first_existing(d, ["overUnder", "over_under"])

    point_numeric = pd.to_numeric(out["point"], errors="coerce")
    ou_numeric = pd.to_numeric(over_under, errors="coerce")

    out["point"] = point_numeric.where(point_numeric.notna(), ou_numeric)

    # Our collection time is the actual observation timestamp
    # used for historical sequencing and pregame/live classification.
    out["timestamp"] = first_existing(
        d,
        [
            "snapshot_at",
            "timestamp",
            "created_at",
        ],
    )

    # Keep the sportsbook/provider update time separately.
    out["source_update_timestamp"] = first_existing(
        d,
        [
            "market_last_update",
            "book_last_update",
            "lastUpdatedAt",
            "last_updated_at",
            "updated_at",
            "last_update",
        ],
    )

    out["away_team"] = first_existing(
        d,
        ["away_team", "away", "awayteam"],
    )

    out["home_team"] = first_existing(
        d,
        ["home_team", "home", "hometeam"],
    )

    # Extra fields retained where available
    out["player"] = first_existing(
        d,
        ["player", "player_name"],
    )

    out["playerID"] = first_existing(
        d,
        ["playerID", "player_id"],
    )

    out["statID"] = first_existing(
        d,
        ["statID", "stat_id"],
    )

    # Exact SGO market identity.
    # These prevent full-game, inning, alternate, and derivative
    # markets from being merged together.
    out["oddID"] = first_existing(
        d,
        ["oddID", "odd_id"],
    )

    out["periodID"] = first_existing(
        d,
        ["periodID", "period_id"],
    )

    out["available"] = first_existing(
        d,
        ["available", "is_available"],
    )

    out["source_file"] = p.name

    return out



def american_to_implied_probability(x):
    try:
        x = float(x)
    except Exception:
        return np.nan

    if not np.isfinite(x) or x == 0:
        return np.nan

    if x > 0:
        return 100.0 / (x + 100.0)

    return (-x) / ((-x) + 100.0)


def run():
    files = load_candidates()

    print(f"Market files found: {len(files)}")
    for p in files:
        print(f" - {p}")

    frames = [normalize(p) for p in files]
    frames = [x for x in frames if not x.empty]

    if not frames:
        raise SystemExit("No market files found")

    d = pd.concat(frames, ignore_index=True, sort=False)

    # The two providers use slightly different ISO timestamp formats.
    # Pandas may infer one format from the first provider and reject the
    # other. format="mixed" safely parses both.
    d["timestamp"] = pd.to_datetime(
        d["timestamp"],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    d["source_update_timestamp"] = pd.to_datetime(
        d["source_update_timestamp"],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    d["game_start"] = pd.to_datetime(
        d["game_start"],
        errors="coerce",
        utc=True,
        format="mixed",
    )

    # Classify each market observation.
    #
    # Anything observed before scheduled first pitch is pregame.
    # Anything at/after first pitch is live/in-game.
    d["market_phase"] = np.where(
        d["timestamp"].notna()
        & d["game_start"].notna()
        & (d["timestamp"] < d["game_start"]),
        "pregame",
        np.where(
            d["timestamp"].notna()
            & d["game_start"].notna()
            & (d["timestamp"] >= d["game_start"]),
            "live",
            "unknown",
        ),
    )

    d["price_num"] = pd.to_numeric(
        d["price"],
        errors="coerce",
    )

    d["point_num"] = pd.to_numeric(
        d["point"],
        errors="coerce",
    )

    # Clean important string fields
    for c in [
        "gamePk",
        "book",
        "market",
        "side",
        "away_team",
        "home_team",
        "player",
        "playerID",
        "statID",
        "oddID",
        "periodID",
    ]:
        if c in d.columns:
            d[c] = d[c].astype("string")

    d["_ord"] = np.arange(len(d))

    #
    # CRITICAL:
    # Book must be part of the identity.
    # Otherwise FanDuel/DraftKings/etc get mixed together.
    #
    keys = [
        "gamePk",
        "away_team",
        "home_team",
        "book",
        "market",
        "side",
        "player",
        "playerID",
        "statID",
        "oddID",
        "periodID",
        "market_phase",
    ]

    keys = [c for c in keys if c in d.columns]

    # Remove rows that have no usable game identity
    d = d[
        d["gamePk"].notna()
        | (d["away_team"].notna() & d["home_team"].notna())
    ].copy()

    #
    # Earliest observation = opening record we have.
    # Latest observation = current record we have.
    #
    d = d.sort_values(
        ["timestamp", "_ord"],
        na_position="first",
    )

    first = (
        d.groupby(keys, dropna=False)
        .first(numeric_only=False)
        .reset_index()
    )

    last = (
        d.groupby(keys, dropna=False)
        .last(numeric_only=False)
        .reset_index()
    )

    first = first.rename(
        columns={
            "price_num": "open_price",
            "point_num": "open_point",
            "timestamp": "open_timestamp",
        }
    )

    last = last.rename(
        columns={
            "price_num": "current_price",
            "point_num": "current_point",
            "timestamp": "current_timestamp",
        }
    )

    keep = keys + [
        "open_price",
        "open_point",
        "open_timestamp",
    ]

    out = last.merge(
        first[keep],
        on=keys,
        how="left",
    )

    out["price_move"] = (
        out["current_price"] - out["open_price"]
    )

    out["point_move"] = (
        out["current_point"] - out["open_point"]
    )

    # American odds are not linear, so use implied probability
    # for meaningful sportsbook price movement.
    out["open_implied_prob"] = out["open_price"].apply(
        american_to_implied_probability
    )

    out["current_implied_prob"] = out["current_price"].apply(
        american_to_implied_probability
    )

    # Percentage-point change in implied probability.
    out["implied_prob_move"] = (
        out["current_implied_prob"]
        - out["open_implied_prob"]
    ) * 100.0

    out["abs_implied_prob_move"] = (
        out["implied_prob_move"].abs()
    )

    # Number of observations backing each market record
    counts = (
        d.groupby(keys, dropna=False)
        .size()
        .reset_index(name="observation_count")
    )

    out = out.merge(
        counts,
        on=keys,
        how="left",
    )

    csv_path = DERIVED / "MLB_MARKET_HISTORY_SUMMARY.csv"
    parquet_path = DERIVED / "MLB_MARKET_HISTORY_SUMMARY.parquet"

    out.to_csv(csv_path, index=False)
    out.to_parquet(parquet_path, index=False)

    # Pregame-only history.
    #
    # This is the safe file for the pregame prediction engine.
    pregame = out[out["market_phase"] == "pregame"].copy()

    pregame_csv = DERIVED / "MLB_PREGAME_MARKET_HISTORY.csv"
    pregame_parquet = DERIVED / "MLB_PREGAME_MARKET_HISTORY.parquet"

    pregame.to_csv(pregame_csv, index=False)
    pregame.to_parquet(pregame_parquet, index=False)

    print()
    print(f"Raw normalized market rows: {len(d):,}")
    print(f"Market history rows: {len(out):,}")

    print()
    print("Market phases:")
    print(out["market_phase"].value_counts(dropna=False).to_string())

    print()
    print(f"Pregame history rows: {len(pregame):,}")
    print(
        "Pregame rows with 2+ observations:",
        f"{int((pregame.observation_count >= 2).sum()):,}",
    )

    print(
        "Pregame rows with point movement:",
        f"{int((pregame.point_move.fillna(0) != 0).sum()):,}",
    )

    print(
        "Pregame rows with price movement:",
        f"{int((pregame.price_move.fillna(0) != 0).sum()):,}",
    )

    print()
    print(
        "Rows with open/current points:",
        f"{int((out.open_point.notna() & out.current_point.notna()).sum()):,}",
    )

    print(
        "Rows with open/current prices:",
        f"{int((out.open_price.notna() & out.current_price.notna()).sum()):,}",
    )

    print(
        "Rows with 2+ observations:",
        f"{int((out.observation_count >= 2).sum()):,}",
    )

    print(
        "Rows with actual point movement:",
        f"{int((out.point_move.fillna(0) != 0).sum()):,}",
    )

    print(
        "Rows with actual price movement:",
        f"{int((out.price_move.fillna(0) != 0).sum()):,}",
    )

    print()
    print("SPORTS HULK MLB MARKET HISTORY SUMMARY: DONE")


if __name__ == "__main__":
    run()
