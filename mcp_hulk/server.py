from pathlib import Path
import pandas as pd
from mcp.server import MCPServer

ROOT = Path("/home/ubuntu/sports-hulk")
mcp = MCPServer("Sports Hulk")

DATASETS = {
    "prizepicks_all": ROOT / "prizepicks_live/derived/PRIZEPICKS_ALL.csv",
    "prizepicks_standard": ROOT / "prizepicks_live/derived/PRIZEPICKS_STANDARD.csv",
    "parlay_nfl": ROOT / "parlay_live/derived/NFL_PARLAY_MARKET_RAW.csv",
    "nfl_current": ROOT / "nfl_live/derived/NFL_CURRENT_WEEK.csv",
    "nfl_survivor": ROOT / "nfl_live/derived/NFL_SURVIVOR_BOARD.csv",
    "nfl_props": ROOT / "props_live/nfl/derived/NFL_PLAYER_PROPS.csv",
    "mlb_props": ROOT / "props_live/mlb/derived/MLB_PLAYER_PROPS.csv",
    "mlb_board": ROOT / "baseball_vault/derived/MLB_MATCHUP_BOARD_INTELLIGENCE.csv",
    "cfb_board": ROOT / "college_vault/derived/CFB_CURRENT_BOARD.csv",
    "fantasy": ROOT / "fantasy_live/derived/FANTASY_HULK_V2_ADP_BOARD.csv",
}

@mcp.tool()
def status() -> dict:
    return {
        name: {
            "exists": path.exists(),
            "path": str(path),
            "size": path.stat().st_size if path.exists() else None,
        }
        for name, path in DATASETS.items()
    }

@mcp.tool()
def inspect_dataset(name: str, rows: int = 5) -> dict:
    if name not in DATASETS:
        raise ValueError(f"Unknown dataset: {name}")

    path = DATASETS[name]

    if not path.exists():
        raise FileNotFoundError(str(path))

    df = pd.read_csv(path)

    rows = max(1, min(rows, 20))

    return {
        "dataset": name,
        "rows": len(df),
        "columns": list(df.columns),
        "sample": df.head(rows).fillna("").to_dict("records"),
    }

@mcp.tool()
def market_keys() -> dict:
    df = pd.read_csv(DATASETS["parlay_nfl"])

    return (
        df["market_key"]
        .fillna("NULL")
        .value_counts()
        .head(100)
        .to_dict()
    )


@mcp.tool()
def prizepicks_board(
    sport: str = "NFL",
    odds_type: str = "standard",
    limit: int = 50,
) -> dict:
    """Read cached PrizePicks projections."""

    df = pd.read_csv(DATASETS["prizepicks_all"])

    sport = sport.upper().strip()
    odds_type = odds_type.lower().strip()
    limit = max(1, min(int(limit), 200))

    x = df[
        df["league"].fillna("").astype(str).str.upper().eq(sport)
    ].copy()

    if odds_type != "all":
        x = x[
            x["odds_type"]
            .fillna("")
            .astype(str)
            .str.lower()
            .eq(odds_type)
        ]

    if odds_type == "standard" and "is_promo" in x.columns:
        x = x[~x["is_promo"].fillna(False)]

    cols = [
        c for c in [
            "player",
            "team",
            "description",
            "stat",
            "line",
            "odds_type",
            "trending_count",
            "start_time",
        ]
        if c in x.columns
    ]

    return {
        "sport": sport,
        "odds_type": odds_type,
        "matches": len(x),
        "data": x[cols].head(limit).fillna("").to_dict("records"),
    }


@mcp.tool()
def nfl_receiving_consensus(player: str) -> dict:
    """Build cached sportsbook consensus for NFL receiving yards."""

    df = pd.read_csv(DATASETS["parlay_nfl"])

    x = df[
        df["player"]
        .fillna("")
        .astype(str)
        .str.casefold()
        .eq(player.strip().casefold())
        &
        df["market_key"]
        .fillna("")
        .eq("player_receiving_yards")
    ].copy()

    if x.empty:
        return {
            "player": player,
            "status": "NO MARKET DATA"
        }

    x["line"] = pd.to_numeric(x["line"], errors="coerce")
    x = x.dropna(subset=["line"])

    if x.empty:
        return {
            "player": player,
            "status": "NO VALID LINES"
        }

    return {
        "player": player,
        "books": int(x["bookmaker"].nunique()),
        "median_line": float(x["line"].median()),
        "low_line": float(x["line"].min()),
        "high_line": float(x["line"].max()),
        "mean_line": float(x["line"].mean()),
        "lines": (
            x[
                [
                    "bookmaker",
                    "line",
                    "over_price",
                    "under_price",
                    "age_seconds",
                ]
            ]
            .sort_values(["line", "bookmaker"])
            .fillna("")
            .to_dict("records")
        ),
    }


@mcp.tool()
def compare_prizepicks_receiving_yards(player: str) -> dict:
    """Compare cached PrizePicks NFL receiving-yards line to sportsbook consensus."""

    pp = pd.read_csv(DATASETS["prizepicks_standard"])

    x = pp[
        pp["league"].fillna("").astype(str).str.upper().eq("NFL")
        &
        pp["player"].fillna("").astype(str).str.casefold().eq(
            player.strip().casefold()
        )
        &
        pp["stat"].fillna("").astype(str).eq("Rec Yards")
    ].copy()

    if x.empty:
        return {
            "player": player,
            "status": "NO PRIZEPICKS LINE"
        }

    pp_line = pd.to_numeric(
        x.iloc[0]["line"],
        errors="coerce"
    )

    market = pd.read_csv(DATASETS["parlay_nfl"])

    y = market[
        market["player"].fillna("").astype(str).str.casefold().eq(
            player.strip().casefold()
        )
        &
        market["market_key"].fillna("").eq(
            "player_receiving_yards"
        )
    ].copy()

    y["line"] = pd.to_numeric(y["line"], errors="coerce")
    y = y.dropna(subset=["line"])

    if y.empty:
        return {
            "player": player,
            "prizepicks_line": float(pp_line),
            "status": "NO SPORTSBOOK CONSENSUS"
        }

    median = float(y["line"].median())
    diff = float(pp_line - median)

    if diff <= -2:
        signal = "PP BELOW MARKET"
    elif diff >= 2:
        signal = "PP ABOVE MARKET"
    else:
        signal = "MARKET ALIGNED"

    return {
        "player": player,
        "stat": "Receiving Yards",
        "prizepicks_line": float(pp_line),
        "market_median": median,
        "market_low": float(y["line"].min()),
        "market_high": float(y["line"].max()),
        "books": int(y["bookmaker"].nunique()),
        "difference": diff,
        "signal": signal,
    }


@mcp.tool()
def budget_status() -> dict:
    """Read local API budget files only. No external API calls."""

    files = {
        "api_budget_state":
            ROOT / "api_control/api_budget_state.json",

        "api_budget_config":
            ROOT / "api_control/api_budget_config.json",

        "feed_budget_config":
            ROOT / "api_control/feed_budget_config.json",
    }

    out = {}

    for name, path in files.items():
        if not path.exists():
            out[name] = {
                "exists": False,
                "path": str(path),
            }
            continue

        try:
            out[name] = {
                "exists": True,
                "path": str(path),
                "data": json.loads(path.read_text()),
            }
        except Exception as e:
            out[name] = {
                "exists": True,
                "path": str(path),
                "error": str(e),
            }

    return out

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8765,
    )
