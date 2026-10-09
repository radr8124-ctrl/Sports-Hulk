#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import csv
import hashlib
import json
import shutil

try:
    from cfb_live.decision.cfb_incremental_ledger_index import latest_source_rows_if_complete
except ModuleNotFoundError:
    from cfb_incremental_ledger_index import latest_source_rows_if_complete


ROOT = Path(
    "/home/ubuntu/sports-hulk"
)

DEC = (
    ROOT
    / "cfb_live"
    / "decision"
)

HIST = DEC / "history"
SNAPS = HIST / "snapshots"

LEDGER = (
    HIST
    / "CFB_RECOMMENDATION_LEDGER.csv"
)

LATEST = (
    HIST
    / "LATEST_CFB_SNAPSHOT.json"
)


SOURCES = {
    "GAME":
        DEC
        / "CFB_GAME_DECISIONS.csv",

    "PARLAY":
        DEC
        / "CFB_PARLAYS_TODAY.csv",
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


def redundant_clock_only_observation(previous:dict|None,current:dict)->bool:
    """Suppress solely derived countdown recurrence, NEVER a changed source fact.

    Original immutable evidence and per-bundle snapshot manifest remain on disk.
    Every changed odds, score, decision, player, game or status is appended.
    """
    if not isinstance(previous,dict) or not isinstance(current,dict):return False
    for field in FIELDS:
        if field in ("snapshot_at","bundle_hash","payload_json"):
            continue
        if str(previous.get(field) or "")!=str(current.get(field) or ""):
            return False
    try:
        old=json.loads(previous["payload_json"])
        new=json.loads(current["payload_json"])
    except (KeyError,TypeError,ValueError):return False
    if not isinstance(old,dict) or not isinstance(new,dict):return False
    old.pop("hours_to_start",None)
    new.pop("hours_to_start",None)
    return json.dumps(old,sort_keys=True,separators=(",",":"))==json.dumps(new,sort_keys=True,separators=(",",":"))


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
                    "UNCHANGED CFB RECOMMENDATION BUNDLE"
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
    clock_only_skipped = 0
    try:
        previous_index = latest_source_rows_if_complete(source=LEDGER)
        index_check_status = "VERIFIED_COMPLETE_SOURCE_INDEX_CLOCK_ONLY_DELTA_GUARD"
    except ValueError as exc:
        if str(exc) not in ("CFB_COMPLETE_SOURCE_INDEX_MISSING","CFB_SOURCE_INDEX_NOT_FULLY_CAUGHT_UP"):
            raise  # A changed source fingerprint must never be ignored.
        previous_index = {}
        index_check_status = "INCOMPLETE_INDEX_FALLBACK_APPEND_EVERY_ORIGINAL_OBSERVATION"


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


                if redundant_clock_only_observation(
                    previous_index.get(output["recommendation_key"]),output
                ):
                    clock_only_skipped += 1
                    continue

                writer.writerow(
                    output
                )

                rows_added += 1


    manifest["source_index_verification"] = index_check_status
    manifest["original_recommendation_rows_appended"] = rows_added
    manifest["derived_clock_only_rows_not_repeated"] = clock_only_skipped
    manifest["old_raw_source_history_rewritten_or_truncated"] = False
    (snapshot / "manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True))

    LATEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "CFB SNAPSHOT:",
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
