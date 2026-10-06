#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import json
import shutil


ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "nba_live" / "decision"
HIST = DEC / "history"
SNAPS = HIST / "snapshots"

LEDGER = (
    HIST
    / "NBA_RECOMMENDATION_LEDGER.csv"
)

LATEST = (
    HIST
    / "LATEST_NBA_SNAPSHOT.json"
)


FILES = {
    "GAME":
        DEC
        / "NBA_GAME_FINALISTS.csv",

    "PROP":
        DEC
        / "NBA_PROP_FINALISTS.csv",

    "PRIZEPICKS":
        DEC
        / "NBA_PRIZEPICKS_FINALISTS.csv",

    "PARLAY":
        DEC
        / "NBA_PARLAYS_TODAY.csv",
}


LEDGER_FIELDS = [
    "snapshot_at",
    "bundle_hash",
    "lane",
    "recommendation_key",
    "source_file",
    "game_key",
    "event_id",
    "start",
    "player",
    "team",
    "market",
    "selection",
    "side",
    "line",
    "decision",
    "score",
    "payload_json",
]


def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def read_rows(path):

    if (
        not path.exists()
        or path.stat().st_size <= 1
    ):
        return []

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:

        return list(
            csv.DictReader(f)
        )


def stable_subset(
    lane,
    row,
):

    if lane == "GAME":

        fields = [
            "game_key",
            "start_dt",
            "market_canonical",
            "selection_canonical",
            "line_group",
            "approved_book_count",
            "median_price_american",
            "historical_context_value",
            "context_direction",
            "evidence_score",
            "decision",
            "context_basis",
        ]


    elif lane in {
        "PROP",
        "PRIZEPICKS",
    }:

        fields = [
            "event_id",
            "game_key",
            "start_dt",
            "player_key",
            "player",
            "current_team",
            "market_subtype",
            "stat_type",
            "side",
            "line",
            "book_count",
            "sportsbook_book_count",
            "stat_l5_avg",
            "stat_l10_avg",
            "l5_hit_rate",
            "l10_hit_rate",
            "minutes_l5_avg",
            "context_direction",
            "injury_gate",
            "sample_gate",
            "evidence_score",
            "decision",
        ]


    else:

        fields = [
            "leg1_lane",
            "leg1_game",
            "leg1_player",
            "leg1_market",
            "leg1_selection",
            "leg1_line",
            "leg1_score",
            "leg2_lane",
            "leg2_game",
            "leg2_player",
            "leg2_market",
            "leg2_selection",
            "leg2_line",
            "leg2_score",
            "evidence_score",
            "status",
        ]


    return {
        field:
            clean(
                row.get(field)
            )

        for field in fields
    }


def recommendation_key(
    lane,
    row,
):

    if lane == "GAME":

        identity = [
            lane,
            row.get("game_key"),
            row.get("market_canonical"),
            row.get("selection_canonical"),
            row.get("line_group"),
        ]


    elif lane in {
        "PROP",
        "PRIZEPICKS",
    }:

        identity = [
            lane,
            row.get("event_id"),
            row.get("player_key"),
            row.get("market_subtype"),
            row.get("side"),
            row.get("line"),
        ]


    else:

        identity = [
            lane,
            row.get("leg1_lane"),
            row.get("leg1_game"),
            row.get("leg1_player"),
            row.get("leg1_market"),
            row.get("leg1_selection"),
            row.get("leg1_line"),
            row.get("leg2_lane"),
            row.get("leg2_game"),
            row.get("leg2_player"),
            row.get("leg2_market"),
            row.get("leg2_selection"),
            row.get("leg2_line"),
        ]


    raw = json.dumps(
        [
            clean(x)
            for x in identity
        ],
        separators=(",", ":"),
    )


    return hashlib.sha256(
        raw.encode()
    ).hexdigest()


def main():

    HIST.mkdir(
        parents=True,
        exist_ok=True,
    )

    SNAPS.mkdir(
        parents=True,
        exist_ok=True,
    )


    all_rows = {}

    semantic_bundle = {}


    for lane, path in FILES.items():

        rows = read_rows(path)

        all_rows[lane] = rows

        semantic_bundle[lane] = sorted(
            [
                stable_subset(
                    lane,
                    row,
                )
                for row in rows
            ],
            key=lambda x:
                json.dumps(
                    x,
                    sort_keys=True,
                ),
        )


    semantic_raw = json.dumps(
        semantic_bundle,
        sort_keys=True,
        separators=(",", ":"),
    )


    bundle_hash = hashlib.sha256(
        semantic_raw.encode()
    ).hexdigest()


    if LATEST.exists():

        try:

            latest = json.loads(
                LATEST.read_text()
            )

            if (
                latest.get(
                    "bundle_hash"
                )
                == bundle_hash
            ):

                print(
                    "UNCHANGED NBA RECOMMENDATION BUNDLE"
                )

                print(
                    "BUNDLE HASH:",
                    bundle_hash[
                        :12
                    ],
                )

                return

        except Exception:
            pass


    now = datetime.now(
        timezone.utc
    )

    stamp = now.strftime(
        "%Y%m%dT%H%M%SZ"
    )


    snap = (
        SNAPS
        / (
            stamp
            + "_"
            + bundle_hash[
                :12
            ]
        )
    )


    snap.mkdir(
        parents=True,
        exist_ok=False,
    )


    for path in FILES.values():

        if path.exists():

            shutil.copy2(
                path,
                snap
                / path.name,
            )


    manifest = {
        "snapshot_at":
            now.isoformat(),

        "bundle_hash":
            bundle_hash,

        "files":
            {
                lane:
                    len(
                        rows
                    )

                for lane, rows
                in all_rows.items()
            },
    }


    (
        snap
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    exists = LEDGER.exists()

    with LEDGER.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=LEDGER_FIELDS,
        )


        if not exists:

            writer.writeheader()


        for lane, rows in all_rows.items():

            for row in rows:

                if lane == "GAME":

                    game_key = row.get(
                        "game_key",
                        "",
                    )

                    event_id = ""

                    start = row.get(
                        "start_dt",
                        "",
                    )

                    player = ""

                    team = row.get(
                        "selection_canonical",
                        "",
                    )

                    market = row.get(
                        "market_canonical",
                        "",
                    )

                    selection = row.get(
                        "selection_canonical",
                        "",
                    )

                    side = selection

                    line = row.get(
                        "line_group",
                        "",
                    )

                    decision = row.get(
                        "decision",
                        "",
                    )

                    score = row.get(
                        "evidence_score",
                        "",
                    )


                elif lane in {
                    "PROP",
                    "PRIZEPICKS",
                }:

                    game_key = row.get(
                        "game_key",
                        "",
                    )

                    event_id = row.get(
                        "event_id",
                        "",
                    )

                    start = row.get(
                        "start_dt",
                        row.get(
                            "start",
                            "",
                        ),
                    )

                    player = row.get(
                        "player",
                        "",
                    )

                    team = row.get(
                        "current_team",
                        "",
                    )

                    market = row.get(
                        "market_subtype",
                        "",
                    )

                    selection = row.get(
                        "side",
                        "",
                    )

                    side = row.get(
                        "side",
                        "",
                    )

                    line = row.get(
                        "line",
                        "",
                    )

                    decision = row.get(
                        "decision",
                        "",
                    )

                    score = row.get(
                        "evidence_score",
                        "",
                    )


                else:

                    game_key = (
                        clean(
                            row.get(
                                "leg1_game"
                            )
                        )
                        + " + "
                        + clean(
                            row.get(
                                "leg2_game"
                            )
                        )
                    )

                    event_id = ""

                    start = ""

                    player = ""

                    team = ""

                    market = "PARLAY"

                    selection = ""

                    side = ""

                    line = ""

                    decision = row.get(
                        "status",
                        "",
                    )

                    score = row.get(
                        "evidence_score",
                        "",
                    )


                writer.writerow({
                    "snapshot_at":
                        now.isoformat(),

                    "bundle_hash":
                        bundle_hash,

                    "lane":
                        lane,

                    "recommendation_key":
                        recommendation_key(
                            lane,
                            row,
                        ),

                    "source_file":
                        FILES[
                            lane
                        ].name,

                    "game_key":
                        game_key,

                    "event_id":
                        event_id,

                    "start":
                        start,

                    "player":
                        player,

                    "team":
                        team,

                    "market":
                        market,

                    "selection":
                        selection,

                    "side":
                        side,

                    "line":
                        line,

                    "decision":
                        decision,

                    "score":
                        score,

                    "payload_json":
                        json.dumps(
                            row,
                            separators=(
                                ",",
                                ":",
                            ),
                        ),
                })


    LATEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "NBA SNAPSHOT:",
        snap,
    )

    print(
        "BUNDLE HASH:",
        bundle_hash[
            :12
        ],
    )

    print(
        "LEDGER ROWS ADDED:",
        sum(
            len(x)
            for x in all_rows.values()
        ),
    )


if __name__ == "__main__":
    main()
