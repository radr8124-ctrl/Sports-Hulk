from pathlib import Path

import collect_nightly as c


def main():
    c.ensure_dirs()
    c.load_env()

    run_stamp = c.stamp()

    print("=== SPORTS HULK MLB MARKET SNAPSHOT ===")

    # --------------------------------------------------
    # SPORTS GAME ODDS
    # --------------------------------------------------

    sgo, err = c.sgo_mlb()
    sgo_ok = sgo is not None

    if sgo_ok:
        c.save_json(
            sgo,
            c.RAW / f"sgo_mlb_{run_stamp}.json",
        )

        rows = c.flatten_sgo(sgo)

        snapshot_time = c.now_local().isoformat()

        for r in rows:
            r["snapshot_at"] = snapshot_time

        c.write_csv(
            rows,
            c.LATEST / "MLB_SGO_MARKETS.csv",
        )

        c.append_history_csv(
            rows,
            c.HISTORY / "MLB_SGO_MARKET_HISTORY.csv",
        )

        print(
            f"SGO snapshot rows: {len(rows):,}"
        )
    else:
        print(
            f"SGO skipped/error: {err}"
        )

    # --------------------------------------------------
    # THE ODDS API
    # --------------------------------------------------

    oa, err = c.odds_api_mlb()
    odds_ok = oa is not None

    if odds_ok:
        c.save_json(
            oa,
            c.RAW / f"odds_api_mlb_{run_stamp}.json",
        )

        rows = c.flatten_odds_api(oa)

        snapshot_time = c.now_local().isoformat()

        for r in rows:
            r["snapshot_at"] = snapshot_time

        c.write_csv(
            rows,
            c.LATEST / "MLB_ODDS_API_MARKETS.csv",
        )

        c.append_history_csv(
            rows,
            c.HISTORY / "MLB_ODDS_API_MARKET_HISTORY.csv",
        )

        print(
            f"Odds API snapshot rows: {len(rows):,}"
        )
    else:
        print(
            f"Odds API skipped/error: {err}"
        )

    # --------------------------------------------------
    # RUN STATUS
    # --------------------------------------------------

    if not sgo_ok and not odds_ok:
        print(
            "SPORTS HULK MLB MARKET SNAPSHOT: FAILED — "
            "both market feeds unavailable"
        )
        raise SystemExit(1)

    if not sgo_ok or not odds_ok:
        failed = (
            "SGO"
            if not sgo_ok
            else "Odds API"
        )

        print(
            f"WARNING: partial market snapshot — "
            f"{failed} unavailable"
        )

    print(
        "SPORTS HULK MLB MARKET SNAPSHOT: DONE"
    )


if __name__ == "__main__":
    main()
