"""Append-only experiment registry for Sports HULK research.

Every threshold/model/feature experiment gets an identity before evaluation.
Rejected and failed experiments remain in the ledger so research history cannot
silently forget unsuccessful trials.
"""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
import json


SCHEMA_VERSION = 1


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def experiment_id(spec: dict[str, Any]) -> str:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "sport": spec.get("sport"),
        "lane": spec.get("lane"),
        "market": spec.get("market"),
        "features": spec.get("features") or [],
        "calibration": spec.get("calibration"),
        "thresholds": spec.get("thresholds") or {},
        "training_window": spec.get("training_window"),
        "validation_window": spec.get("validation_window"),
        "cluster_key": spec.get("cluster_key"),
        "notes": spec.get("notes"),
    }
    return "EXP-" + sha256(canonical_json(payload).encode("utf-8")).hexdigest()[:16].upper()


def append_event(path: str | Path, event: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json(event) + "\n")


def register_experiment(path: str | Path, spec: dict[str, Any]) -> str:
    exp_id = experiment_id(spec)
    append_event(path, {
        "event_type": "REGISTERED",
        "schema_version": SCHEMA_VERSION,
        "experiment_id": exp_id,
        "recorded_at": utc_now_iso(),
        "spec": spec,
    })
    return exp_id


def record_result(
    path: str | Path,
    exp_id: str,
    *,
    status: str,
    metrics: dict[str, Any],
    decision: str,
    reason: str,
    forward_only: bool = False,
) -> None:
    append_event(path, {
        "event_type": "RESULT",
        "schema_version": SCHEMA_VERSION,
        "experiment_id": exp_id,
        "recorded_at": utc_now_iso(),
        "status": status,
        "metrics": metrics,
        "decision": decision,
        "reason": reason,
        "forward_only": bool(forward_only),
    })


def read_events(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def summarize(path: str | Path) -> dict[str, Any]:
    events = read_events(path)
    registered: dict[str, dict[str, Any]] = {}
    results: dict[str, list[dict[str, Any]]] = {}

    for event in events:
        exp_id = event.get("experiment_id")
        if not exp_id:
            continue
        if event.get("event_type") == "REGISTERED":
            registered.setdefault(exp_id, event)
        elif event.get("event_type") == "RESULT":
            results.setdefault(exp_id, []).append(event)

    decisions: dict[str, int] = {}
    unresolved = 0
    for exp_id in registered:
        exp_results = results.get(exp_id, [])
        if not exp_results:
            unresolved += 1
            continue
        latest = exp_results[-1]
        decision = str(latest.get("decision") or "UNKNOWN")
        decisions[decision] = decisions.get(decision, 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "registered_experiments": len(registered),
        "experiments_with_results": sum(bool(results.get(exp_id)) for exp_id in registered),
        "unresolved_experiments": unresolved,
        "decision_counts": decisions,
        "total_events": len(events),
    }
