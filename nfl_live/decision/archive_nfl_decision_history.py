#!/usr/bin/env python3

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
    / "nfl_live"
    / "decision"
)

HISTORY = (
    DEC
    / "history"
)

SNAPSHOTS = (
    HISTORY
    / "snapshots"
)

LEDGER = (
    HISTORY
    / "NFL_RECOMMENDATION_LEDGER.csv"
)


ARCHIVE_FILES = [
    "NFL_GAME_DECISIONS.csv",
    "NFL_GAME_FINALISTS.csv",

    "NFL_PROP_DECISIONS.csv",
    "NFL_PROP_FINALISTS.csv",

    "NFL_PRIZEPICKS_DECISIONS.csv",
    "NFL_PRIZEPICKS_FINALISTS.csv",

    "NFL_PARLAY_CANDIDATES.csv",
    "NFL_PARLAYS_TODAY.csv",

    "NFL_DECISION_BRAIN_RECEIPT.json",
    "NFL_DECISION_SANITY_RECEIPT.json",
    "NFL_PARLAY_RECEIPT.json",
]


RECOMMENDATION_FILES = {
    "GAME":
        "NFL_GAME_FINALISTS.csv",

    "PROP":
        "NFL_PROP_FINALISTS.csv",

    "PRIZEPICKS":
        "NFL_PRIZEPICKS_FINALISTS.csv",

    "PARLAY":
        "NFL_PARLAYS_TODAY.csv",
}


LEDGER_FIELDS = [
    "snapshot_at",
    "bundle_hash",
    "lane",
    "recommendation_key",
    "source_file",

    "event_id",
    "start",
    "game_key",

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

    return str(
        value
    ).strip()


def first(
    row,
    *names,
):
    for name in names:

        value = clean(
            row.get(name)
        )

        if value:
            return value

    return ""


def file_hash(path):
    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def current_sources():
    sources = []

    for filename in ARCHIVE_FILES:

        path = (
            DEC
            / filename
        )

        if not path.exists():
            continue

        sources.append(
            {
                "filename":
                    filename,

                "path":
                    path,

                "sha256":
                    file_hash(path),

                "size":
                    path.stat().st_size,

                "mtime":
                    datetime.fromtimestamp(
                        path.stat().st_mtime,
                        tz=timezone.utc,
                    ).isoformat(),
            }
        )

    return sources


def bundle_hash(
    sources,
):
    payload = [
        (
            x["filename"],
            x["sha256"],
        )
        for x in sources
    ]

    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode()

    return hashlib.sha256(
        raw
    ).hexdigest()


def existing_bundle(
    digest,
):
    for manifest in (
        SNAPSHOTS
        .glob(
            "*/manifest.json"
        )
    ):
        try:
            data = json.loads(
                manifest.read_text()
            )

        except Exception:
            continue

        if (
            data.get(
                "bundle_hash"
            )
            == digest
        ):
            return manifest.parent

    return None


def recommendation_identity(
    lane,
    row,
):

    if lane == "GAME":

        identity = {
            "game":
                first(
                    row,
                    "game_key",
                    "game_pair",
                ),

            "market":
                first(
                    row,
                    "market",
                ),

            "selection":
                first(
                    row,
                    "selection",
                ),

            "line":
                first(
                    row,
                    "line",
                ),
        }


    elif lane in {
        "PROP",
        "PRIZEPICKS",
    }:

        identity = {
            "event":
                first(
                    row,
                    "event_id",
                    "event_id_dfs",
                    "event_id_sportsbook",
                ),

            "player":
                first(
                    row,
                    "player_key",
                    "canonical_player_identity",
                    "player",
                    "player_dfs",
                    "player_sportsbook",
                ),

            "market":
                first(
                    row,
                    "market_subtype",
                    "market",
                    "stat_type",
                ),

            "side":
                first(
                    row,
                    "side",
                ),

            "line":
                first(
                    row,
                    "line",
                    "dfs_line",
                ),
        }


    else:

        identity = {
            "leg1_kind":
                first(
                    row,
                    "leg1_kind",
                ),

            "leg1_event":
                first(
                    row,
                    "leg1_event",
                ),

            "leg1_player":
                first(
                    row,
                    "leg1_player",
                ),

            "leg1_market":
                first(
                    row,
                    "leg1_market",
                ),

            "leg1_selection":
                first(
                    row,
                    "leg1_selection",
                ),

            "leg1_line":
                first(
                    row,
                    "leg1_line",
                ),

            "leg2_kind":
                first(
                    row,
                    "leg2_kind",
                ),

            "leg2_event":
                first(
                    row,
                    "leg2_event",
                ),

            "leg2_player":
                first(
                    row,
                    "leg2_player",
                ),

            "leg2_market":
                first(
                    row,
                    "leg2_market",
                ),

            "leg2_selection":
                first(
                    row,
                    "leg2_selection",
                ),

            "leg2_line":
                first(
                    row,
                    "leg2_line",
                ),
        }


    # Lane is part of recommendation identity.
    # A PrizePicks projection and a sportsbook prop
    # may have the same player / market / side / line
    # but they are distinct Sports HULK recommendations.
    identity = {
        "lane": lane,
        **identity,
    }

    raw = json.dumps(
        identity,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    ).encode()

    return hashlib.sha256(
        raw
    ).hexdigest()


def ledger_row(
    lane,
    filename,
    row,
    snapshot_at,
    digest,
):

    if lane == "GAME":

        event_id = ""
        start = first(
            row,
            "start",
        )

        game_key = first(
            row,
            "game_key",
            "game_pair",
        )

        player = ""
        team = ""

        market = first(
            row,
            "market",
        )

        selection = first(
            row,
            "selection",
        )

        side = ""

        line = first(
            row,
            "line",
        )

        decision = first(
            row,
            "decision",
        )

        score = first(
            row,
            "hulk_market_score",
        )


    elif lane == "PROP":

        event_id = first(
            row,
            "event_id_dfs",
            "event_id_sportsbook",
        )

        start = first(
            row,
            "start_dfs",
            "start_sportsbook",
        )

        game_key = ""

        player = first(
            row,
            "canonical_player_identity",
            "player_dfs",
            "player_sportsbook",
        )

        team = first(
            row,
            "identity_team",
            "player_team",
            "prop_team",
        )

        market = first(
            row,
            "market_subtype",
            "market",
            "stat_type",
        )

        selection = first(
            row,
            "side",
        )

        side = first(
            row,
            "side",
        )

        line = first(
            row,
            "line",
            "dfs_line",
        )

        decision = first(
            row,
            "decision",
        )

        score = first(
            row,
            "hulk_prop_score",
        )


    elif lane == "PRIZEPICKS":

        event_id = first(
            row,
            "event_id",
        )

        start = first(
            row,
            "start",
        )

        game_key = ""

        player = first(
            row,
            "player",
        )

        team = first(
            row,
            "identity_team",
        )

        market = first(
            row,
            "market_subtype",
        )

        selection = first(
            row,
            "side",
        )

        side = first(
            row,
            "side",
        )

        line = first(
            row,
            "line",
        )

        decision = first(
            row,
            "decision",
        )

        score = first(
            row,
            "hulk_prop_score",
        )


    else:

        event_id = "|".join(
            filter(
                None,
                [
                    first(
                        row,
                        "leg1_event",
                    ),

                    first(
                        row,
                        "leg2_event",
                    ),
                ],
            )
        )

        start = first(
            row,
            "generated_at",
        )

        game_key = event_id

        player = "|".join(
            filter(
                None,
                [
                    first(
                        row,
                        "leg1_player",
                    ),

                    first(
                        row,
                        "leg2_player",
                    ),
                ],
            )
        )

        team = ""

        market = first(
            row,
            "parlay_type",
        )

        selection = first(
            row,
            "leg_summary",
        )

        side = ""
        line = ""

        decision = first(
            row,
            "status",
        )

        score = first(
            row,
            "parlay_score",
        )


    return {
        "snapshot_at":
            snapshot_at,

        "bundle_hash":
            digest,

        "lane":
            lane,

        "recommendation_key":
            recommendation_identity(
                lane,
                row,
            ),

        "source_file":
            filename,

        "event_id":
            event_id,

        "start":
            start,

        "game_key":
            game_key,

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
                sort_keys=True,
                separators=(
                    ",",
                    ":",
                ),
            ),
    }


def append_ledger(
    snapshot_at,
    digest,
):
    rows = []


    for lane, filename in (
        RECOMMENDATION_FILES.items()
    ):

        path = (
            DEC
            / filename
        )

        if not path.exists():
            continue


        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:

            reader = csv.DictReader(
                f
            )

            for row in reader:

                rows.append(
                    ledger_row(
                        lane,
                        filename,
                        row,
                        snapshot_at,
                        digest,
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

        writer.writerows(
            rows
        )


    return rows


def main():

    HISTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    SNAPSHOTS.mkdir(
        parents=True,
        exist_ok=True,
    )


    sources = current_sources()

    if not sources:

        raise SystemExit(
            "No NFL decision files found."
        )


    digest = bundle_hash(
        sources
    )


    already = existing_bundle(
        digest
    )

    if already:

        print(
            "UNCHANGED DECISION BUNDLE:",
            digest[:12],
        )

        print(
            "EXISTING SNAPSHOT:",
            already,
        )

        return


    now = datetime.now(
        timezone.utc
    )

    snapshot_at = (
        now.isoformat()
    )

    stamp = (
        now.strftime(
            "%Y%m%dT%H%M%SZ"
        )
    )


    target = (
        SNAPSHOTS
        / (
            stamp
            + "_"
            + digest[:12]
        )
    )

    target.mkdir(
        parents=True,
        exist_ok=False,
    )


    manifest_files = []


    for item in sources:

        src = item[
            "path"
        ]

        dst = (
            target
            / src.name
        )

        shutil.copy2(
            src,
            dst,
        )

        manifest_files.append(
            {
                "filename":
                    src.name,

                "sha256":
                    item[
                        "sha256"
                    ],

                "size":
                    item[
                        "size"
                    ],

                "mtime":
                    item[
                        "mtime"
                    ],
            }
        )


    ledger_rows = append_ledger(
        snapshot_at,
        digest,
    )


    lane_counts = {}

    for row in ledger_rows:

        lane = row[
            "lane"
        ]

        lane_counts[
            lane
        ] = (
            lane_counts.get(
                lane,
                0,
            )
            + 1
        )


    manifest = {
        "sport":
            "NFL",

        "snapshot_at":
            snapshot_at,

        "bundle_hash":
            digest,

        "source_files":
            manifest_files,

        "recommendation_rows":
            len(
                ledger_rows
            ),

        "lane_counts":
            lane_counts,
    }


    (
        target
        / "manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


    print(
        "NEW NFL DECISION SNAPSHOT:",
        target
    )

    print(
        "BUNDLE HASH:",
        digest[:12],
    )

    print(
        "RECOMMENDATION ROWS:",
        len(
            ledger_rows
        ),
    )


    for lane in sorted(
        lane_counts
    ):

        print(
            lane,
            lane_counts[
                lane
            ],
        )


if __name__ == "__main__":
    main()
