"""Archive current NFL availability inputs; gate evidence against a future quote.

No historical backfill, starter inference, probability adjustment, or trade.
Timestamp eligibility alone does not authenticate the publisher's claim.
"""
import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def eligibility(record, *, event_id, quote_at, kickoff_at):
    """Reasons a record cannot enter a quote-time feature set; [] means timing/identity passed."""
    reasons = []
    quote, kickoff = timestamp(quote_at), timestamp(kickoff_at)
    if quote is None:
        reasons.append("INVALID_QUOTE_TIME")
    if kickoff is None:
        reasons.append("INVALID_KICKOFF_TIME")
    if quote and kickoff and quote >= kickoff:
        reasons.append("QUOTE_NOT_PREGAME")
    if not event_id or record.get("event_id") != event_id:
        reasons.append("EVENT_MISMATCH")
    for key in ("team", "player_id", "source_url"):
        if not record.get(key):
            reasons.append("MISSING_" + key.upper())
    if not re.fullmatch(r"[0-9a-f]{64}", record.get("archive_sha256", "")):
        reasons.append("MISSING_ARCHIVE_HASH")
    times = []
    for field, label in (("source_published_at", "PUBLICATION"),
                         ("source_ingested_at", "INGESTION"), ("captured_at", "CAPTURE")):
        value = record.get(field)
        t = timestamp(value)
        times.append(t)
        if not value:
            reasons.append("MISSING_" + label + "_TIME")
        elif t is None:
            reasons.append("INVALID_" + label + "_TIME")
        elif quote and t > quote:
            reasons.append("AFTER_QUOTE")
    if all(times) and not times[0] <= times[1] <= times[2]:
        reasons.append("TIMESTAMP_ORDER_INVALID")
    kind = record.get("evidence_kind")
    if kind == "news_context":
        reasons.append("CONTEXT_ONLY")
    elif kind == "confirmed_starting_qb":
        # None of the existing adapters verifies an event-specific starter announcement.
        reasons.append("STARTER_CONFIRMATION_NOT_VERIFIED")
    elif kind != "injury_status":
        reasons.append("UNSUPPORTED_EVIDENCE_KIND")
    return sorted(set(reasons))


def capture(inputs, output, captured_at):
    """Create an exclusive archive from existing local files, with original times unmodified."""
    captured = timestamp(captured_at)
    if captured is None:
        raise ValueError("capture time must be timezone-aware")
    inputs, output = Path(inputs), Path(output)
    # Read exactly once: hashes, raw archive and normalized records share the same bytes.
    payloads = {name: (inputs / name).read_bytes() for name in
                ("AVAILABILITY_TIMELINE.csv", "AVAILABILITY_REPORTS_CURRENT.csv")}
    archive = output / captured.strftime("%Y%m%dT%H%M%S%fZ")
    archive.mkdir(parents=True, exist_ok=False)
    hashes = {}
    records = []
    for name, raw in payloads.items():
        hashes[name] = hashlib.sha256(raw).hexdigest()
        (archive / name).write_bytes(raw)
        source_rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        latest = {}
        for row in source_rows:
            if row.get("sport") != "NFL":
                continue
            if name == "AVAILABILITY_TIMELINE.csv":
                key = (row.get("player_id") or row.get("player_key"), row.get("source"))
                observed = timestamp(row.get("observed_at"))
                previous = latest.get(key)
                if previous is None or (observed or datetime.min.replace(tzinfo=timezone.utc)) > (
                        timestamp(previous.get("observed_at")) or datetime.min.replace(tzinfo=timezone.utc)):
                    latest[key] = row
            else:
                latest[row.get("news_id") or json.dumps(row, sort_keys=True)] = row
        for row in latest.values():
            injury = name == "AVAILABILITY_TIMELINE.csv"
            records.append(dict(
                evidence_kind="injury_status" if injury else "news_context",
                event_id=row.get("event_id", ""), team=row.get("team", ""),
                player_id=row.get("player_id", ""), player=row.get("player", ""),
                position=row.get("position", ""), source=row.get("source", ""),
                source_url=row.get("source_url", ""),
                source_published_at=row.get("source_record_at", "") if injury else row.get("published_at", ""),
                source_ingested_at=row.get("observed_at", "") if injury else row.get("ingested_at", ""),
                captured_at=captured_at, archive_sha256=hashes[name], archive_file=name,
                status=row.get("status_normalized", "") if injury else "",
                headline=row.get("headline", "") if not injury else "",
                verified_starting_qb=False,
            ))
    encoded = "".join(json.dumps(r, sort_keys=True) + "\n" for r in records).encode()
    (archive / "records.jsonl").write_bytes(encoded)
    receipt = dict(
        schema_version=1, captured_at=captured_at, archive_directory=str(archive.resolve()),
        source_file_sha256=hashes, records_sha256=hashlib.sha256(encoded).hexdigest(),
        injury_records=sum(r["evidence_kind"] == "injury_status" for r in records),
        news_context_records=sum(r["evidence_kind"] == "news_context" for r in records),
        records_with_publication_time=sum(timestamp(r["source_published_at"]) is not None for r in records),
        injury_records_with_publication_time=sum(
            r["evidence_kind"] == "injury_status" and timestamp(r["source_published_at"]) is not None
            for r in records),
        confirmed_starting_qb_records=0, quote_linked_feature_sets=0,
        status="ARCHIVED_ONLY_NOT_A_MODEL_FEATURE_SET",
        limitations=[
            "Local export bytes are preserved; these are not original upstream HTTP payloads.",
            "Capture time is now, even when source observation is older; no retroactive quote joins.",
            "Missing publication timestamps remain empty.",
            "News is context, not verified player state. QB injury status is not a starting-QB announcement.",
            "Event identity, publisher verification, freshness and future quote joins remain required.",
            "This command is manual; no recurring collection or profitable edge is implied.",
        ],
    )
    (archive / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--inputs", type=Path, default=root / "intelligence_warehouse/availability")
    parser.add_argument("--output", type=Path, default=root / "nfl_live/prediction_markets/prospective_availability")
    args = parser.parse_args()
    receipt = capture(args.inputs, args.output, datetime.now(timezone.utc).isoformat())
    print(json.dumps(receipt, indent=2))
