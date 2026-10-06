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
    / "cbb_live"
    / "decision"
)

HIST = DEC / "history"
SNAPS = HIST / "snapshots"

LEDGER = (
    HIST
    / "CBB_RECOMMENDATION_LEDGER.csv"
)

LATEST = (
    HIST
    / "LATEST_CBB_SNAPSHOT.json"
)


SOURCES = {
    "GAME":
        DEC
        / "CBB_GAME_DECISIONS.csv",

    "PARLAY":
        DEC
        / "CBB_PARLAYS_TODAY.csv",
}


FIELDS = [
    "snapshot_at",
    "bundle_hash",
    "lane",
    "recommendation_key",
    "source_file",
    "game_key",
    "schedule_event_id",
    "market",
    "selection",
    "line",
    "decision",
    "score",
    "context_stage",
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
            "schedule_event_id",
            "market_canonical",
            "selection_canonical",
            "line",
            "sportsbook_count",
            "provider_count",
            "median_price_american",
            "selected_current_games",
            "opponent_current_games",
            "prior_elo_edge",
            "prior_srs_edge",
            "current_margin_edge",
            "context_stage",
            "context_direction",
            "evidence_score",
            "decision",
        ]


    else:

        names = [
            "leg1_game",
            "leg1_selection",
            "leg1_market",
            "leg1_line",
            "leg1_score",
            "leg2_game",
            "leg2_selection",
            "leg2_market",
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
                "line"
            ),
        ]


    else:

        identity = [
            lane,
            row.get(
                "leg1_game"
            ),
            row.get(
                "leg1_selection"
            ),
            row.get(
                "leg1_market"
            ),
            row.get(
                "leg1_line"
            ),
            row.get(
                "leg2_game"
            ),
            row.get(
                "leg2_selection"
            ),
            row.get(
                "leg2_market"
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


def ensure_ledger():

    if LEDGER.exists():
        return


    with LEDGER.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
        )

        writer.writeheader()


def main():

    HIST.mkdir(
        parents=True,
        exist_ok=True,
    )

    SNAPS.mkdir(
        parents=True,
        exist_ok=True,
    )

    ensure_ledger()


    rows_by_lane = {}

    semantic = {}


    for lane, path in SOURCES.items():

        rows = read_rows(
            path
        )

        rows_by_lane[
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

            previous = json.loads(
                LATEST.read_text()
            )

            if (
                previous.get(
                    "bundle_hash"
                )
                == bundle_hash
            ):

                print(
                    "UNCHANGED CBB RECOMMENDATION BUNDLE"
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


    snapshot = (
        SNAPS
        / (
            stamp
            + "_"
            + bundle_hash[
                :12
            ]
        )
    )


    snapshot.mkdir(
        parents=True,
        exist_ok=False,
    )


    for path in SOURCES.values():

        if path.exists():

            shutil.copy2(
                path,
                snapshot
                / path.name,
            )


    manifest = {
        "snapshot_at":
            now.isoformat(),

        "bundle_hash":
            bundle_hash,

        "rows":
            {
                lane:
                    len(
                        rows
                    )

                for lane, rows
                in rows_by_lane.items()
            },
    }


    (
        snapshot
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    rows_added = 0


    with LEDGER.open(
        "a",
        encoding="utf-8",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=FIELDS,
        )


        for lane, rows in (
            rows_by_lane.items()
        ):

            for row in rows:

                if lane == "GAME":

                    output = {
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
                            SOURCES[
                                lane
                            ].name,

                        "game_key":
                            row.get(
                                "game_key",
                                "",
                            ),

                        "schedule_event_id":
                            row.get(
                                "schedule_event_id",
                                "",
                            ),

                        "market":
                            row.get(
                                "market_canonical",
                                "",
                            ),

                        "selection":
                            row.get(
                                "selection_canonical",
                                "",
                            ),

                        "line":
                            row.get(
                                "line",
                                "",
                            ),

                        "decision":
                            row.get(
                                "decision",
                                "",
                            ),

                        "score":
                            row.get(
                                "evidence_score",
                                "",
                            ),

                        "context_stage":
                            row.get(
                                "context_stage",
                                "",
                            ),

                        "payload_json":
                            json.dumps(
                                row,
                                separators=(
                                    ",",
                                    ":",
                                ),
                            ),
                    }


                else:

                    output = {
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
                            SOURCES[
                                lane
                            ].name,

                        "game_key":
                            (
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
                            ),

                        "schedule_event_id":
                            "",

                        "market":
                            "PARLAY",

                        "selection":
                            "",

                        "line":
                            "",

                        "decision":
                            row.get(
                                "status",
                                "",
                            ),

                        "score":
                            row.get(
                                "evidence_score",
                                "",
                            ),

                        "context_stage":
                            "CURRENT_SEASON_READY",

                        "payload_json":
                            json.dumps(
                                row,
                                separators=(
                                    ",",
                                    ":",
                                ),
                            ),
                    }


                writer.writerow(
                    output
                )

                rows_added += 1


    LATEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "CBB SNAPSHOT:",
        snapshot
    )

    print(
        "BUNDLE HASH:",
        bundle_hash[
            :12
        ],
    )

    print(
        "LEDGER ROWS ADDED:",
        rows_added
    )


if __name__ == "__main__":
    main()
