"""Proof-only MLB player-ID crosswalk from two official-derived sources.

A normalized *exact* player name AND team must have the same unique numeric MLB
ID in both existing player-context and pregame official player-game history.
Crosswalks can confirm identity only inside an already uniquely matched
provider event/official MLB game box; they cannot infer games, played stats,
wager profitability or unrecorded betting selections.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path
import csv
import re
import unicodedata

CROSSWALK_FILES = (
    "mlb_live/derived/MLB_PLAYER_CONTEXT.csv",
    "intelligence_warehouse/mlb_player_history/MLB_PLAYER_GAME_HISTORY.csv",
)
OFFICIAL_HISTORY_SOURCE = "MLB_STATSAPI_OFFICIAL_BOXSCORE"
OFFICIAL_HISTORY_TIER = "OFFICIAL_LEAGUE_FEED"


def person_key(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", ascii_name)


def person_id(value):
    value = str(value or "").strip()
    if re.fullmatch(r"[0-9]+(?:\.0)?", value):
        return value[:-2] if value.endswith(".0") else value
    return ""


def source_fingerprint(root: Path) -> dict | None:
    root = Path(root)
    sources = [root / path for path in CROSSWALK_FILES]
    if not all(path.is_file() and path.stat().st_size for path in sources):
        return None
    digests = {}
    for base, path in zip(CROSSWALK_FILES, sources):
        hasher = sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        digests[base] = hasher.hexdigest()
    return digests


def indexed_verified_ids(root: Path, wanted_names: set[str], wanted_seasons: set[str]):
    """Read only name/ID/team evidence relevant to frozen pending cases."""
    sources = [Path(root) / path for path in CROSSWALK_FILES]
    if not all(path.exists() for path in sources):
        return {}, {"status": "CROSSWALK_SOURCES_MISSING", "unique_ids": 0}
    context = defaultdict(set)
    history = defaultdict(lambda: defaultdict(set))
    stats = Counter()
    with sources[0].open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not {"player_id", "player", "team"}.issubset(reader.fieldnames or []):
            raise ValueError("MLB player context lacks official identity columns")
        for row in reader:
            name, team, pid = person_key(row["player"]), person_key(row["team"]), person_id(row["player_id"])
            if name in wanted_names and team and pid:
                context[(name, team)].add(pid)
                stats["context_rows"] += 1

    with sources[1].open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"player_id", "player", "team", "official_date", "season", "source", "source_tier", "status"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("MLB StatsAPI history lacks verified player identity columns")
        for row in reader:
            name, team, pid = person_key(row["player"]), person_key(row["team"]), person_id(row["player_id"])
            if not (name in wanted_names and team and pid):
                continue
            if row["source"] != OFFICIAL_HISTORY_SOURCE or row["source_tier"] != OFFICIAL_HISTORY_TIER:
                continue
            if row["season"] not in wanted_seasons or row["status"] not in {"Final", "Completed Early"}:
                continue
            try:
                evidence_day = date.fromisoformat(row["official_date"])
            except (ValueError, TypeError):
                continue
            history[(name, team)][pid].add(evidence_day)
            stats["official_history_rows"] += 1

    proven = {}
    all_pairs = set(context) | set(history)
    for pair in all_pairs:
        context_ids = context.get(pair, set())
        historical_ids = set(history.get(pair, {}))
        if len(context_ids) == 1 and context_ids == historical_ids:
            pid = next(iter(context_ids))
            dates = history[pair][pid]
            if dates:
                proven[pair] = {
                    "player_id": pid,
                    "earliest_official_box_date": min(dates).isoformat(),
                    "official_prior_game_count": len(dates),
                }
        elif pair in history and pair in context:
            stats["conflicting_official_identity_pairs"] += 1
    stats["exact_unique_official_id_pairs"] = len(proven)
    stats["status"] = "READY"
    return proven, dict(stats)
