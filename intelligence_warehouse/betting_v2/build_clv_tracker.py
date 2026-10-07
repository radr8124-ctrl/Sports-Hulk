#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

try:
    from .competition_regime import (
        normalize_competition_regime,
        proof_lane_key as regime_proof_lane_key,
        proof_version as regime_proof_version,
        regime_enforced,
    )
except ImportError:
    from competition_regime import (
        normalize_competition_regime,
        proof_lane_key as regime_proof_lane_key,
        proof_version as regime_proof_version,
        regime_enforced,
    )

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "intelligence_warehouse" / "betting_v2"
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

CURRENT = OUT_DIR / "BETTING_V2_CURRENT.json"
REGIME_SOURCE = OUT_DIR / "BETTING_V2_ALL_MARKETS_CURRENT.json"
PRICE_LEDGER = OUT_DIR / "BETTING_V2_PRICE_TIMELINE.jsonl"
PICK_LEDGER = OUT_DIR / "BETTING_V2_PICK_LEDGER.jsonl"
OUT = OUT_DIR / "BETTING_V2_CLV.json"
PUBLIC_OUT = PUBLIC / "betting_v2_clv.json"
DIST_OUT = DIST / "betting_v2_clv.json"


def now():
    return datetime.now(timezone.utc)


def now_iso():
    return now().isoformat()


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if fallback is None else fallback


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def parse_dt(value):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        try:
            # Some feeds use a space separator and explicit offset.
            dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S%z")
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def num(value):
    try:
        x = float(value)
        return None if math.isnan(x) else x
    except Exception:
        return None


def american_implied(odds):
    odds = num(odds)
    if odds is None or odds == 0:
        return None
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def decimal_odds(american):
    american = num(american)
    if american is None or american == 0:
        return None
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def clean(value):
    return str(value or "").strip()


def row_key(row):
    side = clean(row.get("side")).upper()
    selection = clean(row.get("selection")).upper()
    side_or_selection = side if side in {"HOME", "AWAY"} else selection
    return "|".join([
        clean(row.get("sport")).upper(),
        clean(row.get("game_key")),
        side_or_selection,
    ])


def regime_metadata(row, model_version=None):
    sport = clean(row.get("sport")).upper()
    regime = normalize_competition_regime(
        row.get("competition_regime"),
        sport,
    )
    proof_key = clean(
        row.get("proof_lane_key")
        or regime_proof_lane_key(sport, "MONEYLINE", regime)
    )
    version = clean(
        row.get("proof_version")
        or regime_proof_version(
            model_version or row.get("model_version"),
            sport,
            regime,
        )
    )
    return {
        "competition_regime": regime,
        "proof_lane_key": proof_key,
        "proof_version": version,
    }


def regime_source_lookup():
    payload = read_json(REGIME_SOURCE, {})
    model_version = payload.get("model_version")
    lookup = {}
    conflicts = set()

    for row in payload.get("picks") or []:
        sport = clean(row.get("sport")).upper()
        game_key = clean(row.get("game_key"))
        market = clean(row.get("market")).upper()
        if not sport or not game_key:
            continue
        if market and market != "MONEYLINE":
            continue
        key = (sport, game_key)
        metadata = regime_metadata(row, model_version)
        prior = lookup.get(key)
        if prior is not None and prior != metadata:
            conflicts.add(key)
        else:
            lookup[key] = metadata

    for sport, game_key in conflicts:
        lookup[(sport, game_key)] = regime_metadata(
            {
                "sport": sport,
                "competition_regime": "UNKNOWN",
            },
            model_version,
        )
    return lookup


def resolved_regime_metadata(row, model_version=None, lookup=None):
    explicit = (
        "competition_regime" in row
        or bool(clean(row.get("proof_lane_key")))
        or bool(clean(row.get("proof_version")))
    )
    if explicit:
        return regime_metadata(row, model_version)

    source = regime_source_lookup() if lookup is None else lookup
    key = (
        clean(row.get("sport")).upper(),
        clean(row.get("game_key")),
    )
    if key in source:
        return dict(source[key])
    return regime_metadata(row, model_version)


def regime_clv_key(row):
    sport = clean(row.get("sport")).upper()
    regime_aware = (
        regime_enforced(sport)
        and (
            "competition_regime" in row
            or bool(clean(row.get("proof_version")))
            or bool(clean(row.get("proof_lane_key")))
        )
    )
    if not regime_aware:
        return row_key(row)
    metadata = regime_metadata(row)
    return "|".join([
        metadata["proof_version"],
        metadata["competition_regime"],
        row_key(row),
    ])


def pick_key(row):
    return regime_clv_key(row)


def snapshot_market_board(payload):
    captured_at = now_iso()
    regime_lookup = regime_source_lookup()
    existing = read_jsonl(PRICE_LEDGER)
    latest_signature = {}
    for row in existing:
        key = row.get("market_key")
        if key:
            latest_signature[key] = (
                row.get("american_odds"),
                row.get("market_fair_probability_pct"),
                row.get("book_count"),
            )

    added = 0
    for row in payload.get("market_board") or []:
        metadata = resolved_regime_metadata(
            row,
            payload.get("model_version"),
            regime_lookup,
        )
        resolved_row = {**row, **metadata}
        start = parse_dt(row.get("event_start"))
        if start is not None and now() >= start:
            # Never record an in-play price as pregame market history.
            continue

        market_key = regime_clv_key(resolved_row)
        if not market_key:
            continue

        signature = (
            num(row.get("american_odds")),
            num(row.get("market_fair_probability_pct")),
            int(num(row.get("book_count")) or 0),
        )
        if latest_signature.get(market_key) == signature:
            continue

        implied = american_implied(row.get("american_odds"))
        event = {
            "event_type": "MARKET_PRICE",
            "captured_at": captured_at,
            "market_key": market_key,
            "sport": clean(row.get("sport")).upper(),
            **metadata,
            "game_key": clean(row.get("game_key")),
            "selection": clean(row.get("selection")),
            "side": clean(row.get("side")).upper() or None,
            "event_start": row.get("event_start"),
            "american_odds": num(row.get("american_odds")),
            "raw_implied_probability_pct": (
                None if implied is None else round(100 * implied, 4)
            ),
            "market_fair_probability_pct": num(
                row.get("market_fair_probability_pct")
            ),
            "book_count": int(num(row.get("book_count")) or 0),
        }
        append_jsonl(PRICE_LEDGER, event)
        latest_signature[market_key] = signature
        added += 1
    return added


def capture_v2_picks(payload):
    regime_lookup = regime_source_lookup()
    existing = {}
    for row in read_jsonl(PICK_LEDGER):
        key = row.get("pick_key")
        if key and row.get("event_type") == "ENTRY":
            existing[key] = row

    added = 0
    for row in payload.get("picks") or []:
        metadata = resolved_regime_metadata(
            row,
            payload.get("model_version"),
            regime_lookup,
        )
        resolved_row = {**row, **metadata}
        key = pick_key(resolved_row)
        if not key or key in existing:
            continue

        start = parse_dt(row.get("event_start"))
        if start is not None and now() >= start:
            continue

        implied = american_implied(row.get("american_odds"))
        event = {
            "event_type": "ENTRY",
            "pick_key": key,
            "entry_at": now_iso(),
            "sport": clean(row.get("sport")).upper(),
            **metadata,
            "game_key": clean(row.get("game_key")),
            "selection": clean(row.get("selection")),
            "side": clean(row.get("side")).upper() or None,
            "event_start": row.get("event_start"),
            "entry_american_odds": num(row.get("american_odds")),
            "entry_raw_implied_probability_pct": (
                None if implied is None else round(100 * implied, 4)
            ),
            "entry_market_fair_probability_pct": num(
                row.get("market_fair_probability_pct")
            ),
            "entry_market_reference_probability_pct": num(
                row.get("market_reference_probability_pct")
            ),
            "entry_market_reference_type": row.get("market_reference_type"),
            "entry_devig_paired_books": int(
                num(row.get("devig_paired_books")) or 0
            ),
            "entry_hulk_evidence_score": num(row.get("hulk_evidence_score")),
            "entry_v2_probability_pct": num(
                row.get("calibrated_win_probability_pct")
            ),
            "entry_expected_value_pct": num(row.get("expected_value_pct")),
            "entry_conservative_ev_pct": num(
                row.get("conservative_expected_value_pct")
            ),
            "entry_data_quality_grade": row.get("data_quality_grade"),
            "entry_v2_shadow_decision": row.get("shadow_decision"),
            "probability_source": row.get("probability_source"),
            "model_version": payload.get("model_version"),
            "historical_edge_confidence": row.get(
                "historical_edge_confidence"
            ),
            "selection_rule_status": row.get("selection_rule_status"),
            "book_count": int(num(row.get("book_count")) or 0),
            "status": "OPEN",
        }
        append_jsonl(PICK_LEDGER, event)
        existing[key] = event
        added += 1
    return added


def canonical_entries():
    entries = {}
    for row in read_jsonl(PICK_LEDGER):
        key = row.get("pick_key")
        if not key:
            continue
        if row.get("event_type") == "ENTRY":
            entries.setdefault(key, {}).update(row)
        elif row.get("event_type") == "CLOSE":
            entries.setdefault(key, {}).update(row)
    return entries


def price_history():
    history = {}
    for row in read_jsonl(PRICE_LEDGER):
        key = row.get("market_key")
        if not key:
            continue
        history.setdefault(key, []).append(row)
    for rows in history.values():
        rows.sort(key=lambda x: x.get("captured_at") or "")
    return history


def finalize_closes():
    entries = canonical_entries()
    prices = price_history()
    closed_now = 0

    for key, entry in entries.items():
        if entry.get("status") == "CLOSED":
            continue

        start = parse_dt(entry.get("event_start"))
        if start is None or now() < start:
            continue

        candidates = []
        for row in prices.get(key, []):
            captured = parse_dt(row.get("captured_at"))
            if captured is None or captured > start:
                continue
            candidates.append(row)

        if candidates:
            close = candidates[-1]
            close_source = "LAST_PRESTART_MARKET_SNAPSHOT"
        else:
            # If we never received a later quote, the entry price is the only
            # valid pregame price we can defend.
            close = {
                "captured_at": entry.get("entry_at"),
                "american_odds": entry.get("entry_american_odds"),
                "raw_implied_probability_pct": entry.get(
                    "entry_raw_implied_probability_pct"
                ),
                "market_fair_probability_pct": entry.get(
                    "entry_market_fair_probability_pct"
                ),
                "book_count": entry.get("book_count"),
            }
            close_source = "ENTRY_PRICE_FALLBACK"

        entry_raw = num(entry.get("entry_raw_implied_probability_pct"))
        close_raw = num(close.get("raw_implied_probability_pct"))
        entry_fair = num(entry.get("entry_market_fair_probability_pct"))
        close_fair = num(close.get("market_fair_probability_pct"))

        raw_clv = (
            None if entry_raw is None or close_raw is None
            else round(close_raw - entry_raw, 4)
        )
        fair_clv = (
            None if entry_fair is None or close_fair is None
            else round(close_fair - entry_fair, 4)
        )

        entry_dec = decimal_odds(entry.get("entry_american_odds"))
        close_fair_decimal_ev = None
        if entry_dec is not None and close_fair is not None:
            close_fair_decimal_ev = round(
                100 * ((entry_dec * (close_fair / 100.0)) - 1.0), 4
            )

        preferred_clv = fair_clv if fair_clv is not None else raw_clv
        if preferred_clv is None:
            direction = "UNKNOWN"
        elif preferred_clv > 0.05:
            direction = "BEAT_CLOSE"
        elif preferred_clv < -0.05:
            direction = "LOST_TO_CLOSE"
        else:
            direction = "FLAT"

        regime_aware = any(
            field in entry
            for field in (
                "competition_regime",
                "proof_lane_key",
                "proof_version",
            )
        )
        event = {
            "event_type": "CLOSE",
            "pick_key": key,
            **(
                {
                    "competition_regime": entry.get("competition_regime"),
                    "proof_lane_key": entry.get("proof_lane_key"),
                    "proof_version": entry.get("proof_version"),
                }
                if regime_aware else {}
            ),
            "status": "CLOSED",
            "closed_at": now_iso(),
            "closing_quote_at": close.get("captured_at"),
            "close_source": close_source,
            "closing_american_odds": num(close.get("american_odds")),
            "closing_raw_implied_probability_pct": close_raw,
            "closing_market_fair_probability_pct": close_fair,
            "closing_book_count": int(num(close.get("book_count")) or 0),
            "raw_clv_probability_pp": raw_clv,
            "fair_clv_probability_pp": fair_clv,
            "clv_ev_pct_at_entry_price": close_fair_decimal_ev,
            "clv_direction": direction,
        }
        append_jsonl(PICK_LEDGER, event)
        closed_now += 1

    return closed_now


def mean(values):
    vals = [float(v) for v in values if v is not None]
    return None if not vals else round(sum(vals) / len(vals), 4)


def summarize_group(rows):
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    preferred = [
        num(r.get("fair_clv_probability_pp"))
        if num(r.get("fair_clv_probability_pp")) is not None
        else num(r.get("raw_clv_probability_pp"))
        for r in closed
    ]
    preferred = [v for v in preferred if v is not None]

    return {
        "tracked": len(rows),
        "open": sum(r.get("status") != "CLOSED" for r in rows),
        "closed": len(closed),
        "beat_close": sum(r.get("clv_direction") == "BEAT_CLOSE" for r in closed),
        "lost_to_close": sum(
            r.get("clv_direction") == "LOST_TO_CLOSE" for r in closed
        ),
        "flat": sum(r.get("clv_direction") == "FLAT" for r in closed),
        "positive_clv_rate_pct": (
            None if not closed
            else round(
                100
                * sum(r.get("clv_direction") == "BEAT_CLOSE" for r in closed)
                / len(closed),
                1,
            )
        ),
        "avg_preferred_clv_probability_pp": mean(preferred),
        "avg_fair_clv_probability_pp": mean(
            [num(r.get("fair_clv_probability_pp")) for r in closed]
        ),
        "avg_entry_price_clv_ev_pct": mean(
            [num(r.get("clv_ev_pct_at_entry_price")) for r in closed]
        ),
    }


def build_output():
    entries = list(canonical_entries().values())
    by_sport = {}
    by_v2_decision = {}
    by_regime = {}
    by_proof_lane = {}

    for sport in sorted({r.get("sport") for r in entries if r.get("sport")}):
        by_sport[sport] = summarize_group(
            [r for r in entries if r.get("sport") == sport]
        )

    for decision in sorted(
        {r.get("entry_v2_shadow_decision") for r in entries
         if r.get("entry_v2_shadow_decision")}
    ):
        by_v2_decision[decision] = summarize_group(
            [r for r in entries if r.get("entry_v2_shadow_decision") == decision]
        )

    regime_groups = {}
    proof_groups = {}
    for row in entries:
        sport = clean(row.get("sport")).upper()
        regime = normalize_competition_regime(
            row.get("competition_regime"),
            sport,
        )
        proof_key = clean(row.get("proof_lane_key"))
        if not proof_key:
            proof_key = regime_proof_lane_key(
                sport,
                "MONEYLINE",
                regime,
            )
        regime_groups.setdefault(regime, []).append(row)
        proof_groups.setdefault(proof_key, []).append(row)

    for regime in sorted(regime_groups):
        by_regime[regime] = summarize_group(regime_groups[regime])

    for proof_key in sorted(proof_groups):
        by_proof_lane[proof_key] = summarize_group(proof_groups[proof_key])

    payload = {
        "generated_at": now_iso(),
        "status": "READY",
        "method": "FIRST_V2_ENTRY_TO_LAST_VALID_PRESTART_MARKET_PRICE",
        "summary": summarize_group(entries),
        "by_sport": by_sport,
        "by_v2_decision": by_v2_decision,
        "by_regime": by_regime,
        "by_proof_lane": by_proof_lane,
        "open_picks": [
            r for r in entries if r.get("status") != "CLOSED"
        ][:50],
        "recent_closed": sorted(
            [r for r in entries if r.get("status") == "CLOSED"],
            key=lambda x: x.get("closed_at") or "",
            reverse=True,
        )[:50],
        "definitions": {
            "positive_clv": (
                "Closing implied/fair probability moved toward the selected side "
                "after V2 first tracked it."
            ),
            "fair_clv_probability_pp": (
                "Closing no-vig fair probability minus entry no-vig fair probability."
            ),
            "raw_clv_probability_pp": (
                "Closing raw implied probability minus entry raw implied probability."
            ),
            "clv_ev_pct_at_entry_price": (
                "Expected value of the entry price using the closing no-vig fair "
                "probability; positive means the entry price beat the close."
            ),
        },
    }
    return payload


def write_outputs(payload):
    rendered = json.dumps(payload, indent=2)
    OUT.write_text(rendered)
    PUBLIC_OUT.write_text(rendered)
    if DIST.exists():
        DIST_OUT.write_text(rendered)


def main():
    payload = read_json(CURRENT, {})
    if payload.get("status") != "READY":
        raise SystemExit("BETTING_V2_CURRENT.json is not ready.")

    price_added = snapshot_market_board(payload)
    picks_added = capture_v2_picks(payload)
    closed_now = finalize_closes()
    output = build_output()
    output["last_run"] = {
        "market_snapshots_added": price_added,
        "pick_entries_added": picks_added,
        "closed_now": closed_now,
    }
    write_outputs(output)

    print(json.dumps({
        "status": output["status"],
        "last_run": output["last_run"],
        "summary": output["summary"],
        "sports": output["by_sport"],
    }, indent=2))


if __name__ == "__main__":
    main()
