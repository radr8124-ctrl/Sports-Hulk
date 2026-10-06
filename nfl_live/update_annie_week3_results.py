from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
ENTRIES = ROOT / "nfl_live/derived/SURVIVOR_ENTRIES.json"

SCHEDULE = ROOT / "nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv"

TEAM_MAP = {
    "ARI":"Arizona Cardinals","ATL":"Atlanta Falcons","BAL":"Baltimore Ravens",
    "BUF":"Buffalo Bills","CAR":"Carolina Panthers","CHI":"Chicago Bears",
    "CIN":"Cincinnati Bengals","CLE":"Cleveland Browns","DAL":"Dallas Cowboys",
    "DEN":"Denver Broncos","DET":"Detroit Lions","GB":"Green Bay Packers",
    "HOU":"Houston Texans","IND":"Indianapolis Colts","JAX":"Jacksonville Jaguars",
    "KC":"Kansas City Chiefs","LV":"Las Vegas Raiders","LAC":"Los Angeles Chargers",
    "LA":"Los Angeles Rams","MIA":"Miami Dolphins","MIN":"Minnesota Vikings",
    "NE":"New England Patriots","NO":"New Orleans Saints","NYG":"New York Giants",
    "NYJ":"New York Jets","PHI":"Philadelphia Eagles","PIT":"Pittsburgh Steelers",
    "SF":"San Francisco 49ers","SEA":"Seattle Seahawks","TB":"Tampa Bay Buccaneers",
    "TEN":"Tennessee Titans","WAS":"Washington Commanders",
}

TRACKED = [
    "ANNIE G 01",
    "ANNIE G 03",
]


def load_entries():
    return json.loads(ENTRIES.read_text())


def save_entries(data):
    ENTRIES.write_text(
        json.dumps(data, indent=2)
    )


def fetch_games():
    df = pd.read_csv(SCHEDULE, low_memory=False)
    df = df[(df["season"] == 2026) & (df["week"] == 3) & (df["game_type"] == "REG")].copy()

    games = {}
    for _, row in df.iterrows():
        away = TEAM_MAP.get(str(row.get("away_team")), str(row.get("away_team")))
        home = TEAM_MAP.get(str(row.get("home_team")), str(row.get("home_team")))
        away_score = pd.to_numeric(row.get("away_score"), errors="coerce")
        home_score = pd.to_numeric(row.get("home_score"), errors="coerce")
        completed = pd.notna(away_score) and pd.notna(home_score)

        if completed:
            if home_score > away_score:
                home_winner, away_winner = True, False
            elif away_score > home_score:
                home_winner, away_winner = False, True
            else:
                # Survivor pool treats a tie as a loss.
                home_winner = away_winner = False
            detail = f"FINAL: {away} {int(away_score)} - {home} {int(home_score)}"
        else:
            home_winner = away_winner = None
            detail = "Game not final"

        teams = {
            away: {"score": away_score, "winner": away_winner},
            home: {"score": home_score, "winner": home_winner},
        }
        games[away] = {"teams": teams, "completed": completed, "detail": detail}
        games[home] = {"teams": teams, "completed": completed, "detail": detail}

    return games


def result_for_team(team, games):
    g = games.get(team)

    if not g:
        return "PENDING", "Game not found"

    if not g["completed"]:
        return "PENDING", g.get("detail")

    t = g["teams"].get(team)

    if not t:
        return "PENDING", g.get("detail")

    if t.get("winner") is True:
        return "WIN", g.get("detail")

    if t.get("winner") is False:
        return "LOSS", g.get("detail")

    return "LOSS", g.get("detail")


def main():
    data = load_entries()
    entries = data["entries"]

    games = fetch_games()

    now = datetime.now(
        timezone.utc
    ).isoformat()

    print()
    print("ANNIE G WEEK 3 LIVE STATUS")
    print("=" * 70)

    for name in TRACKED:

        if name not in entries:
            print(
                name,
                "MISSING — skipped"
            )
            continue

        e = entries[name]

        week3 = e.get("week_3")

        if not week3:
            print(
                name,
                "NO WEEK 3 DATA — skipped"
            )
            continue

        picks = week3.get(
            "picks", []
        )

        # Lock submitted Week 3 teams into
        # permanent used-team history.
        used = e.setdefault(
            "used_teams", []
        )

        for leg in picks:
            team = leg.get("team")

            if team and team not in used:
                used.append(team)

        leg_results = []

        for leg in picks:
            team = leg.get("team")

            result, detail = (
                result_for_team(
                    team,
                    games,
                )
            )

            leg["result"] = result
            leg["game_status"] = detail

            leg_results.append(result)

        if "LOSS" in leg_results:
            entry_result = "LOSS"
            e["status"] = "ELIMINATED"
            e["current_pick_status"] = "ELIMINATED"

        elif (
            len(leg_results) == 2
            and all(
                x == "WIN"
                for x in leg_results
            )
        ):
            entry_result = "WIN"
            e["status"] = "ALIVE"

            # Week 3 result refreshes can run repeatedly. Once Week 4 has
            # been opened, never wipe a manual Week 4 pick that the user
            # already saved in Sports HULK.
            prior_current_week = int(
                e.get("current_week")
                or 0
            )

            if prior_current_week < 4:
                e["current_week"] = 4
                e["current_picks"] = []
                e["current_pick"] = None
                e["backup_pick"] = None
                e["current_pick_status"] = "OPEN"
            else:
                e["current_week"] = 4
                e.setdefault(
                    "current_picks",
                    [],
                )
                e.setdefault(
                    "current_pick",
                    None,
                )
                e.setdefault(
                    "backup_pick",
                    None,
                )
                e.setdefault(
                    "current_pick_status",
                    "OPEN",
                )

            week4 = e.get("week_4")
            if not isinstance(
                week4,
                dict,
            ):
                week4 = {
                    "required_picks": None,
                    "rule_status": "AWAITING_OFFICIAL_WEEK4_SHEET",
                    "picks": [],
                    "entry_result": "OPEN",
                    "opened_at": now,
                }
            else:
                week4.setdefault(
                    "required_picks",
                    None,
                )
                week4.setdefault(
                    "rule_status",
                    "AWAITING_OFFICIAL_WEEK4_SHEET",
                )
                week4.setdefault(
                    "picks",
                    [],
                )
                week4.setdefault(
                    "entry_result",
                    "OPEN",
                )
                week4.setdefault(
                    "opened_at",
                    now,
                )

            e["week_4"] = week4

        else:
            entry_result = "PENDING"

        week3["entry_result"] = (
            entry_result
        )

        week3["last_checked_at"] = now

        e["week_3"] = week3

        print()
        print(name)
        print(
            " Used:",
            ", ".join(used)
        )

        for leg in picks:
            print(
                " ",
                leg["team"],
                "=>",
                leg["result"],
                "|",
                leg.get(
                    "game_status"
                ),
            )

        print(
            " ENTRY:",
            entry_result,
        )

    save_entries(data)

    print()
    print("=" * 70)
    print("RESULT TRACKER COMPLETE")


if __name__ == "__main__":
    main()
