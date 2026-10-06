#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/ubuntu/sports-hulk")
PUBLIC = ROOT / "commercial_web" / "public"
DIST = ROOT / "commercial_web" / "dist"

INPUTS = {
    "performance": PUBLIC / "performance_snapshot.json",
    "bets": PUBLIC / "betting_v2_all_markets_current.json",
    "props": PUBLIC / "prop_v2_current.json",
    "survivor": PUBLIC / "survivor_v2_current.json",
    "news": PUBLIC / "ask_retrieval.json",
    "fantasy": PUBLIC / "fantasy_decisions.json",
}

def load(name: str) -> dict:
    try:
        return json.loads(INPUTS[name].read_text())
    except Exception:
        return {}

def slugify(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:96] or "draft"

def ev(label, value, source_ref, note=None):
    item = {"label": label, "value": value, "source_ref": source_ref}
    if note:
        item["note"] = note
    return item

def source(label, source_name, url=None, published_at=None, source_ref=None):
    item = {"label": label, "source": source_name}
    if url:
        item["url"] = url
    if published_at:
        item["published_at"] = published_at
    if source_ref:
        item["source_ref"] = source_ref
    return item

def brief(*, category, title, thesis, priority, route, evidence, reasoning, risks, changes_mind, sources, labels=None):
    return {
        "draft_id": slugify(category + "-" + title),
        "slug": slugify(title),
        "category": category,
        "status": "DRAFT_BRIEF_ONLY",
        "priority": int(priority),
        "title": title,
        "thesis": thesis,
        "related_route": route,
        "evidence": evidence,
        "reasoning": reasoning,
        "risks": risks,
        "what_could_change_the_conclusion": changes_mind,
        "sources": sources,
        "suggested_sections": [
            "What happened / current state",
            "Why it matters",
            "Evidence",
            "Current conclusion",
            "Confidence and proof status",
            "What could change the conclusion",
            "Sources",
        ],
        "claim_guardrails": labels or [
            "Do not convert research scores into probabilities.",
            "Do not call PASS or MONITOR a PLAY.",
            "Do not claim profitability without captured price/payout evidence.",
            "Attribute external reporting and preserve source links.",
            "Manual editorial approval is required before publication.",
        ],
    }

def main():
    performance = load("performance")
    bets = load("bets")
    props = load("props")
    survivor = load("survivor")
    news = load("news")
    fantasy = load("fantasy")
    drafts = []

    official = performance.get("official") or {}
    if official:
        record = f"{official.get('wins',0)}-{official.get('losses',0)}-{official.get('pushes',0)}"
        units = official.get("units")
        roi = official.get("roi_pct")
        title = f"Brain Record update: the official forward record is {record}"
        drafts.append(brief(
            category="Brain Record",
            title=title,
            thesis="The public record should show the first official result exactly as it happened, including losses, because forward accountability is more valuable than a polished backfilled launch record.",
            priority=96,
            route="#brain-record",
            evidence=[
                ev("Official record", record, "performance_snapshot.json"),
                ev("Published", official.get("published", 0), "performance_snapshot.json"),
                ev("Settled", official.get("settled", 0), "performance_snapshot.json"),
                ev("Units", units, "performance_snapshot.json"),
                ev("ROI", None if roi is None else f"{roi:.1f}%", "performance_snapshot.json"),
            ],
            reasoning=[
                "Only picks frozen as OFFICIAL after record start count.",
                "Historical research is not backfilled into the headline record.",
                "A losing first result remains visible rather than being removed or reclassified.",
            ],
            risks=[
                "One settled pick is far too small a sample to judge model quality.",
                "Early ROI can move dramatically with each additional result.",
            ],
            changes_mind=[
                "Additional settled official picks expand the sample.",
                "Price capture or settlement corrections would change units/ROI if the source data were wrong.",
            ],
            sources=[source("Official performance ledger", "Internal governed snapshot", source_ref="performance_snapshot.json")],
            labels=[
                "Do not frame a one-pick sample as proof of quality.",
                "Do not hide or minimize losses.",
                "State that this is the official forward record, not historical validation.",
                "Manual editorial approval is required before publication.",
            ],
        ))

    bet_summary = bets.get("summary") or {}
    if bet_summary:
        candidates = int(bet_summary.get("candidates") or 0)
        plays = int(bet_summary.get("shadow_plays") or 0)
        passes = int(bet_summary.get("passes") or 0)
        drafts.append(brief(
            category="Best Bets",
            title="Why there is no Best Bet PLAY right now",
            thesis="A disciplined no-play slate is a valid outcome when candidates fail independent-edge, price or proof gates.",
            priority=93,
            route="#best-bets",
            evidence=[
                ev("Current candidates", candidates, "betting_v2_all_markets_current.json"),
                ev("V2 PLAYs", plays, "betting_v2_all_markets_current.json"),
                ev("PASS decisions", passes, "betting_v2_all_markets_current.json"),
                ev("Opposite-side conflicts", bet_summary.get("opposite_side_conflicts", 0), "betting_v2_all_markets_current.json"),
                ev("Duplicate line variants", bet_summary.get("duplicate_line_variants", 0), "betting_v2_all_markets_current.json"),
            ],
            reasoning=[
                "A high market-implied probability is not enough; the model must create independent edge.",
                "Available price and conservative EV must support the selection.",
                "Conflict and alternate-line gates prevent a crowded board from masquerading as many independent opportunities.",
            ],
            risks=[
                "The slate can change as prices and market data update.",
                "No-play today does not imply the model will never find a qualified play.",
            ],
            changes_mind=[
                "A candidate clears independent model edge plus conservative price/EV proof.",
                "Forward evidence reaches the promotion threshold without violating exposure/conflict gates.",
            ],
            sources=[source("Best Bets V2 current board", bets.get("model_version") or "Internal governed snapshot", source_ref="betting_v2_all_markets_current.json")],
        ))

    prop_rows = props.get("picks") or []
    monitors = [r for r in prop_rows if r.get("lane") == "PRIZEPICKS" and r.get("shadow_decision") == "SHADOW_MONITOR"]
    if monitors:
        row = sorted(monitors, key=lambda r: float(r.get("conservative_edge_pct_points") or -999), reverse=True)[0]
        title = f"Why {row.get('player')} {row.get('side')} {row.get('line')} {str(row.get('market_subtype') or '').replace('_',' ').title()} is a monitor — not a PLAY"
        drafts.append(brief(
            category="PrizePicks",
            title=title,
            thesis="The current signal is interesting enough to freeze and monitor forward, but the evidence is not mature enough to call it a proven play or profitable entry.",
            priority=91,
            route="#prizepicks",
            evidence=[
                ev("Model probability", f"{row.get('v2_probability_pct')}%", "prop_v2_current.json"),
                ev("Market reference", f"{row.get('market_reference_probability_pct')}%", "prop_v2_current.json"),
                ev("Conservative probability", f"{row.get('conservative_probability_pct')}%", "prop_v2_current.json"),
                ev("Conservative edge", f"{row.get('conservative_edge_pct_points')} pts", "prop_v2_current.json"),
                ev("Reference price", row.get("american_odds"), "prop_v2_current.json"),
                ev("Data quality", row.get("data_quality_grade"), "prop_v2_current.json"),
                ev("Proof status", row.get("historical_edge_confidence"), "prop_v2_current.json"),
            ],
            reasoning=[
                "The model probability is above the de-vigged market reference in the current snapshot.",
                "The uncertainty haircut still leaves a positive conservative edge.",
                "The historical signal is explicitly labeled promising but uncertain, so the leg stays in shadow monitoring.",
                "PrizePicks entry economics are separate from single-leg probability and still require payout-level proof.",
            ],
            risks=[
                "A shadow monitor is not a recommendation.",
                "Player availability, role, line movement or platform payout can change the decision.",
                "Single-leg edge does not prove a multi-pick entry is profitable.",
            ],
            changes_mind=[
                "Forward settled evidence reaches the required independent sample and confidence thresholds.",
                "The live line/market moves enough to remove conservative edge.",
                "Entry-level payout economics are captured and fail or pass profitability review.",
            ],
            sources=[source("PrizePicks V2 monitor", row.get("model_version") or "Internal governed snapshot", source_ref="prop_v2_current.json")],
        ))

    candidates = survivor.get("candidates") or []
    if candidates:
        top = sorted(candidates, key=lambda r: float(r.get("strategy_index") or 0), reverse=True)[0]
        week = survivor.get("pool_current_week")
        locked = not bool(survivor.get("rule_confirmed"))
        title = (
            f"Week {week} Survivor: why {top.get('team')} leads the research board but the pick is locked"
            if locked else
            f"Week {week} Survivor: why {top.get('team')} leads the current board"
        )
        drafts.append(brief(
            category="Survivor",
            title=title,
            thesis="The research board can rank eligible teams while the final recommendation remains blocked until pool-specific rules and current-week ownership are confirmed.",
            priority=90,
            route="#survivor",
            evidence=[
                ev("Research leader", top.get("team"), "survivor_v2_current.json"),
                ev("Opponent", top.get("opponent"), "survivor_v2_current.json"),
                ev("Market survival", f"{top.get('market_prob_pct')}%", "survivor_v2_current.json"),
                ev("Spread", top.get("spread"), "survivor_v2_current.json"),
                ev("Context score", top.get("hulk_context_score"), "survivor_v2_current.json", "Internal research score; not a probability."),
                ev("Strategy index", top.get("strategy_index"), "survivor_v2_current.json"),
                ev("Rule status", survivor.get("rule_status"), "survivor_v2_current.json"),
                ev("Teams already used", len(survivor.get("used_teams") or []), "survivor_v2_current.json"),
            ],
            reasoning=[
                "Used teams are removed from the active-entry candidate set.",
                "Market survival is considered alongside context and future-value tradeoffs.",
                f"Positive signals: {str(top.get('positive_signals') or 'None').replace('|', ', ')}.",
                "The final recommendation stays locked when the current pool sheet has not confirmed the required pick count/ownership.",
            ],
            risks=[
                f"Risk signals: {str(top.get('risk_signals') or 'None').replace('|', ', ')}.",
                "Pool rules can change the optimal strategy even if team win probability does not change.",
            ],
            changes_mind=[
                "The official current-week pool sheet confirms required pick count and ownership.",
                "Market probability, injuries or opponent context materially change before kickoff.",
            ],
            sources=[source("Survivor V2 governed state", survivor.get("model_version") or "Internal governed snapshot", source_ref="survivor_v2_current.json")],
        ))

    faab_rows = (((fantasy.get("lanes") or {}).get("faab") or {}).get("rows") or [])
    if faab_rows:
        row = faab_rows[0]
        title = f"Waiver watch: why {row.get('player')} is surging in the current research board"
        drafts.append(brief(
            category="Fantasy",
            title=title,
            thesis="A rising role plus strong add activity can identify a waiver candidate worth researching, but generic FAAB ranges are not personalized bids.",
            priority=84,
            route="#fantasy",
            evidence=[
                ev("Player", row.get("player"), "fantasy_decisions.json"),
                ev("Team / position", f"{row.get('team')} · {row.get('position')}", "fantasy_decisions.json"),
                ev("Role signal", row.get("role_signal"), "fantasy_decisions.json"),
                ev("Adds in 24h", row.get("adds_24h"), "fantasy_decisions.json"),
                ev("Waiver research score", row.get("waiver_research_score"), "fantasy_decisions.json", "Research ranking; not a probability."),
                ev("Research FAAB range", f"{row.get('suggested_faab_low_pct')}–{row.get('suggested_faab_high_pct')}%", "fantasy_decisions.json"),
            ],
            reasoning=[
                "The current market-activity feed shows strong add volume.",
                "The role signal is moving upward in the current snapshot.",
                "The board combines role and market activity to prioritize research.",
            ],
            risks=[
                "No personal league size, roster need, scoring format or remaining FAAB budget is connected.",
                "The displayed FAAB range is a research range, not a prediction of the winning bid.",
            ],
            changes_mind=[
                "Role or availability changes before waivers run.",
                "Connected league context materially changes positional need or bidding constraints.",
            ],
            sources=[source("Fantasy decision snapshot", "Internal governed snapshot", source_ref="fantasy_decisions.json")],
            labels=[
                "Do not call the research score a probability.",
                "Do not present the FAAB range as a guaranteed or personalized bid.",
                "State that league-specific context is not connected.",
                "Manual editorial approval is required before publication.",
            ],
        ))

    news_events = [
        e for e in (news.get("news_events") or [])
        if e.get("event_source_type") == "NEWS"
        and e.get("event_type") in {"INJURY", "TRANSACTION", "LINEUP_ROLE"}
        and e.get("title")
        and e.get("source_url")
    ]
    if news_events:
        row = sorted(news_events, key=lambda e: str(e.get("published_or_effective_at") or ""), reverse=True)[0]
        title = f"{row.get('title')}: what to verify next"
        drafts.append(brief(
            category="News Impact",
            title=title,
            thesis="A source-linked development should trigger a structured impact review before it changes any betting, fantasy or player recommendation.",
            priority=82,
            route="#news",
            evidence=[
                ev("Sport", row.get("sport"), "ask_retrieval.json"),
                ev("Event type", row.get("event_type"), "ask_retrieval.json"),
                ev("Source", row.get("source"), "ask_retrieval.json"),
                ev("Published", row.get("published_or_effective_at"), "ask_retrieval.json"),
                ev("Source tier", row.get("source_tier"), "ask_retrieval.json"),
            ],
            reasoning=[
                row.get("detail") or row.get("title"),
                "The report is preserved as attributed reporting rather than silently converted into a verified player state.",
                "Any model or fantasy implication should be checked against structured availability/role data before publication.",
            ],
            risks=[
                "Breaking reports can be superseded by later official updates.",
                "The current brief does not infer a betting or fantasy recommendation from the headline alone.",
            ],
            changes_mind=[
                "An official team/league status update confirms or contradicts the report.",
                "Structured role, availability or market data changes after the report.",
            ],
            sources=[source(
                "Original report",
                row.get("source") or "External reporting",
                url=row.get("source_url"),
                published_at=row.get("published_or_effective_at"),
                source_ref=row.get("event_node_id"),
            )],
            labels=[
                "Attribute the report to its source.",
                "Do not turn a headline into a verified injury/availability status without structured confirmation.",
                "Do not infer a pick solely from news reporting.",
                "Manual editorial approval is required before publication.",
            ],
        ))

    drafts.sort(key=lambda item: item["priority"], reverse=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "READY",
        "schema_version": 1,
        "editorial_policy": {
            "auto_publish": False,
            "requires_manual_approval": True,
            "drafts_are_recommendations": False,
            "source_links_required": True,
            "proof_labels_required": True,
            "engagement_can_prioritize_topics": True,
            "engagement_can_change_prediction_truth": False,
        },
        "draft_count": len(drafts),
        "drafts": drafts,
    }

    rendered = json.dumps(payload, indent=2, allow_nan=False)
    for path in (PUBLIC / "insight_drafts.json", DIST / "insight_drafts.json"):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(rendered)
        tmp.replace(path)

    print(json.dumps({
        "status": "READY",
        "draft_count": len(drafts),
        "titles": [item["title"] for item in drafts],
    }, indent=2))

if __name__ == "__main__":
    main()
