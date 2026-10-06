#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import argparse
import csv
import fcntl
import gzip
import hashlib
import json
import os
import shutil
import tempfile

ROOT = Path("/home/ubuntu/sports-hulk")
WH = ROOT / "intelligence_warehouse"
CATALOG = WH / "catalog.json"
BLOBS = WH / "blobs"
MANIFESTS = WH / "manifests"
REGISTRY = WH / "registry"
LEDGER = REGISTRY / "SNAPSHOT_LEDGER.csv"
SNAPSHOTS = REGISTRY / "SNAPSHOT_RUNS.csv"
LOCK = WH / ".archive.lock"

LEDGER_FIELDS = [
    "snapshot_id","captured_at","sport","lane","logical_name",
    "source_path","source_mtime_utc","sha256","raw_bytes",
    "blob_bytes","blob_path","blob_created",
]
RUN_FIELDS = [
    "snapshot_id","captured_at","file_count","missing_count",
    "new_blob_count","raw_bytes","new_blob_bytes","manifest_path",
]

def utc_now():
    return datetime.now(timezone.utc)

def iso_mtime(ts: float):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()

def sha256(data: bytes):
    return hashlib.sha256(data).hexdigest()

def atomic_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name+".", dir=path.parent)
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_bytes(data)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def append_csv(path: Path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)

def archive_file(entry, captured_at):
    rel = entry["path"]
    path = ROOT / rel
    result = {
        "sport": entry["sport"],
        "lane": entry["lane"],
        "logical_name": path.name,
        "source_path": rel,
        "exists": path.exists(),
    }
    if not path.exists():
        return result, None

    data = path.read_bytes()
    digest = sha256(data)
    blob_rel = Path(digest[:2]) / f"{digest}.gz"
    blob = BLOBS / blob_rel
    created = False

    if not blob.exists():
        packed = gzip.compress(data, compresslevel=6, mtime=0)
        atomic_bytes(blob, packed)
        created = True

    # Verify immutable blob can reconstruct the exact original bytes.
    restored = gzip.decompress(blob.read_bytes())
    if sha256(restored) != digest:
        raise RuntimeError(f"Blob verification failed for {rel}")

    stat = path.stat()
    result.update({
        "source_mtime_utc": iso_mtime(stat.st_mtime),
        "sha256": digest,
        "raw_bytes": len(data),
        "blob_bytes": blob.stat().st_size,
        "blob_path": str(blob.relative_to(ROOT)),
        "blob_created": created,
    })
    return result, {
        "captured_at": captured_at,
        **{k: result[k] for k in [
            "sport","lane","logical_name","source_path","source_mtime_utc",
            "sha256","raw_bytes","blob_bytes","blob_path","blob_created"
        ]}
    }

def snapshot(sport=None):
    cfg = json.loads(CATALOG.read_text())
    entries = cfg["files"]
    if sport:
        sport = sport.upper()
        entries = [e for e in entries if e["sport"].upper() == sport]
        if not entries:
            raise SystemExit(f"No catalog entries for sport {sport}")

    now = utc_now()
    captured_at = now.isoformat()
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")

    files = []
    ledger_rows = []
    new_blobs = 0
    raw_bytes = 0
    new_blob_bytes = 0
    missing = 0

    for entry in entries:
        item, ledger = archive_file(entry, captured_at)
        files.append(item)
        if ledger is None:
            missing += 1
            continue
        ledger_rows.append(ledger)
        raw_bytes += int(item["raw_bytes"])
        if item["blob_created"]:
            new_blobs += 1
            new_blob_bytes += int(item["blob_bytes"])

    fingerprint = sha256(
        json.dumps(
            [(x.get("source_path"), x.get("sha256"), x.get("exists")) for x in files],
            separators=(",",":"), sort_keys=True
        ).encode()
    )[:12]
    scope = sport or "ALL"
    snapshot_id = f"{stamp}_{scope}_{fingerprint}"

    for row in ledger_rows:
        row["snapshot_id"] = snapshot_id

    manifest = {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "scope": scope,
        "catalog_version": cfg.get("version", 1),
        "file_count": len(ledger_rows),
        "missing_count": missing,
        "new_blob_count": new_blobs,
        "raw_bytes": raw_bytes,
        "new_blob_bytes": new_blob_bytes,
        "files": files,
    }
    manifest_path = MANIFESTS / f"{snapshot_id}.json"
    atomic_bytes(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True).encode()
    )

    append_csv(LEDGER, LEDGER_FIELDS, ledger_rows)
    append_csv(SNAPSHOTS, RUN_FIELDS, [{
        "snapshot_id": snapshot_id,
        "captured_at": captured_at,
        "file_count": len(ledger_rows),
        "missing_count": missing,
        "new_blob_count": new_blobs,
        "raw_bytes": raw_bytes,
        "new_blob_bytes": new_blob_bytes,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
    }])

    print("SNAPSHOT_ID:", snapshot_id)
    print("FILES:", len(ledger_rows))
    print("MISSING:", missing)
    print("NEW_BLOBS:", new_blobs)
    print("RAW_MB:", round(raw_bytes/1024/1024, 2))
    print("NEW_STORED_MB:", round(new_blob_bytes/1024/1024, 2))
    print("RESULT: INTELLIGENCE_SNAPSHOT_READY")
    return snapshot_id

def restore(snapshot_id, source_path, output):
    manifest = json.loads((MANIFESTS / f"{snapshot_id}.json").read_text())
    matches = [x for x in manifest["files"] if x.get("source_path") == source_path and x.get("exists")]
    if not matches:
        raise SystemExit("Source path not found in snapshot.")
    item = matches[0]
    blob = ROOT / item["blob_path"]
    data = gzip.decompress(blob.read_bytes())
    if sha256(data) != item["sha256"]:
        raise SystemExit("Restore verification failed.")
    out = Path(output)
    atomic_bytes(out, data)
    print("RESTORED:", source_path)
    print("TO:", out)
    print("SHA256:", item["sha256"])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport")
    ap.add_argument("--restore-snapshot")
    ap.add_argument("--restore-source")
    ap.add_argument("--output")
    args = ap.parse_args()

    WH.mkdir(parents=True, exist_ok=True)
    with LOCK.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.restore_snapshot:
            if not args.restore_source or not args.output:
                raise SystemExit("Restore requires --restore-source and --output.")
            restore(args.restore_snapshot, args.restore_source, args.output)
        else:
            snapshot(args.sport)

if __name__ == "__main__":
    main()
