#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
NEWS_NODES = ROOT / "intelligence_warehouse/news_graph/NEWS_EVENT_NODES_CURRENT.csv"
ENTITY_LINKS = ROOT / "intelligence_warehouse/news_graph/NEWS_ENTITY_LINKS_CURRENT.csv"
FACTS = ROOT / "sports_content/derived/SPORTS_FACTS_CURRENT.csv"

OUTS = [
    ROOT / "commercial_web/public/ask_retrieval.json",
    ROOT / "commercial_web/dist/ask_retrieval.json",
]

SPORTS = {"NFL", "MLB", "NBA", "NHL", "CFB", "CBB"}


def clean_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def records(df):
    return [
        {k: clean_value(v) for k, v in row.items()}
        for row in df.to_dict("records")
    ]


def main():
    nodes = pd.read_csv(NEWS_NODES, low_memory=False) if NEWS_NODES.exists() else pd.DataFrame()
    links = pd.read_csv(ENTITY_LINKS, low_memory=False) if ENTITY_LINKS.exists() else pd.DataFrame()
    facts = pd.read_csv(FACTS, low_memory=False) if FACTS.exists() else pd.DataFrame()

    if not nodes.empty:
        nodes = nodes[nodes["sport"].astype(str).str.upper().isin(SPORTS)].copy()
        nodes["_when"] = pd.to_datetime(
            nodes.get("published_or_effective_at"), errors="coerce", utc=True
        )
        nodes = nodes.sort_values("_when", ascending=False, na_position="last")
        # Keep all current nodes; the graph is already current-cycle bounded.
        nodes = nodes.drop(columns=["_when"], errors="ignore")

    if not links.empty:
        valid_ids = set(nodes["event_node_id"].astype(str)) if not nodes.empty else set()
        if valid_ids:
            links = links[links["event_node_id"].astype(str).isin(valid_ids)].copy()

    if not facts.empty:
        facts = facts[facts["sport"].astype(str).str.upper().isin(SPORTS)].copy()
        facts["_when"] = pd.to_datetime(
            facts.get("effective_at"), errors="coerce", utc=True
        )
        facts = facts.sort_values("_when", ascending=False, na_position="last")
        facts = facts.drop(columns=["_when"], errors="ignore")

    entity_index = {}
    if not links.empty:
        for row in links.to_dict("records"):
            event_id = str(row.get("event_node_id") or "")
            if not event_id:
                continue
            for raw in [
                row.get("entity_name"),
                row.get("entity_key"),
                row.get("entity_team"),
            ]:
                key = str(raw or "").strip().lower()
                if not key:
                    continue
                entity_index.setdefault(key, [])
                if event_id not in entity_index[key]:
                    entity_index[key].append(event_id)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Structured sports news/event graph",
        "news_events": records(nodes),
        "entity_links": records(links),
        "facts": records(facts),
        "entity_index": entity_index,
        "counts": {
            "news_events": int(len(nodes)),
            "entity_links": int(len(links)),
            "facts": int(len(facts)),
            "entities": int(len(entity_index)),
        },
        "truth_rules": {
            "structured_facts_first": True,
            "news_is_attributed_reporting": True,
            "source_links_preserved": True,
            "automatic_model_adjustment": False,
        },
    }

    for out in OUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    print(json.dumps({
        "generated_at": payload["generated_at"],
        "counts": payload["counts"],
        "outputs": [str(x) for x in OUTS],
    }, indent=2))


if __name__ == "__main__":
    main()
