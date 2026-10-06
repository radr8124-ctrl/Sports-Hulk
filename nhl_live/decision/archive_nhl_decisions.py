#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import csv
import hashlib
import json
import shutil


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

DEC = (
    ROOT
    / "nhl_live"
    / "decision"
)

HIST = (
    DEC
    / "history"
)

SNAPS = (
    HIST
    / "snapshots"
)

LEDGER = (
    HIST
    / "NHL_RECOMMENDATION_LEDGER.csv"
)

LATEST = (
    HIST
    / "LATEST_NHL_SNAPSHOT.json"
)


FILES = {
    "GAME":
        DEC
        / "NHL_GAME_FINALISTS.csv",

    "PROP":
        DEC
        / "NHL_PROP_FINALISTS.csv",

    "PRIZEPICKS":
        DEC
        / "NHL_PRIZEPICKS_FINALISTS.csv",

    "PARLAY":
        DEC
        / "NHL_PARLAYS_TODAY.csv",
}


FIELDS = [
    "snapshot_at",
    "bundle_hash",
    "lane",
    "recommendation_key",
    "source_file",
    "game_key",
    "start",
    "nhl_player_id",
    "player",
    "market",
    "stat_type",
    "selection",
    "side",
    "line",
    "decision",
    "score",
    "payload_json",
]


def clean(
    value,
):

    if value is None:
        return ""

    return str(
        value
    ).strip()


def read_rows(
    path,
):

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
            csv.DictReader(
                f
            )
        )


def stable_subset(
    lane,
    row,
):

    if lane == "GAME":

        names = [
            "game_key",
            "start_dt",
            "market_canonical",
            "selection_canonical",
            "line_group",
            "approved_book_count",
            "provider_evidence_count",
            "median_price_american",
            "historical_context_value",
            "context_direction",
            "away_injury_blocks",
            "home_injury_blocks",
            "evidence_score",
            "decision",
        ]


    elif lane == "PROP":

        names = [
            "game_key",
            "nhl_player_id",
            "player",
            "market_subtype",
            "stat_type",
            "side",
            "line",
            "book_count",
            "median_price_american",
            "l5_hit_rate",
            "l10_hit_rate",
            "context_direction",
            "injury_gate",
            "evidence_score",
            "decision",
        ]


    elif lane == "PRIZEPICKS":

        names = [
            "game_key",
            "nhl_player_id",
            "player",
            "market_subtype",
            "stat_type",
            "side",
            "line",
            "sportsbook_book_count",
            "sportsbook_median_price_american",
            "l5_hit_rate",
            "l10_hit_rate",
            "context_direction",
            "injury_gate",
            "evidence_score",
            "decision",
        ]


    else:

        names = [
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
        name:
            clean(
                row.get(
                    name
                )
            )

        for name in names
    }


def recommendation_key(
    lane,
    row,
):

    if lane == "GAME":

        identity = [
            lane,
            row.get(
                "game_key"
            ),
            row.get(
                "market_canonical"
            ),
            row.get(
                "selection_canonical"
            ),
            row.get(
                "line_group"
            ),
        ]


    elif lane in {
        "PROP",
        "PRIZEPICKS",
    }:

        identity = [
            lane,
            row.get(
                "game_key"
            ),
            row.get(
                "nhl_player_id"
            ),
            row.get(
                "market_subtype"
            ),
            row.get(
                "side"
            ),
            row.get(
                "line"
            ),
        ]


    else:

        identity = [
            lane,
            row.get(
                "leg1_lane"
            ),
            row.get(
                "leg1_game"
            ),
            row.get(
                "leg1_player"
            ),
            row.get(
                "leg1_market"
            ),
            row.get(
                "leg1_selection"
            ),
            row.get(
                "leg1_line"
            ),
            row.get(
                "leg2_lane"
            ),
            row.get(
                "leg2_game"
            ),
            row.get(
                "leg2_player"
            ),
            row.get(
                "leg2_market"
            ),
            row.get(
                "leg2_selection"
            ),
            row.get(
                "leg2_line"
            ),
        ]


    raw = json.dumps(
        [
            clean(
                x
            )
            for x in identity
        ],
        separators=(
            ",",
            ":",
        ),
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
    semantic = {}


    for lane, path in FILES.items():

        rows = read_rows(
            path
        )

        all_rows[
            lane
        ] = rows

        semantic[
            lane
        ] = sorted(
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


    raw = json.dumps(
        semantic,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )


    bundle_hash = hashlib.sha256(
        raw.encode()
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
                    "UNCHANGED NHL RECOMMENDATION BUNDLE"
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
            fieldnames=FIELDS,
        )


        if not exists:
            writer.writeheader()


        for lane, rows in all_rows.items():

            for row in rows:

                if lane == "GAME":

                    game_key = row.get(
                        "game_key",
                        ""
                    )

                    start = row.get(
                        "start_dt",
                        ""
                    )

                    player_id = ""
                    player = ""

                    market = row.get(
                        "market_canonical",
                        ""
                    )

                    stat_type = ""

                    selection = row.get(
                        "selection_canonical",
                        ""
                    )

                    side = selection

                    line = row.get(
                        "line_group",
                        ""
                    )

                    decision = row.get(
                        "decision",
                        ""
                    )

                    score = row.get(
                        "evidence_score",
                        ""
                    )


                elif lane in {
                    "PROP",
                    "PRIZEPICKS",
                }:

                    game_key = row.get(
                        "game_key",
                        ""
                    )

                    start = row.get(
                        "start_dt",
                        row.get(
                            "start",
                            "",
                        ),
                    )

                    player_id = row.get(
                        "nhl_player_id",
                        ""
                    )

                    player = (
                        row.get(
                            "player"
                        )
                        or row.get(
                            "canonical_player"
                        )
                        or ""
                    )

                    market = row.get(
                        "market_subtype",
                        ""
                    )

                    stat_type = row.get(
                        "stat_type",
                        ""
                    )

                    selection = row.get(
                        "side",
                        ""
                    )

                    side = selection

                    line = row.get(
                        "line",
                        ""
                    )

                    decision = row.get(
                        "decision",
                        ""
                    )

                    score = row.get(
                        "evidence_score",
                        ""
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

                    start = ""
                    player_id = ""
                    player = ""
                    market = "PARLAY"
                    stat_type = ""
                    selection = ""
                    side = ""
                    line = ""

                    decision = row.get(
                        "status",
                        ""
                    )

                    score = row.get(
                        "evidence_score",
                        ""
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

                    "start":
                        start,

                    "nhl_player_id":
                        player_id,

                    "player":
                        player,

                    "market":
                        market,

                    "stat_type":
                        stat_type,

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
        "NHL SNAPSHOT:",
        snap
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
            len(
                x
            )
            for x in all_rows.values()
        ),
    )


if __name__ == "__main__":
    main()
