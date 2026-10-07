#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUTS = [
    ROOT / "commercial_web/public/ask_context.json",
    ROOT / "commercial_web/dist/ask_context.json",
]

SOURCES = {
    "weekly_fantasy": ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_WEEKLY_DECISIONS_CURRENT.csv",
    "waivers": ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_FAAB_RESEARCH_CURRENT.csv",
    "stash": ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_IR_STASH_CURRENT.csv",
    "defense_streaming": ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_DEFENSE_STREAMING_CURRENT.csv",
    "idp": ROOT / "intelligence_warehouse/fantasy_decisions/FANTASY_IDP_OPPORTUNITY_CURRENT.csv",
    "dfs": ROOT / "intelligence_warehouse/dfs/DFS_CONTEST_ARCHETYPES_CURRENT.csv",
    "schedule_load": ROOT / "intelligence_warehouse/schedule/TEAM_SCHEDULE_LOAD_CURRENT.csv",
    "future_schedule": ROOT / "intelligence_warehouse/schedule/FUTURE_SCHEDULE_DIFFICULTY.csv",
}

LIMITS = {
    "weekly_fantasy": 160,
    "waivers": 120,
    "stash": 120,
    "defense_streaming": 40,
    "idp": 120,
    "dfs": 240,
    "schedule_load": 1600,
    "future_schedule": 1600,
}


def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def frame_to_records(df, limit):
    if df.empty:
        return []
    out = []
    for row in df.head(limit).to_dict("records"):
        out.append({k: clean_value(v) for k, v in row.items()})
    return out


def load(name, path):
    if not path.exists():
        return []
    df = pd.read_csv(path, low_memory=False)

    if "sport" in df.columns and name in {"weekly_fantasy", "waivers", "stash", "defense_streaming", "idp", "dfs"}:
        nfl = df[df["sport"].astype(str).str.upper().eq("NFL")].copy()
        if not nfl.empty:
            df = nfl

    if name == "weekly_fantasy" and "weekly_research_score" in df.columns:
        df["_sort"] = pd.to_numeric(df["weekly_research_score"], errors="coerce")
        df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"], errors="ignore")
    elif name == "waivers" and "waiver_research_score" in df.columns:
        df["_sort"] = pd.to_numeric(df["waiver_research_score"], errors="coerce")
        df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"], errors="ignore")
    elif name == "stash" and "stash_research_score" in df.columns:
        df["_sort"] = pd.to_numeric(df["stash_research_score"], errors="coerce")
        df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"], errors="ignore")
    elif name == "defense_streaming" and "weekly_stream_score" in df.columns:
        df["_sort"] = pd.to_numeric(df["weekly_stream_score"], errors="coerce")
        df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"], errors="ignore")
    elif name == "idp" and "idp_usage_score" in df.columns:
        df["_sort"] = pd.to_numeric(df["idp_usage_score"], errors="coerce")
        df = df.sort_values("_sort", ascending=False).drop(columns=["_sort"], errors="ignore")
    elif name == "dfs":
        df = df[
            df["platform"].astype(str).str.upper().isin(["FANDUEL", "DRAFTKINGS"])
        ].copy() if "platform" in df.columns else df
        if "projected_fantasy_points" in df.columns:
            df["_sort"] = pd.to_numeric(df["projected_fantasy_points"], errors="coerce")
            if "platform" in df.columns:
                per_platform = max(1, LIMITS[name] // 2)
                parts = []
                for platform in ["FANDUEL", "DRAFTKINGS"]:
                    part = df[
                        df["platform"].astype(str).str.upper().eq(platform)
                    ].sort_values("_sort", ascending=False).head(per_platform)
                    if not part.empty:
                        parts.append(part)
                if parts:
                    df = pd.concat(parts, ignore_index=True)
                else:
                    df = df.sort_values("_sort", ascending=False)
            else:
                df = df.sort_values("_sort", ascending=False)
            df = df.drop(columns=["_sort"], errors="ignore")

    return frame_to_records(df, LIMITS[name])


def main():
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "generated_at": now,
        "source": "Governed intelligence warehouse",
        "datasets": {},
        "status": {},
    }

    for name, path in SOURCES.items():
        try:
            rows = load(name, path)
            payload["datasets"][name] = rows
            payload["status"][name] = {
                "status": "CURRENT" if rows else "WAITING",
                "rows": len(rows),
                "path": str(path.relative_to(ROOT)),
                "modified_at": (
                    datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
                    if path.exists()
                    else None
                ),
            }
        except Exception as exc:
            payload["datasets"][name] = []
            payload["status"][name] = {
                "status": "ERROR",
                "rows": 0,
                "path": str(path.relative_to(ROOT)),
                "error": repr(exc),
            }

    for out in OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    print(json.dumps({
        "generated_at": now,
        "rows": {k: len(v) for k, v in payload["datasets"].items()},
        "errors": [
            k for k, v in payload["status"].items()
            if v.get("status") == "ERROR"
        ],
    }, indent=2))


if __name__ == "__main__":
    main()
