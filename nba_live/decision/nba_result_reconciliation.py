"""Resolve duplicate official NBA game results without losing verified metadata.

This module does not fetch data, mutate source histories, or infer a competition
type from the schedule. Conflicting final scores/teams/types remain ungraded.
"""
from __future__ import annotations

from math import isfinite
from typing import Any

import pandas as pd


def explicit_type(value: Any) -> str:
    """Canonicalize an explicitly supplied season code, not a game date."""
    if value is None or pd.isna(value):
        return ""
    raw = str(value).strip().lower()
    named = {
        "preseason": "1", "pre-season": "1",
        "regular": "2", "regular season": "2",
        "postseason": "3", "post-season": "3",
        "playoffs": "3", "playoff": "3",
    }
    if raw in named:
        return named[raw]
    try:
        parsed = float(raw)
        if isfinite(parsed) and parsed.is_integer() and 0 < parsed < 100:
            return str(int(parsed))
    except (ValueError, TypeError):
        pass
    return ""


def numeric_score(value: Any) -> float | None:
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (TypeError, ValueError):
        return None


def bool_final(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "yes", "1"}


def source_quality(group: pd.DataFrame) -> list[int]:
    """Sort stable: final, actual score, explicit type, preferred source."""
    quality = []
    for _, row in group.iterrows():
        points = (
            1000 * int(bool_final(row.get("completed")))
            + 100 * int(numeric_score(row.get("home_score")) is not None
                        and numeric_score(row.get("away_score")) is not None)
            + 10 * int(bool(explicit_type(row.get("season_type"))))
            + 3 - int(row.get("_source_order", 0))
        )
        quality.append(points)
    return quality


def final_conflicts(group: pd.DataFrame) -> list[str]:
    """Disagreeing final evidence must not silently become a WIN or LOSS."""
    finals = group[group["completed"].map(bool_final)]
    if len(finals) < 2:
        return []
    reasons = []
    valid_scores = set()
    valid_teams = set()
    valid_types = set()
    valid_dates = set()
    for _, row in finals.iterrows():
        home = numeric_score(row.get("home_score"))
        away = numeric_score(row.get("away_score"))
        if home is not None and away is not None:
            valid_scores.add((home, away))
        away_team = str(row.get("away_team_norm") or "").strip()
        home_team = str(row.get("home_team_norm") or "").strip()
        if away_team and home_team and away_team.lower() != "nan" and home_team.lower() != "nan":
            valid_teams.add((away_team, home_team))
        typ = explicit_type(row.get("season_type"))
        if typ:
            valid_types.add(typ)
        dt = row.get("start_dt")
        if pd.notna(dt):
            valid_dates.add(pd.Timestamp(dt).date())
    if len(valid_scores) > 1:
        reasons.append("FINAL_SCORE_CONFLICT")
    if len(valid_teams) > 1:
        reasons.append("FINAL_TEAM_CONFLICT")
    if len(valid_types) > 1:
        reasons.append("FINAL_SEASON_TYPE_CONFLICT")
    if len(valid_dates) > 1:
        reasons.append("FINAL_DATE_CONFLICT")
    return reasons


def reconcile_games(games: pd.DataFrame) -> pd.DataFrame:
    """One reproducible game row per event id, preserving explicit metadata.

    A final result is preferred over a scheduled row, then a complete score,
    then an explicit season type, then the earlier official source. Conflict
    flags are carried into the grader, never silently resolved.
    """
    if games.empty:
        return games.copy()
    rows = []
    for event_id, group in games.groupby("event_id", dropna=False, sort=False):
        scored = group.copy()
        scored["_source_quality"] = source_quality(scored)
        chosen = scored.sort_values("_source_quality", kind="stable").iloc[-1].copy()
        conflicts = final_conflicts(group)
        chosen["_result_conflict"] = "|".join(conflicts)
        chosen["_official_result_sources"] = int(len(group))
        explicit = explicit_type(chosen.get("season_type"))
        chosen["season_type"] = explicit if explicit else None
        rows.append(chosen)
    return pd.DataFrame(rows).reset_index(drop=True).drop(
        columns=["_source_quality"], errors="ignore"
    )
