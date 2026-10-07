#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from premium_ui.dfs_optimizer import (
    optimize_nfl,
    lineup_frame,
    prepare_pool,
)

MODE_TO_STRATEGY = {
    "BEST_OVERALL": "Balanced",
    "CASH_SAFE": "Cash Safe",
    "TOURNAMENT_UPSIDE": "GPP",
    "CONTRARIAN": "Contrarian",
}


def load_rows():
    candidates = [
        ROOT / "commercial_web" / "dist" / "ask_context.json",
        ROOT / "commercial_web" / "public" / "ask_context.json",
    ]
    for path in candidates:
        if path.exists():
            payload = json.loads(path.read_text())
            return payload.get("datasets", {}).get("dfs", []), payload.get("generated_at")
    return [], None


def clean_value(value):
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value



def _numeric_present(frame, column):
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce").notna()


def verified_ownership_mask(frame):
    mask = pd.Series(False, index=frame.index)

    if "verified_ownership_pct" in frame.columns:
        mask = mask | _numeric_present(frame, "verified_ownership_pct")

    if "projected_ownership_pct" in frame.columns:
        projected = pd.to_numeric(frame["projected_ownership_pct"], errors="coerce")
        if "projected_ownership_source" in frame.columns:
            source = frame["projected_ownership_source"].fillna("").astype(str).str.upper()
            verified_source = (
                source.str.strip().ne("")
                & ~source.str.contains("HEURISTIC|MODELLED|MODELED|SHARKSNIP", regex=True)
            )
            mask = mask | (projected.notna() & verified_source)

    if "ownership_is_verified" in frame.columns:
        verified_flag = frame["ownership_is_verified"].astype(str).str.lower().isin({"true", "1", "yes"})
        projected = pd.to_numeric(
            frame.get("projected_ownership_pct", pd.Series(index=frame.index, dtype=float)),
            errors="coerce",
        )
        mask = mask | (verified_flag & projected.notna())

    return mask


def prepare_commercial_ownership(source):
    out = source.copy()
    verified = verified_ownership_mask(out)

    verified_values = pd.Series(float("nan"), index=out.index)
    if "verified_ownership_pct" in out.columns:
        verified_values = pd.to_numeric(out["verified_ownership_pct"], errors="coerce")

    projected = pd.to_numeric(
        out.get("projected_ownership_pct", pd.Series(index=out.index, dtype=float)),
        errors="coerce",
    )
    projected_source = (
        out.get("projected_ownership_source", pd.Series("", index=out.index))
        .fillna("")
        .astype(str)
        .str.upper()
    )
    verified_projected = (
        projected.notna()
        & projected_source.str.strip().ne("")
        & ~projected_source.str.contains("HEURISTIC|MODELLED|MODELED|SHARKSNIP", regex=True)
    )

    commercial_projected = verified_values.where(verified_values.notna(), projected.where(verified_projected))
    out["projected_ownership_pct"] = commercial_projected
    out["modelled_ownership_pct"] = None

    modelled_available = False
    if "modelled_ownership_pct" in source.columns:
        modelled_available = bool(pd.to_numeric(source["modelled_ownership_pct"], errors="coerce").notna().any())

    return out, bool(verified.any()), modelled_available


def player_payload(slot, row, reason, locked):
    keys = [
        "player", "player_key", "position", "team", "opponent", "salary",
        "projected_fantasy_points", "audit_value_per_1000",
        "contest_archetype", "context_signal", "availability_status",
        "injury_type", "projected_ownership_pct", "modelled_ownership_pct",
    ]
    out = {key: clean_value(row.get(key)) for key in keys}
    out["slot"] = slot
    out["why"] = reason
    out["locked"] = bool(locked)
    return out


def main():
    request = json.loads(sys.stdin.read() or "{}")
    platform = str(request.get("platform") or "DRAFTKINGS").upper()
    mode = str(request.get("mode") or "BEST_OVERALL").upper()
    strategy = MODE_TO_STRATEGY.get(mode)
    if not strategy:
        raise ValueError("Unsupported DFS build mode.")

    locked = [str(x) for x in request.get("locked_keys") or [] if str(x)]
    excluded = [str(x) for x in request.get("excluded_keys") or [] if str(x)]
    alternatives = max(1, min(10, int(request.get("alternatives") or 3)))

    rows, generated_at = load_rows()
    source = pd.DataFrame(rows)
    if source.empty:
        raise ValueError("The current DFS projection pool is unavailable.")

    slate_id = request.get("slate_id")
    platform_rows = source[
        source["sport"].astype(str).str.upper().eq("NFL")
        & source["platform"].astype(str).str.upper().eq(platform)
    ].copy()
    if slate_id is None and "slate_id" in platform_rows.columns and not platform_rows.empty:
        counts = platform_rows["slate_id"].astype(str).value_counts()
        if not counts.empty:
            slate_id = counts.index[0]

    raw_prepared = prepare_pool(source, platform, slate_id=slate_id)
    verified_ownership_available = bool(verified_ownership_mask(raw_prepared).any())
    modelled_ownership_available = bool(
        "modelled_ownership_pct" in raw_prepared.columns
        and pd.to_numeric(raw_prepared["modelled_ownership_pct"], errors="coerce").notna().any()
    )

    source_for_optimizer, _, _ = prepare_commercial_ownership(source)
    prepared = prepare_pool(source_for_optimizer, platform, slate_id=slate_id)
    ownership_available = bool(
        verified_ownership_available
        and "projected_ownership_pct" in prepared.columns
        and pd.to_numeric(prepared["projected_ownership_pct"], errors="coerce").notna().any()
    )

    if strategy == "Contrarian" and not ownership_available:
        response = {
            "status": "MODE_UNAVAILABLE",
            "reason": "Contrarian mode requires verified current slate ownership. Sports Zenith will not unlock leverage mode from modelled or heuristic ownership alone.",
            "platform": platform,
            "slate_id": str(slate_id) if slate_id is not None else None,
            "mode": mode,
            "strategy": strategy,
            "ownership_available": False,
            "verified_ownership_available": False,
            "modelled_ownership_available": modelled_ownership_available,
            "ownership_policy": "VERIFIED_ONLY_FOR_CONTRARIAN",
            "pool_size": int(len(prepared)),
            "generated_at": generated_at,
            "lineups": [],
        }
        print(json.dumps(response, separators=(",", ":")))
        return

    reference_lineups = []
    max_overlap = None
    if strategy in {"GPP", "Contrarian"}:
        for reference_strategy in ["Balanced", "Cash Safe"]:
            reference = optimize_nfl(
                source_for_optimizer,
                platform,
                locked_keys=locked,
                excluded_keys=excluded,
                strategy=reference_strategy,
                alternatives=1,
                slate_id=slate_id,
            )
            if reference:
                reference_lineups.append([
                    str(player.get("player_key"))
                    for _, player in reference[0]["players"]
                    if str(player.get("player_key") or "")
                ])
        max_overlap = 7 if strategy == "GPP" else 6

    results = optimize_nfl(
        source_for_optimizer,
        platform,
        locked_keys=locked,
        excluded_keys=excluded,
        strategy=strategy,
        alternatives=alternatives,
        slate_id=slate_id,
        reference_lineups=reference_lineups,
        max_overlap=max_overlap,
    )

    lineups = []
    for result in results:
        frame = lineup_frame(result, strategy, locked_keys=locked)
        reasons = {
            str(row["Player"]): str(row["Why"])
            for _, row in frame.iterrows()
        }
        players = []
        for slot, player in result["players"]:
            players.append(
                player_payload(
                    slot,
                    player,
                    reasons.get(str(player.get("player")), "Projection/value fit"),
                    str(player.get("player_key")) in set(locked),
                )
            )
        lineups.append({
            "players": players,
            "salary_used": result["salary_used"],
            "salary_cap": result["salary_cap"],
            "salary_remaining": result["salary_remaining"],
            "projected_points": result["projected_points"],
            "optimizer_score": result["optimizer_score"],
            "stack_pattern": result["stack_pattern"],
            "games_used": result["games_used"],
            "ownership_player_count": result.get("ownership_player_count", 0),
            "projected_ownership_sum": result.get("projected_ownership_sum"),
            "strategy_constraints": result.get("strategy_constraints", {}),
        })

    if lineups:
        status = "READY"
        unavailable_reason = None
    elif strategy in {"GPP", "Contrarian"}:
        status = "MODE_UNAVAILABLE"
        unavailable_reason = (
            "No lineup satisfied the strategy's required differentiation from Balanced/Cash under the current slate constraints."
        )
    else:
        status = "NO_LEGAL_LINEUP"
        unavailable_reason = None

    response = {
        "status": status,
        "reason": unavailable_reason,
        "platform": platform,
        "slate_id": str(slate_id) if slate_id is not None else None,
        "mode": mode,
        "strategy": strategy,
        "ownership_available": ownership_available,
        "verified_ownership_available": ownership_available,
        "modelled_ownership_available": modelled_ownership_available,
        "ownership_policy": "VERIFIED_ONLY_FOR_CONTRARIAN",
        "pool_size": int(len(prepared)),
        "generated_at": generated_at,
        "lineups": lineups,
    }
    print(json.dumps(response, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}))
        sys.exit(1)
