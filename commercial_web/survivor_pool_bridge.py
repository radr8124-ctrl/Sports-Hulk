"""Manager-authorized two-stage Survivor pool PDF/XLSX/CSV import bridge.

Only a server-side authenticated, allowlisted manager may invoke this script.
Preview is read-only; commit uses the existing audited parser with backups.
"""
from __future__ import annotations

import base64
import binascii
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile, BadZipFile
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nfl_live import survivor_pool_upload as upload

MAX_UPLOAD_BYTES = 5_000_000
MAX_XLSX_UNCOMPRESSED = 35_000_000


def decode_pool_file(payload: dict) -> tuple[str, bytes]:
    if not isinstance(payload, dict):
        raise ValueError("Invalid Survivor upload.")
    name = payload.get("filename")
    encoded = payload.get("base64")
    if not isinstance(name, str) or not 1 <= len(name) <= 160:
        raise ValueError("Choose a PDF, XLSX or CSV file.")
    if "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("Use a file name without directory paths.")
    suffix = Path(name).suffix.lower()
    if suffix not in {".pdf", ".xlsx", ".csv"}:
        raise ValueError("Only PDF, XLSX and CSV are supported.")
    if not isinstance(encoded, str) or len(encoded) > 7_000_000:
        raise ValueError("Pool file is too large.")
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("The uploaded file encoding is invalid.")
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Pool file must be between 1 byte and 5 MB.")
    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("This is not a valid PDF file.")
    if suffix == ".xlsx":
        try:
            with ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                size = sum(item.file_size for item in entries)
                if len(entries) > 250 or size > MAX_XLSX_UNCOMPRESSED:
                    raise ValueError("The workbook is too large to process safely.")
                if "xl/workbook.xml" not in archive.namelist():
                    raise ValueError("This is not a valid XLSX workbook.")
        except BadZipFile:
            raise ValueError("This is not a valid XLSX workbook.")
    return name, content


def current_state_version() -> tuple[int, str]:
    state_path = ROOT / "nfl_live/derived/SURVIVOR_ENTRIES.json"
    latest = upload.DERIVED / "LATEST_OFFICIAL_POOL.json"
    if state_path.is_file():
        private_state = json.loads(state_path.read_text())
        pool_week = int(private_state.get("pool_current_week") or 0)
    else:
        pool_week = 0
    latest_bytes = latest.read_bytes() if latest.is_file() else b""
    return pool_week, sha256(latest_bytes).hexdigest()


def check_preview(preview: dict, *, before_week: int, required_sha: str | None = None) -> None:
    count = int(preview.get("entry_count") or 0)
    max_week = int(preview.get("meta", {}).get("current_week") or preview.get("max_week") or 0)
    if count < 1 or count > 20000 or max_week < 1 or max_week > 25:
        raise ValueError("The pool sheet does not contain valid entry and week evidence.")
    if max_week < before_week:
        raise ValueError(
            f"Week {max_week} pool sheets cannot replace the active Week {before_week} pool. Upload the newest official sheet."
        )
    if required_sha is not None and preview["sha256"] != required_sha:
        raise ValueError("The uploaded file changed since the preview.")


def describe(preview: dict) -> dict:
    meta = preview.get("meta") or {}
    return {
        "status": "PREVIEW_READY",
        "filename": preview["filename"],
        "sha256": preview["sha256"],
        "entry_count": preview["entry_count"],
        "pick_rows": preview["pick_rows"],
        "max_week": preview["max_week"],
        "current_week_required_picks": meta.get("current_week_required_picks"),
        "source_format": meta.get("format"),
        "duplicate_ticket_instances": preview.get("duplicate_ticket_instances", 0),
        "warnings": (meta.get("warnings") or [])[:5],
        "examples": [
            {
                "entry_name": entry["entry_name"],
                "pick_count": len(entry.get("picks") or []),
            }
            for entry in preview.get("entries", [])[:8]
        ],
    }


def process(payload: dict) -> dict:
    filename, filebytes = decode_pool_file(payload)
    preview = upload.parse_upload(filebytes, filename)
    week, fingerprint = current_state_version()
    if payload.get("action") == "preview":
        check_preview(preview, before_week=week)
        return {
            **describe(preview),
            "pool_week_before": week,
            "official_source_before_sha256": fingerprint,
        }
    if payload.get("action") != "confirm":
        raise ValueError("Choose preview or confirmed import.")
    expected = payload.get("expected_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError("Preview the pool sheet before importing.")
    check_preview(preview, before_week=week, required_sha=expected)
    if fingerprint != payload.get("official_source_before_sha256"):
        raise ValueError("The existing pool snapshot changed. Review the file again.")
    if week != payload.get("pool_week_before"):
        raise ValueError("The active pool week changed. Review the file again.")
    current_sha_file = upload.DERIVED / "LATEST_OFFICIAL_POOL.json"
    latest = json.loads(current_sha_file.read_text()) if current_sha_file.is_file() else {}
    if latest.get("source_sha256") == expected:
        return {
            "status": "ALREADY_IMPORTED",
            "entry_count": int(latest.get("parsed_entries") or preview["entry_count"]),
            "pool_week": week,
        }
    saved = upload.commit_preview(preview, filebytes)
    return {
        "status": "IMPORTED",
        "entry_count": saved["entries"],
        "weekly_pick_rows": saved["ledger_rows"],
        "pool_week": saved["pool_week"],
        "personal_entry_state_preserved": saved["personal_entry_state_preserved"],
    }


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read(7_500_000).decode())
        output = process(payload)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as error:
        output = {"status": "ERROR", "message": str(error)[:350]}
    except Exception:
        output = {"status": "ERROR", "message": "The pool file could not be processed safely."}
    sys.stdout.write(json.dumps(output, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
