#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import pandas as pd


ROOT = Path("/home/ubuntu/sports-hulk")
DEC = ROOT / "mlb_live" / "decision"
HIST = DEC / "history"
SNAPS = HIST / "snapshots"

SOURCES = {
    "GAME": DEC / "MLB_GAME_DECISIONS.csv",
    "PROP": DEC / "MLB_PROP_FINALISTS.csv",
    "PRIZEPICKS": DEC / "MLB_PRIZEPICKS_FINALISTS.csv",
    "PARLAY": DEC / "MLB_PARLAYS_TODAY.csv",
}

LEDGER = HIST / "MLB_RECOMMENDATION_LEDGER.csv"
LATEST = HIST / "LATEST_MLB_SNAPSHOT.json"

FIELDS = [
    "snapshot_at",
    "bundle_hash",
    "lane",
    "recommendation_key",
    "source_file",
    "game_key",
    "official_gamePk",
    "event_id",
    "market",
    "selection",
    "line",
    "decision",
    "score",
    "player_id",
    "player",
    "metric",
    "payload_json",
]


def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def clean(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def norm(value):
    import re
    import unicodedata

    text = unicodedata.normalize(
        "NFKD",
        str(value or ""),
    ).encode(
        "ascii",
        "ignore",
    ).decode().lower()

    return re.sub(
        r"[^a-z0-9]+",
        "",
        text,
    )


def game_candidates():
    d = read_csv(SOURCES["GAME"])
    if d.empty:
        return d

    d = d.copy()
    hours = pd.to_numeric(
        d.get("hours_to_start"),
        errors="coerce",
    )
    books = pd.to_numeric(
        d.get("sportsbook_count"),
        errors="coerce",
    ).fillna(0)

    finalists = d[
        d["decision"].astype(str).eq("QUALIFIED_RESEARCH")
        & d["market_canonical"].astype(str).eq("MONEYLINE")
    ].copy()

    research = d[
        hours.between(-1, 36, inclusive="both")
        & d["market_canonical"].astype(str).isin(["SPREAD", "TOTAL"])
        & d["decision"].astype(str).eq("MARKET_RESEARCH")
        & books.ge(3)
        & d["official_match"].astype(str).str.lower().isin(["true", "1"])
    ].copy()

    if not research.empty:
        research["_books"] = books.loc[research.index]
        research["_score"] = pd.to_numeric(
            research.get("evidence_score"),
            errors="coerce",
        ).fillna(0)
        research = (
            research
            .sort_values(
                ["_books", "_score"],
                ascending=[False, False],
            )
            .drop_duplicates(
                [
                    "official_gamePk",
                    "market_canonical",
                    "selection_canonical",
                ],
                keep="first",
            )
            .drop(
                columns=["_books", "_score"],
                errors="ignore",
            )
            .head(100)
        )

    return pd.concat(
        [finalists, research],
        ignore_index=True,
        sort=False,
    )


def key_for(lane, row):
    if lane == "GAME":
        identity = [
            lane,
            row.get("official_gamePk"),
            row.get("market_canonical"),
            row.get("selection_canonical"),
            row.get("line"),
            row.get("decision"),
        ]
    elif lane in {"PROP", "PRIZEPICKS"}:
        identity = [
            lane,
            row.get("event_id"),
            row.get("player_id"),
            row.get("metric"),
            row.get("side"),
            row.get("line"),
        ]
    else:
        identity = [
            lane,
            row.get("leg1_game"),
            row.get("leg1_subject"),
            row.get("leg1_market"),
            row.get("leg1_selection"),
            row.get("leg1_line"),
            row.get("leg2_game"),
            row.get("leg2_subject"),
            row.get("leg2_market"),
            row.get("leg2_selection"),
            row.get("leg2_line"),
        ]

    raw = json.dumps(
        [clean(x) for x in identity],
        separators=(",", ":"),
    )

    return hashlib.sha256(
        raw.encode()
    ).hexdigest()


def row_for(lane, row, now, bundle_hash):
    key = key_for(lane, row)

    if lane == "GAME":
        return {
            "snapshot_at": now.isoformat(),
            "bundle_hash": bundle_hash,
            "lane": lane,
            "recommendation_key": key,
            "source_file": SOURCES[lane].name,
            "game_key": clean(row.get("game_key")),
            "official_gamePk": clean(row.get("official_gamePk")),
            "event_id": "",
            "market": clean(row.get("market_canonical")),
            "selection": clean(row.get("selection_canonical")),
            "line": clean(row.get("line")),
            "decision": clean(row.get("decision")),
            "score": clean(row.get("evidence_score")),
            "player_id": "",
            "player": "",
            "metric": "",
            "payload_json": json.dumps(
                row,
                default=str,
                separators=(",", ":"),
            ),
        }

    if lane in {"PROP", "PRIZEPICKS"}:
        return {
            "snapshot_at": now.isoformat(),
            "bundle_hash": bundle_hash,
            "lane": lane,
            "recommendation_key": key,
            "source_file": SOURCES[lane].name,
            "game_key":
                clean(row.get("start"))
                + "|"
                + norm(row.get("away_team"))
                + "|"
                + norm(row.get("home_team")),
            "official_gamePk": "",
            "event_id": clean(row.get("event_id")),
            "market": "PLAYER_TOTAL",
            "selection": clean(row.get("side")),
            "line": clean(row.get("line")),
            "decision": clean(row.get("decision")),
            "score": clean(row.get("evidence_score")),
            "player_id": clean(row.get("player_id")),
            "player": clean(row.get("player")),
            "metric": clean(row.get("metric")),
            "payload_json": json.dumps(
                row,
                default=str,
                separators=(",", ":"),
            ),
        }

    return {
        "snapshot_at": now.isoformat(),
        "bundle_hash": bundle_hash,
        "lane": lane,
        "recommendation_key": key,
        "source_file": SOURCES[lane].name,
        "game_key":
            clean(row.get("leg1_game"))
            + " + "
            + clean(row.get("leg2_game")),
        "official_gamePk": "",
        "event_id": "",
        "market": "PARLAY",
        "selection": "",
        "line": "",
        "decision": clean(row.get("status")),
        "score": clean(row.get("evidence_score")),
        "player_id": "",
        "player": "",
        "metric": "",
        "payload_json": json.dumps(
            row,
            default=str,
            separators=(",", ":"),
        ),
    }


def main():
    HIST.mkdir(parents=True, exist_ok=True)
    SNAPS.mkdir(parents=True, exist_ok=True)

    candidates = {
        "GAME": game_candidates(),
        "PROP": read_csv(SOURCES["PROP"]),
        "PRIZEPICKS": read_csv(SOURCES["PRIZEPICKS"]),
        "PARLAY": read_csv(SOURCES["PARLAY"]),
    }

    semantic = []

    for lane, frame in candidates.items():
        for _, row in frame.iterrows():
            semantic.append({
                "lane": lane,
                "key": key_for(lane, row.to_dict()),
            })

    bundle_hash = hashlib.sha256(
        json.dumps(
            semantic,
            sort_keys=True,
        ).encode()
    ).hexdigest()

    existing = read_csv(LEDGER)

    existing_keys = (
        set(existing["recommendation_key"].astype(str))
        if not existing.empty
        and "recommendation_key" in existing.columns
        else set()
    )

    now = datetime.now(timezone.utc)
    rows = []

    for lane, frame in candidates.items():
        for _, row in frame.iterrows():
            payload = row.to_dict()
            key = key_for(lane, payload)
            if key in existing_keys:
                continue
            rows.append(
                row_for(
                    lane,
                    payload,
                    now,
                    bundle_hash,
                )
            )

    if not rows:
        print("NO NEW MLB LEARNING CANDIDATES")
        print("CANDIDATES:", len(semantic))
        print("BUNDLE HASH:", bundle_hash[:12])
        return

    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    snapshot = SNAPS / f"{stamp}_{bundle_hash[:12]}"
    snapshot.mkdir(parents=True, exist_ok=False)

    for lane, frame in candidates.items():
        frame.to_csv(
            snapshot / f"MLB_{lane}_CANDIDATES.csv",
            index=False,
        )

    new_df = pd.DataFrame(
        rows,
        columns=FIELDS,
    )

    ledger = (
        new_df
        if existing.empty
        else pd.concat(
            [existing, new_df],
            ignore_index=True,
            sort=False,
        )
    )

    ledger.to_csv(
        LEDGER,
        index=False,
    )

    manifest = {
        "snapshot_at": now.isoformat(),
        "bundle_hash": bundle_hash,
        "candidate_counts": {
            lane: int(len(frame))
            for lane, frame in candidates.items()
        },
        "novel_rows": int(len(new_df)),
        "ledger_rows": int(len(ledger)),
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

    LATEST.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )

    print("MLB SNAPSHOT:", snapshot)
    print("CANDIDATES:", len(semantic))
    print("NOVEL ROWS:", len(new_df))
    print("LEDGER ROWS:", len(ledger))
    print("BUNDLE HASH:", bundle_hash[:12])


if __name__ == "__main__":
    main()
