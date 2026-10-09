"""Memory-bounded, resumable CFB historical recommendation index.

The entire original append-only CSV remains authoritative and unmodified.
This index records every processed source row as a streaming cursor and keeps
one latest record per recommendation_key for grading. No auto-bets/promotion.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "cfb_live/decision/history/CFB_RECOMMENDATION_LEDGER.csv"
INDEX = ROOT / "cfb_live/decision/history/CFB_RECOMMENDATION_LATEST_INDEX.sqlite3"
HEADER = [
    "snapshot_at", "bundle_hash", "lane", "recommendation_key", "source_file",
    "game_key", "schedule_event_id", "market", "selection", "line", "decision",
    "score", "context_stage", "payload_json",
]
BOUNDARY = 16384
PREFIX = 65536
SCHEMA_VERSION = "CFB_APPEND_ONLY_RAW_HISTORY_LATEST_INDEX_V1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(f, cursor: int) -> str:
    a = max(0, cursor - BOUNDARY)
    f.seek(a)
    return digest(f.read(cursor - a))


def header_and_identity(f, st: os.stat_result, *, prefix_len: int) -> dict:
    f.seek(0)
    first = f.readline()
    columns = next(csv.reader([first.decode("utf-8")], strict=True))
    if columns != HEADER:
        raise ValueError("CFB_SOURCE_SCHEMA_CHANGED")
    f.seek(0)
    return {
        "source_device": str(st.st_dev),
        "source_inode": str(st.st_ino),
        "first_64k_sha256": digest(f.read(prefix_len)),
        "source_prefix_bytes_hashed": str(prefix_len),
        "first_row_end": str(len(first)),
        "columns": json.dumps(columns, separators=(",", ":")),
    }


def connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path,timeout=5)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA cache_size=-32768")
    con.execute("CREATE TABLE IF NOT EXISTS info (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    con.execute("""CREATE TABLE IF NOT EXISTS latest (
        recommendation_key TEXT PRIMARY KEY, snapshot_at TEXT NOT NULL,
        source_row_sequence INTEGER NOT NULL, serialized_row TEXT NOT NULL
    )""")
    return con


def metadata(con: sqlite3.Connection) -> dict[str,str]:
    return dict(con.execute("SELECT key,value FROM info"))


def setmeta(con: sqlite3.Connection, values: dict[str,str]) -> None:
    con.executemany(
        "INSERT INTO info(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        values.items(),
    )


def prepare(con: sqlite3.Connection, f, st: os.stat_result) -> dict[str,str]:
    m=metadata(con)
    prefix_len=int(m['source_prefix_bytes_hashed']) if m else min(PREFIX,st.st_size)
    initial=header_and_identity(f,st,prefix_len=prefix_len)
    if not m:
        cursor=int(initial["first_row_end"])
        m={
            "schema":SCHEMA_VERSION,**initial,
            "cursor_bytes":str(cursor),"processed_raw_rows":"0",
            "last_boundary_sha256":fingerprint(f,cursor),
        }
        with con:
            setmeta(con,m)
    else:
        if m.get("schema")!=SCHEMA_VERSION:
            raise ValueError("CFB_INDEX_UNKNOWN_VERSION")
        if any(m.get(k)!=v for k,v in initial.items()):
            raise ValueError("CFB_SOURCE_REPLACED_OR_SCHEMA_PREFIX_CHANGED")
        cursor=int(m["cursor_bytes"])
        if cursor < int(initial["first_row_end"]) or cursor > st.st_size:
            raise ValueError("CFB_SOURCE_LEDGER_WAS_TRUNCATED")
        if m["last_boundary_sha256"]!=fingerprint(f,cursor):
            raise ValueError("CFB_SOURCE_PRIOR_INDEXED_BYTES_CHANGED")
    return m


def apply_batch(con: sqlite3.Connection, rows: list[tuple], *,cursor:int, processed:int, boundary:str):
    if not rows: return
    with con:
        con.executemany("""
        INSERT INTO latest(recommendation_key,snapshot_at,source_row_sequence,serialized_row)
        VALUES(?,?,?,?)
        ON CONFLICT(recommendation_key) DO UPDATE SET
            snapshot_at=excluded.snapshot_at,
            source_row_sequence=excluded.source_row_sequence,
            serialized_row=excluded.serialized_row
        WHERE excluded.snapshot_at >= latest.snapshot_at
        """,rows)
        setmeta(con,{
            "cursor_bytes":str(cursor),
            "processed_raw_rows":str(processed),
            "last_boundary_sha256":boundary,
        })


def parse_line(raw: bytes) -> dict:
    if not raw.endswith(b"\n"):
        raise ValueError("CFB_PARTIAL_SOURCE_ROW")
    if len(raw)>2_000_000:
        raise ValueError("CFB_SOURCE_ROW_TOO_LARGE")
    fields=next(csv.reader([raw.decode("utf-8")],strict=True))
    if len(fields)!=len(HEADER):
        raise ValueError("CFB_CORRUPTED_OR_MULTILINE_CSV_ROW")
    entry=dict(zip(HEADER,fields))
    key=entry["recommendation_key"]
    if len(key)!=64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("CFB_INVALID_RECOMMENDATION_KEY")
    at=entry["snapshot_at"]
    if len(at)<25 or not at.endswith("+00:00") or at[4:5]!="-" or at[10:11]!="T":
        raise ValueError("CFB_INVALID_OR_AMBIGUOUS_ORIGINAL_TIMESTAMP")
    if entry["lane"] not in ("GAME","PARLAY"):
        raise ValueError("CFB_UNKNOWN_RECOMMENDATION_LANE")
    if not entry["payload_json"]:
        raise ValueError("CFB_EMPTY_SOURCE_RECOMMENDATION")
    return entry


def scan(*,source:Path=LEDGER,index:Path=INDEX,max_bytes:int=128*1024*1024,batch_size:int=1500)->dict:
    """Scan up to a byte cap; persist cursor + latest rows as ONE transaction per batch."""
    if max_bytes<1 or batch_size<1 or batch_size>10000:
        raise ValueError("Invalid bounded scan")
    if not source.is_file():
        raise ValueError("Original append-only source missing")
    lockfile=index.with_suffix(index.suffix+".lock")
    lockfile.parent.mkdir(parents=True, exist_ok=True)
    with lockfile.open("a+b") as locked:
        try: fcntl.flock(locked,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: raise RuntimeError("CFB_INDEX_ALREADY_PROCESSING") from exc
        with source.open("rb") as f:
            st=os.fstat(f.fileno())
            with connection(index) as con:
                m=prepare(con,f,st)
                begin=int(m["cursor_bytes"])
                until=min(st.st_size,begin+max_bytes)
                processed=int(m["processed_raw_rows"])
                rows=[]
                f.seek(begin)
                cursor=begin
                while cursor < until:
                    location=f.tell()
                    raw=f.readline()
                    if not raw:break
                    if not raw.endswith(b"\n"):
                        f.seek(location)
                        break  # Writer may be appending; do NOT index incomplete row.
                    entry=parse_line(raw)
                    processed+=1
                    cursor=f.tell()
                    rows.append((
                        entry["recommendation_key"],entry["snapshot_at"],processed,
                        json.dumps(entry,ensure_ascii=False,separators=(",",":")),
                    ))
                    if len(rows)>=batch_size:
                        apply_batch(con,rows,cursor=cursor,processed=processed,boundary=fingerprint(f,cursor))
                        rows.clear()
                        f.seek(cursor)
                if rows:
                    apply_batch(con,rows,cursor=cursor,processed=processed,boundary=fingerprint(f,cursor))
                    f.seek(cursor)
                after=os.stat(source)
                if after.st_dev!=st.st_dev or after.st_ino!=st.st_ino or after.st_size<cursor:
                    raise ValueError("CFB_SOURCE_CHANGED_DURING_INDEX_PASS")
                unique=int(con.execute("SELECT count(*) FROM latest").fetchone()[0])
                complete=(cursor==after.st_size)
                return {
                    "status":"INDEX_CAUGHT_UP_TO_VERIFIED_SOURCE_END" if complete else "BUILDING_INDEX_FROM_ALL_ORIGINAL_ROWS",
                    "source":str(source),"index":str(index),
                    "source_size_bytes_at_start":st.st_size,
                    "source_size_bytes_now":after.st_size,
                    "cursor_bytes":cursor,
                    "new_bytes_indexed":cursor-begin,
                    "total_processed_raw_rows":processed,
                    "unique_recommendations_indexed":unique,
                    "full_raw_ledger_scanned":complete,
                    "original_source_csv_rewritten":False,
                    "wagers_or_betting_models_changed":False,
                }


def read_latest_complete(*,source:Path=LEDGER,index:Path=INDEX):
    """Return (DataFrame, raw_row_count), or refuse incomplete/stale index."""
    import pandas as pd
    if not source.is_file() or not index.is_file():
        raise ValueError("CFB_COMPLETE_SOURCE_INDEX_MISSING")
    with source.open("rb") as f, connection(index) as con:
        st=os.fstat(f.fileno())
        m=prepare(con,f,st)
        if int(m["cursor_bytes"])!=st.st_size:
            raise ValueError("CFB_SOURCE_INDEX_NOT_FULLY_CAUGHT_UP")
        records=[json.loads(r[0]) for r in con.execute(
            "SELECT serialized_row FROM latest ORDER BY source_row_sequence"
        )]
        if not records:
            return pd.DataFrame(columns=HEADER),int(m["processed_raw_rows"])
        # Parse using the same pandas CSV dtype inference as the legacy grader.
        buf=io.StringIO()
        writer=csv.DictWriter(buf,fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(records)
        buf.seek(0)
        frame=pd.read_csv(buf,low_memory=False)
        if frame.recommendation_key.duplicated().any():
            raise ValueError("CFB_INDEX_CONTAINS_DUPLICATE_LATEST_KEYS")
        return frame,int(m["processed_raw_rows"])


def main():
    parser=argparse.ArgumentParser(description="Resumable memory-bounded CFB source index; NEVER delete original ledger")
    parser.add_argument("--max-megabytes",type=int,default=128)
    args=parser.parse_args()
    if not 1<=args.max_megabytes<=8192:
        raise SystemExit("max-megabytes must be 1..8192")
    result=scan(max_bytes=args.max_megabytes*1024*1024)
    print("CFB_RESUMABLE_HISTORICAL_LEDGER_INDEX",json.dumps(result,sort_keys=True))
    if not result["full_raw_ledger_scanned"]:
        raise SystemExit(85)  # Source still indexed progressively; do not grade yet.


if __name__=="__main__":
    main()
