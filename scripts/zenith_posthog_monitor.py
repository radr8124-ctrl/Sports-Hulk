#!/usr/bin/env python3
"""Read-only, strictly anonymous Sports Zenith Ask monitoring -> PostHog.

Never reads private roster/pick files, API request bodies, raw questions, or
browser identity. Only allowlisted derived metrics leave the server.
Designed as a separate oneshot observer: it does not alter live Ask routes.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path("/home/ubuntu/sports-hulk")
DEFAULT_TRACE = ROOT / "intelligence_warehouse/experiment_registry/ASK_TRACE_LEDGER.jsonl"
DEFAULT_STATE = Path("/home/ubuntu/.local/state/sports-zenith/posthog-cursor.json")
ALLOWED_HOSTS = {"https://us.i.posthog.com", "https://eu.i.posthog.com"}
DAILY_HARD_CAP = 50
RUN_HARD_CAP = 12

INTENTS = {
    "help", "live_score", "live_scores", "score_center", "score",
    "schedule", "team_stats", "player_history", "reporting", "reporting_stale",
    "reporting_conflict", "reporting_guardrail", "news", "game_news",
    "ref_market_research", "best_bet", "best_bets", "props", "prop",
    "survivor", "parlay", "waivers", "stash", "defense_stream", "dfs",
    "start_sit", "fantasy_context", "brain_record", "output_guardrail",
}
STATUSES = {
    "CURRENT", "RESEARCH_ONLY", "STALE_SOURCE", "SOURCE_CONFLICT",
    "INSUFFICIENT_EVIDENCE", "ERROR", "UNKNOWN", "NO_GAMES",
    "OUTPUT_VALIDATION_FAILED", "NEEDS_CONTEXT", "SOURCE_FAILURE",
    "DATA_SOURCE_FAILURE", "SOURCE_STALE", "NO_QUALIFIED_ARTICLES",
}


def _number(value, upper):
    # JSON bool is a subclass of int. Never allow fake numeric strings.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    if value != value or value in (float("inf"), float("-inf")):
        return 0
    return max(0, min(int(value), upper))


def build_event(row):
    """Allowlisted public operational metrics only; no trace or user identity."""
    if not isinstance(row, dict) or row.get("route_lane") != "GENERIC":
        return None

    intent = row.get("intent")
    status = row.get("status")
    safe_intent = intent if isinstance(intent, str) and intent in INTENTS else "OTHER"
    safe_status = status if isinstance(status, str) and status in STATUSES else "OTHER"
    # Stable retry deduplication; no raw source trace ID, question hash or URL.
    server_trace_id = str(row.get("trace_id") or "")
    insert_key = hashlib.sha256(
        ("zenith-ask-anonymous-receipt|" + server_trace_id).encode("utf-8")
    ).hexdigest()
    return {
        "event": "zenith_ask_review",
        "distinct_id": "zenith-anonymous-server",
        "properties": {
            "$process_person_profile": False,
            "$insert_id": insert_key,
            "component": "existing_ask_router",
            "scope": "public_generic",
            "intent_bucket": safe_intent,
            "status_bucket": safe_status,
            "output_valid": row.get("output_validation_valid") is True,
            "server_error": row.get("error") is True,
            "latency_ms": _number(row.get("latency_ms"), 60_000),
            "source_count": _number(row.get("source_count"), 20),
            "claim_source_count": _number(row.get("claim_source_count"), 30),
            "output_validation_error_count": _number(
                row.get("output_validation_error_count"), 20
            ),
        },
    }


def _utc(value):
    if not isinstance(value, str) or len(value) > 48:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _persist(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".next")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def process_new_records(
    ledger_path,
    state_path,
    send,
    *,
    now=None,
    daily_cap=DAILY_HARD_CAP,
):
    """Tail only *new* complete trace rows; fail closed on rotation or errors."""
    ledger_path, state_path = Path(ledger_path), Path(state_path)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now_requires_timezone")
    now = now.astimezone(timezone.utc)
    today = now.date().isoformat()
    cap = max(0, min(int(daily_cap), DAILY_HARD_CAP))
    result = {"status": "NO_NEW_EVENTS", "sent": 0, "private_skipped": 0}

    if not ledger_path.is_file():
        return {**result, "status": "LEDGER_MISSING"}
    stat = ledger_path.stat()

    if not state_path.exists():
        state = {
            "inode": stat.st_ino,
            "offset": stat.st_size,
            "day": today,
            "sent_today": 0,
            "sent_total": 0,
            "initialized_at": now.isoformat(),
        }
        _persist(state_path, state)
        return {**result, "status": "INITIALIZED"}

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        offset = int(state["offset"])
        inode = int(state["inode"])
        assert 0 <= offset
    except (ValueError, KeyError, TypeError, AssertionError, json.JSONDecodeError):
        # Never replay a whole ledger after a corrupted local cursor.
        return {**result, "status": "BAD_CURSOR"}

    if inode != stat.st_ino or stat.st_size < offset:
        state.update({"inode": stat.st_ino, "offset": stat.st_size})
        _persist(state_path, state)
        return {**result, "status": "SOURCE_ROTATED"}

    if state.get("day") != today:
        state["day"] = today
        state["sent_today"] = 0

    sent_today = _number(state.get("sent_today"), DAILY_HARD_CAP)
    run_count = 0
    with ledger_path.open("rb") as source:
        source.seek(offset)
        while True:
            start = source.tell()
            line = source.readline()
            if not line:
                break
            if not line.endswith(b"\n"):
                source.seek(start)
                break  # wait for completed JSONL record
            next_offset = source.tell()

            if sent_today >= cap:
                # Drop the backlog; don't transmit it after tomorrow's cap reset.
                state["offset"] = stat.st_size
                result["status"] = "DAILY_LIMIT"
                break
            if run_count >= RUN_HARD_CAP:
                break
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                state["offset"] = next_offset
                continue

            event = build_event(row)
            state["offset"] = next_offset
            if event is None:
                result["private_skipped"] += 1
                continue

            as_of = _utc(row.get("recorded_at"))
            if as_of is None or now - as_of > timedelta(hours=36) or as_of - now > timedelta(minutes=5):
                continue

            # Ack-gated cursor: failed network never discards an unsent event.
            try:
                success = send(event) is True
            except Exception:
                success = False
            if not success:
                state["offset"] = start
                result["status"] = "SEND_FAILED"
                break
            run_count += 1
            sent_today += 1
            state["sent_today"] = sent_today
            state["sent_total"] = _number(state.get("sent_total"), 1_000_000) + 1
            state["last_delivery_at"] = now.isoformat()
            result["sent"] += 1
            result["status"] = "SENT"
            _persist(state_path, state)  # survives process crashes; dedupe insert IDs
    _persist(state_path, state)
    return result


def _capture_sender(token, host):
    if not isinstance(token, str) or not token.startswith("phc_") or len(token) > 150:
        raise ValueError("invalid_project_token")
    if host not in ALLOWED_HOSTS:
        raise ValueError("unapproved_ingest_host")

    def send(payload):
        if payload.get("event") != "zenith_ask_review":
            return False
        body = json.dumps({"api_key": token, **payload}, separators=(",", ":")).encode("utf-8")
        req = Request(
            host + "/i/v0/e/",
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "SportsZenithAnonymousObserver/1"},
            method="POST",
        )
        with urlopen(req, timeout=4) as response:
            return 200 <= response.status < 300

    return send


def main():
    # Monitoring is opt-in and OFF by default. No browser SDK or session replay.
    if os.environ.get("ZENITH_POSTHOG_ENABLED") != "1":
        print('{"status":"DISABLED"}')
        return 0
    token = os.environ.get("ZENITH_POSTHOG_TOKEN", "")
    host = os.environ.get("ZENITH_POSTHOG_HOST", "")
    try:
        send = _capture_sender(token, host)
    except ValueError:
        print('{"status":"UNCONFIGURED"}')
        return 0

    state_path = Path(os.environ.get("ZENITH_POSTHOG_STATE_PATH", str(DEFAULT_STATE)))
    ledger_path = Path(os.environ.get("ZENITH_POSTHOG_LEDGER_PATH", str(DEFAULT_TRACE)))
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = state_path.with_suffix(".lock")
    with lock_path.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('{"status":"ALREADY_RUNNING"}')
            return 0
        response = process_new_records(ledger_path, state_path, send)
    # Whitelisted status and numbers only; don't log inputs or connection errors.
    print(json.dumps(response, sort_keys=True))
    return 1 if response["status"] in {"SEND_FAILED", "BAD_CURSOR"} else 0


if __name__ == "__main__":
    sys.exit(main())
