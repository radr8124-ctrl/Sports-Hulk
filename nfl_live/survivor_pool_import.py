from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib
import json
import re

import pandas as pd
from pypdf import PdfReader


ROOT = Path("/home/ubuntu/sports-hulk")

BASE = ROOT / "nfl_live" / "survivor_pool"
RAW = BASE / "raw"
SNAPSHOTS = BASE / "snapshots"
DERIVED = BASE / "derived"

for p in (RAW, SNAPSHOTS, DERIVED):
    p.mkdir(parents=True, exist_ok=True)


TEAM_MAP = {
    "49ERS": "San Francisco 49ers",
    "BEARS": "Chicago Bears",
    "BENGALS": "Cincinnati Bengals",
    "BILLS": "Buffalo Bills",
    "BRONCOS": "Denver Broncos",
    "BROWNS": "Cleveland Browns",
    "BUCCANEERS": "Tampa Bay Buccaneers",
    "CARDINALS": "Arizona Cardinals",
    "CHARGERS": "Los Angeles Chargers",
    "CHIEFS": "Kansas City Chiefs",
    "COLTS": "Indianapolis Colts",
    "COWBOYS": "Dallas Cowboys",
    "DOLPHINS": "Miami Dolphins",
    "EAGLES": "Philadelphia Eagles",
    "FALCONS": "Atlanta Falcons",
    "GIANTS": "New York Giants",
    "JAGS": "Jacksonville Jaguars",
    "JAGUARS": "Jacksonville Jaguars",
    "JETS": "New York Jets",
    "LIONS": "Detroit Lions",
    "PACKERS": "Green Bay Packers",
    "PANTHERS": "Carolina Panthers",
    "PATRIOTS": "New England Patriots",
    "RAIDERS": "Las Vegas Raiders",
    "RAMS": "Los Angeles Rams",
    "RAVENS": "Baltimore Ravens",
    "SAINTS": "New Orleans Saints",
    "SEAHAWKS": "Seattle Seahawks",
    "STEELERS": "Pittsburgh Steelers",
    "TEXANS": "Houston Texans",
    "TITANS": "Tennessee Titans",
    "VIKINGS": "Minnesota Vikings",
}


SPECIAL_WORDS = {
    "XXXXXXXXXXXXX",
    "NAME",
    "WEEK",
    "TOTAL",
    "GRAND",
    "BACKS",
    "BACK",
    "LEFT",
    "LOST",
    "ENTRIES",
    "BEFORE",
    "AFTER",
}


def normalize_pick(token: str):
    raw = str(token or "").strip().upper()

    if not raw:
        return None, None, raw

    if raw.startswith("XXXXXXXX"):
        return None, None, raw

    marker = None

    if raw.startswith("X") and raw[1:] in TEAM_MAP:
        marker = "X"
        raw_team = raw[1:]
    elif raw.startswith("Y") and raw[1:] in TEAM_MAP:
        marker = "Y"
        raw_team = raw[1:]
    else:
        raw_team = raw

    team = TEAM_MAP.get(raw_team)

    return team, marker, raw


def looks_like_pick(token: str):
    _, marker, raw = normalize_pick(token)

    if raw in TEAM_MAP:
        return True

    if marker in {"X", "Y"}:
        return True

    if raw.startswith("XXXXXXXX"):
        return True

    return False


def extract_text(pdf_path: Path):
    reader = PdfReader(str(pdf_path))

    pages = []

    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        pages.append({
            "page": idx,
            "text": text,
        })

    return pages


def parse_entry_line(line: str, page: int):
    line = " ".join(str(line).split()).strip()

    if not line:
        return None

    upper = line.upper()

    if upper.startswith("NAME WEEK"):
        return None

    if upper.startswith("TOTAL "):
        return None

    if upper.startswith("GRAND TOTAL"):
        return None

    tokens = line.split()

    # Find first token that looks like a pick.
    pick_start = None

    for i, token in enumerate(tokens):
        if looks_like_pick(token):
            pick_start = i
            break

    if pick_start is None:
        return None

    name_tokens = tokens[:pick_start]
    pick_tokens = tokens[pick_start:]

    if not name_tokens:
        return None

    # Last name-side token is commonly the entry number:
    # 01, 02, etc. Preserve labels exactly when no numeric suffix exists.
    entry_suffix = None

    if re.fullmatch(r"\d{1,2}", name_tokens[-1]):
        entry_suffix = name_tokens[-1].zfill(2)
        participant = " ".join(name_tokens[:-1]).strip()
        entry_name = f"{participant} {entry_suffix}"
    else:
        participant = " ".join(name_tokens).strip()
        entry_name = participant

    if not participant:
        return None

    picks = []

    for week_index, token in enumerate(pick_tokens, start=1):
        team, marker, raw_token = normalize_pick(token)

        if raw_token.startswith("XXXXXXXX"):
            break

        if team is None:
            break

        picks.append({
            "week_position": week_index,
            "team": team,
            "marker": marker,
            "raw_token": raw_token,
        })

    if not picks:
        return None

    return {
        "entry_name": entry_name,
        "participant": participant,
        "entry_suffix": entry_suffix,
        "page": page,
        "raw_line": line,
        "picks": picks,
    }


def import_pdf(pdf_bytes: bytes, filename: str):
    sha = hashlib.sha256(pdf_bytes).hexdigest()

    stamp = datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        filename,
    )

    raw_path = RAW / f"{stamp}_{safe_name}"
    raw_path.write_bytes(pdf_bytes)

    pages = extract_text(raw_path)

    entries = []

    for page in pages:
        for line in page["text"].splitlines():
            parsed = parse_entry_line(
                line,
                page["page"],
            )

            if parsed:
                entries.append(parsed)

    if not entries:
        raise RuntimeError(
            "No Survivor entries could be parsed. "
            "Import was not committed."
        )

    # De-duplicate exact entry rows if PDF extraction repeats anything.
    dedup = {}

    for entry in entries:
        key = entry["entry_name"]

        existing = dedup.get(key)

        if existing is None:
            dedup[key] = entry
        elif len(entry["picks"]) > len(existing["picks"]):
            dedup[key] = entry

    entries = list(dedup.values())

    snapshot = {
        "imported_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_filename": filename,
        "source_sha256": sha,
        "page_count": len(pages),
        "entry_count": len(entries),
        "entries": entries,
    }

    snapshot_path = (
        SNAPSHOTS
        / f"SURVIVOR_POOL_{stamp}.json"
    )

    snapshot_path.write_text(
        json.dumps(snapshot, indent=2)
    )

    # -----------------------------------------------
    # BUILD ENTRY LEDGER
    # -----------------------------------------------

    ledger_rows = []

    for entry in entries:
        for pick in entry["picks"]:
            ledger_rows.append({
                "entry_name": entry["entry_name"],
                "participant": entry["participant"],
                "entry_suffix": entry["entry_suffix"],
                "week_position":
                    pick["week_position"],
                "team": pick["team"],
                "marker": pick["marker"],
                "raw_token": pick["raw_token"],
                "page": entry["page"],
                "source_filename": filename,
                "imported_at":
                    snapshot["imported_at"],
            })

    ledger = pd.DataFrame(ledger_rows)

    ledger.to_csv(
        DERIVED / "SURVIVOR_POOL_LEDGER.csv",
        index=False,
    )

    ledger.to_parquet(
        DERIVED / "SURVIVOR_POOL_LEDGER.parquet",
        index=False,
    )

    # -----------------------------------------------
    # CURRENT ENTRY STATE
    # -----------------------------------------------

    state_rows = []

    for entry in entries:

        markers = [
            p["marker"]
            for p in entry["picks"]
            if p["marker"]
        ]

        status = (
            "ELIMINATED"
            if "X" in markers
            else "ACTIVE_OR_UNCONFIRMED"
        )

        used = [
            p["team"]
            for p in entry["picks"]
        ]

        state_rows.append({
            "entry_name": entry["entry_name"],
            "participant": entry["participant"],
            "entry_suffix": entry["entry_suffix"],
            "status": status,
            "weeks_recorded":
                len(entry["picks"]),
            "used_teams":
                " | ".join(used),
            "last_pick":
                used[-1] if used else None,
            "page":
                entry["page"],
        })

    state = pd.DataFrame(state_rows)

    state.to_csv(
        DERIVED / "SURVIVOR_POOL_CURRENT.csv",
        index=False,
    )

    state.to_parquet(
        DERIVED / "SURVIVOR_POOL_CURRENT.parquet",
        index=False,
    )

    # -----------------------------------------------
    # PICK OWNERSHIP BY WEEK
    # -----------------------------------------------

    ownership_rows = []

    if not ledger.empty:

        for week, w in ledger.groupby(
            "week_position"
        ):
            total = len(w)

            counts = Counter(w["team"])

            for team, count in counts.items():
                ownership_rows.append({
                    "week_position": int(week),
                    "team": team,
                    "pick_count": int(count),
                    "pool_rows_with_pick":
                        int(total),
                    "pick_share_pct":
                        round(
                            count / total * 100,
                            2,
                        ),
                })

    ownership = pd.DataFrame(
        ownership_rows
    )

    ownership.to_csv(
        DERIVED / "SURVIVOR_POOL_OWNERSHIP.csv",
        index=False,
    )

    ownership.to_parquet(
        DERIVED / "SURVIVOR_POOL_OWNERSHIP.parquet",
        index=False,
    )

    # -----------------------------------------------
    # ANNIE VIEW
    # -----------------------------------------------

    annie = state[
        state["participant"].str.upper()
        == "ANNIE G"
    ].copy()

    annie.to_csv(
        DERIVED / "ANNIE_G_POOL_ENTRIES.csv",
        index=False,
    )

    return {
        "source_filename": filename,
        "source_sha256": sha,
        "pages": len(pages),
        "entries": len(entries),
        "ledger_rows": len(ledger),
        "snapshot_path": str(
            snapshot_path
        ),
        "annie_entries": len(annie),
    }
