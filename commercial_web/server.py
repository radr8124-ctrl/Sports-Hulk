#!/usr/bin/env python3
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone
import json
import re

ROOT = Path("/home/ubuntu/sports-hulk")
DIST = ROOT / "commercial_web" / "dist"
PORT = 8510

FILES = {
    "nfl_scores": DIST / "nfl_scores.json",
    "nfl_decisions": DIST / "nfl_decisions.json",
    "mlb_scores": DIST / "mlb_scores.json",
    "fantasy_news": DIST / "fantasy_news.json",
    "ask_context": DIST / "ask_context.json",
}


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_all():
    return {name: read_json(path) for name, path in FILES.items()}


def clean(value):
    return str(value or "").strip()
def qtext(value):
    return clean(value).lower()


def num(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def nice(value):
    text = clean(value).replace("_", " ").lower()
    return " ".join(word.capitalize() for word in text.split())


def source_rows(data, keys):
    labels = {
        "nfl_scores": ("NFL scores", "ESPN Core"),
        "nfl_decisions": ("NFL decisions", "Decision engine"),
        "mlb_scores": ("MLB scores", "MLB StatsAPI"),
        "fantasy_news": ("Fantasy news", "News collector"),
        "ask_context": ("Sports intelligence", "Governed warehouse"),
    }
    out = []
    for key in keys:
        payload = data.get(key) or {}
        label, default_source = labels[key]
        out.append({
            "label": label,
            "source": payload.get("source") or default_source,
            "updated_at": payload.get("generated_at"),
        })
    return out


def answer(intent, take, confidence="CURRENT", why=None, risk=None,
           cards=None, sources=None, updated_at=None, followups=None,
           status="CURRENT"):
    return {
        "intent": intent,
        "take": take,
        "confidence": confidence,
        "why": why or [],
        "risk": risk or [],
        "cards": cards or [],
        "sources": sources or [],
        "updated_at": updated_at,
        "followups": followups or [],
        "status": status,
    }
def aliases(game):
    return [
        clean(game.get("away")).lower(),
        clean(game.get("home")).lower(),
        clean(game.get("away_abbr")).lower(),
        clean(game.get("home_abbr")).lower(),
        clean(game.get("away_team")).lower(),
        clean(game.get("home_team")).lower(),
    ]


def find_game(question, games):
    q = qtext(question)
    for game in games:
        if any(alias and len(alias) >= 2 and alias in q for alias in aliases(game)):
            return game
    return None


def score_card(game, league):
    away = game.get("away") or game.get("away_team") or ""
    home = game.get("home") or game.get("home_team") or ""
    state = "FINAL" if game.get("final") else "LIVE" if game.get("live") else "UPCOMING"
    return {
        "type": "score",
        "league": league,
        "title": f"{away} @ {home}",
        "state": state,
        "away": away,
        "home": home,
        "away_score": game.get("away_score"),
        "home_score": game.get("home_score"),
        "status": game.get("status") or "",
        "start_time": game.get("start_time") or game.get("gameDate") or game.get("start"),
    }


def score_answer(question, data):
    q = qtext(question)
    mlb = bool(re.search(r"\b(mlb|baseball|padres|brewers|guardians|white sox)\b", q))
    payload = data.get("mlb_scores") if mlb else data.get("nfl_scores")
    games = (payload or {}).get("today_games" if mlb else "games") or []
    league = "MLB" if mlb else "NFL"
    matched = find_game(question, games)
    if matched:
        card = score_card(matched, league)
        known = matched.get("away_score") is not None and matched.get("home_score") is not None
        take = (
            f"{card['away']} {card['away_score']}, {card['home']} {card['home_score']} — {card['state']}."
            if known else
            f"{card['away']} at {card['home']} is {card['state'].lower()}."
        )
        return answer(
            "live_score", take, "VERIFIED",
            why=[card["status"] or "Current structured score snapshot"],
            risk=["Game has not started yet."] if card["state"] == "UPCOMING" else [],
            cards=[card],
            sources=source_rows(data, ["mlb_scores" if mlb else "nfl_scores"]),
            updated_at=(payload or {}).get("generated_at"),
            followups=["Show the box score", "What changed?", "Any injury news?"],
        )

    live = [g for g in games if g.get("live")]
    current = live or games[:6]
    return answer(
        "live_scores",
        f"{len(live)} {league} game{'s' if len(live) != 1 else ''} live now."
        if live else f"No {league} game is live in the current snapshot.",
        "VERIFIED",
        why=["Current structured score feed"],
        cards=[score_card(g, league) for g in current],
        sources=source_rows(data, ["mlb_scores" if mlb else "nfl_scores"]),
        updated_at=(payload or {}).get("generated_at"),
    )


def player_matches(question, rows):
    q = qtext(question)
    found, seen = [], set()
    for row in rows:
        player = clean(row.get("player") or row.get("player_dfs") or row.get("player_sportsbook"))
        key = player.lower()
        if player and key not in seen and key in q:
            seen.add(key)
            found.append(row)
    return found
def betting_answer(question, data):
    payload = data.get("nfl_decisions") or {}
    rows = list(payload.get("games") or [])
    rows.sort(key=lambda r: num(r.get("hulk_market_score"), 0), reverse=True)
    q = qtext(question)

    if "spread" in q:
        rows = [r for r in rows if clean(r.get("market")).upper() == "SPREAD"]
    elif "total" in q or re.search(r"\bover\b|\bunder\b", q):
        rows = [r for r in rows if clean(r.get("market")).upper() == "TOTAL"]
    elif "moneyline" in q or " ml " in f" {q} ":
        rows = [r for r in rows if clean(r.get("market")).upper() == "MONEYLINE"]

    matched = find_game(question, rows)
    chosen = [matched] if matched else rows[:5]
    if not chosen:
        return answer(
            "best_bet", "No current NFL game bet clears that market filter.",
            "WAITING", risk=["No qualified row in the current board."],
            sources=source_rows(data, ["nfl_decisions"]),
            updated_at=payload.get("generated_at"), status="WAITING",
        )

    top = chosen[0]
    line = clean(top.get("line"))
    take = f"{top.get('selection')} {nice(top.get('market'))} {line}".strip()
    evidence = num(top.get("hulk_market_score"), 0)
    high_juice = "HIGH_JUICE" in clean(top.get("decision")) or abs(num(top.get("line"), 0)) >= 300
    return answer(
        "best_bet", take,
        "STRONG EVIDENCE" if evidence >= 95 else "GOOD EVIDENCE" if evidence >= 85 else "RESEARCH LEAN",
        why=[
            f"{top.get('sw_books', '—')} books in consensus",
            f"Provider view: {nice(top.get('provider_agreement') or 'UNKNOWN')}",
            f"{top.get('market_implied_safety', '—')}% market-implied safety",
        ],
        risk=[
            "High juice; compare sportsbook price before placing." if high_juice else None,
            top.get("model_status") or "Market-backed research, not a guaranteed outcome.",
        ],
        cards=[{
            "type": "bet", "title": r.get("game_key"), "selection": r.get("selection"),
            "market": r.get("market"), "line": r.get("line"),
            "evidence": r.get("hulk_market_score"), "market_safety": r.get("market_implied_safety"),
            "books": r.get("sw_books"), "agreement": r.get("provider_agreement"),
            "decision": r.get("decision"),
        } for r in chosen],
        sources=source_rows(data, ["nfl_decisions"]),
        updated_at=payload.get("generated_at"),
        followups=["Show me spreads", "Show me totals", "Why is this strong?", "Best props"],
    )


def props_answer(question, data):
    payload = data.get("nfl_decisions") or {}
    rows = list(payload.get("props") or [])
    rows.sort(key=lambda r: num(r.get("hulk_prop_score"), 0), reverse=True)
    matched = player_matches(question, rows)
    chosen = matched[:4] if matched else rows[:6]

    if not chosen:
        return answer("props", "No qualified NFL prop is available.", "WAITING",
                      sources=source_rows(data, ["nfl_decisions"]),
                      updated_at=payload.get("generated_at"), status="WAITING")

    top = chosen[0]
    return answer(
        "props",
        f"{top.get('player_dfs')} {top.get('side')} {top.get('dfs_line')} {nice(top.get('stat_type') or top.get('market'))}",
        "STRONG RESEARCH" if num(top.get("hulk_prop_score"), 0) >= 85 else "QUALIFIED RESEARCH",
        why=[
            f"Recent metric {top.get('recent_metric', '—')} vs line {top.get('dfs_line', '—')}",
            f"{top.get('book_count', '—')} sportsbooks in coverage",
            f"Context: {nice(top.get('context_direction') or 'UNKNOWN')}",
            f"{top.get('meaningful_completed_games', '—')} meaningful completed games",
        ],
        risk=[
            f"Injury screen: {nice(top.get('espn_injury_gate'))}"
            if top.get("espn_injury_gate") not in (None, "", "NO_ESPN_LISTING")
            else "No current ESPN injury-listing flag.",
            "Verify current sportsbook line and price before use.",
        ],
        cards=[{
            "type": "prop", "title": r.get("player_dfs"), "team": r.get("player_team"),
            "matchup": f"{r.get('away_team')} @ {r.get('home_team')}",
            "market": nice(r.get("stat_type") or r.get("market")), "side": r.get("side"),
            "line": r.get("dfs_line"), "recent": r.get("recent_metric"),
            "evidence": r.get("hulk_prop_score"), "books": r.get("book_count"),
            "sample": r.get("meaningful_completed_games"), "context": r.get("context_direction"),
        } for r in chosen],
        sources=source_rows(data, ["nfl_decisions"]),
        updated_at=payload.get("generated_at"),
        followups=["Passing props", "Rushing props", "What is the injury risk?", "Build a parlay"],
    )
def survivor_answer(data):
    payload = data.get("nfl_decisions") or {}
    rank = {"TOP_TIER": 0, "STRONG": 1, "VIABLE": 2, "WATCH": 3, "CAUTION": 4}
    rows = list(payload.get("survivor") or [])
    rows.sort(key=lambda r: (rank.get(clean(r.get("hulk_decision_tier")), 9),
                             -num(r.get("hulk_context_score"), 0)))
    if not rows:
        return answer("survivor", "No Survivor strategy row is available.", "WAITING",
                      sources=source_rows(data, ["nfl_decisions"]), status="WAITING")

    top = rows[0]
    return answer(
        "survivor",
        f"{top.get('survivor_team')} is the top current Survivor research option.",
        nice(top.get("hulk_decision_tier")),
        why=[
            f"Market survival probability {top.get('market_prob_pct', '—')}%",
            f"Context score {top.get('hulk_context_score', '—')}",
            f"Positive: {nice(top.get('positive_signals'))}" if top.get("positive_signals") else None,
        ],
        risk=[
            nice(top.get("risk_signals")) if top.get("risk_signals") else "No explicit risk flag.",
            "Commercial board does not yet know this user's burned teams.",
        ],
        cards=[{
            "type": "survivor", "title": r.get("survivor_team"),
            "opponent": r.get("away_team") if r.get("survivor_team") == r.get("home_team") else r.get("home_team"),
            "market_prob": r.get("market_prob_pct"), "spread": r.get("survivor_spread"),
            "context_score": r.get("hulk_context_score"), "tier": r.get("hulk_decision_tier"),
            "positives": r.get("positive_signals"), "risks": r.get("risk_signals"),
        } for r in rows[:5]],
        sources=source_rows(data, ["nfl_decisions"]),
        updated_at=payload.get("generated_at"),
        followups=["Why this pick?", "What team should I save?", "Show five options"],
    )


def parlay_answer(data):
    payload = data.get("nfl_decisions") or {}
    rows = list(payload.get("parlays") or [])
    rows.sort(key=lambda r: num(r.get("parlay_score"), 0), reverse=True)
    if not rows:
        return answer("parlay", "No qualified parlay is available.", "WAITING",
                      sources=source_rows(data, ["nfl_decisions"]), status="WAITING")
    top = rows[0]
    return answer(
        "parlay", f"{top.get('leg1_label')} + {top.get('leg2_label')}", "QUALIFIED RESEARCH",
        why=[
            f"Leg scores {top.get('leg1_score', '—')} / {top.get('leg2_score', '—')}",
            nice(top.get("correlation_status")),
            f"Parlay research score {top.get('parlay_score', '—')}",
        ],
        risk=["Combined win probability is not fabricated.", "Verify final payout and lines at the sportsbook."],
        cards=[{
            "type": "parlay", "title": nice(r.get("parlay_type")),
            "leg1": r.get("leg1_label"), "leg2": r.get("leg2_label"),
            "leg1_score": r.get("leg1_score"), "leg2_score": r.get("leg2_score"),
            "score": r.get("parlay_score"), "correlation": r.get("correlation_status"),
        } for r in rows[:5]],
        sources=source_rows(data, ["nfl_decisions"]),
        updated_at=payload.get("generated_at"),
    )


def ask_rows(data, name):
    return ((data.get("ask_context") or {}).get("datasets") or {}).get(name) or []
def start_sit_answer(question, data):
    rows = ask_rows(data, "weekly_fantasy")
    matches = player_matches(question, rows)
    if not matches:
        chosen = []
        for pos in ("QB", "RB", "WR", "TE"):
            row = next((r for r in rows if clean(r.get("position")).upper() == pos
                        and clean(r.get("weekly_tier")).upper() != "INACTIVE"), None)
            if row:
                chosen.append(row)
    else:
        chosen = matches

    if not chosen:
        return answer("start_sit", "The weekly fantasy decision board is unavailable.", "WAITING",
                      sources=source_rows(data, ["ask_context"]), status="WAITING")

    chosen.sort(key=lambda r: num(r.get("weekly_research_score"), 0), reverse=True)
    top = chosen[0]
    compare = f" over {chosen[1].get('player')}" if len(chosen) > 1 else ""
    return answer(
        "start_sit", f"Start {top.get('player')}{compare}.", nice(top.get("weekly_tier") or "RESEARCH"),
        why=[
            top.get("research_reasons"),
            f"Role: {nice(top.get('role_signal') or 'UNKNOWN')}",
            f"Matchup pressure: {nice(top.get('defensive_pressure_context'))}"
            if top.get("defensive_pressure_context") else None,
        ],
        risk=[
            f"Availability: {nice(top.get('availability_status'))}"
            if top.get("availability_status") not in (None, "", "ACTIVE", "CLEAR")
            else "Recheck inactives and late news before lock."
        ],
        cards=[{
            "type": "fantasy", "title": r.get("player"), "team": r.get("team"),
            "position": r.get("position"), "opponent": r.get("opponent"),
            "tier": r.get("weekly_tier"), "score": r.get("weekly_research_score"),
            "role": r.get("role_signal"), "matchup": r.get("defensive_pressure_context"),
            "reasons": r.get("research_reasons"),
        } for r in chosen[:5]],
        sources=source_rows(data, ["ask_context"]),
        updated_at=(data.get("ask_context") or {}).get("generated_at"),
        followups=["Top waiver adds", "IR stash candidates", "Best defense to stream"],
    )


def waivers_answer(data):
    rows = [r for r in ask_rows(data, "waivers") if "STASH" not in clean(r.get("waiver_priority"))]
    rows.sort(key=lambda r: num(r.get("waiver_research_score"), 0), reverse=True)
    rows = rows[:6]
    if not rows:
        return answer("waivers", "No waiver board is available.", "WAITING", status="WAITING")
    top = rows[0]
    return answer(
        "waivers", f"{top.get('player')} is the top current waiver/FAAB research add.",
        nice(top.get("waiver_priority")),
        why=[
            f"FAAB research range {top.get('suggested_faab_low_pct', 0)}–{top.get('suggested_faab_high_pct', 0)}%",
            f"24h add rank {top.get('add_rank_24h')}" if top.get("add_rank_24h") is not None else None,
            f"Role: {nice(top.get('role_signal') or 'UNKNOWN')}",
        ],
        risk=["FAAB range is research guidance, not a prediction of league bidding."],
        cards=[{
            "type": "waiver", "title": r.get("player"), "team": r.get("team"),
            "position": r.get("position"), "priority": r.get("waiver_priority"),
            "faab_low": r.get("suggested_faab_low_pct"), "faab_high": r.get("suggested_faab_high_pct"),
            "add_rank": r.get("add_rank_24h"), "role": r.get("role_signal"),
        } for r in rows],
        sources=source_rows(data, ["ask_context"]),
        updated_at=(data.get("ask_context") or {}).get("generated_at"),
    )


def stash_answer(data):
    rows = list(ask_rows(data, "stash"))
    rows.sort(key=lambda r: num(r.get("stash_research_score"), 0), reverse=True)
    rows = rows[:6]
    if not rows:
        return answer("stash", "No stash board is available.", "WAITING", status="WAITING")
    top = rows[0]
    return answer(
        "stash", f"{top.get('player')} is the top current return/stash research candidate.",
        nice(top.get("stash_tier")),
        why=[
            f"Return window: {nice(top.get('return_window') or 'UNKNOWN')}",
            f"Status: {nice(top.get('status') or 'UNKNOWN')}",
            f"Role: {nice(top.get('role_signal'))}" if top.get("role_signal") else None,
        ],
        risk=["Injury sources disagree." if top.get("source_disagreement")
              else "Return timing is research, not a guarantee."],
        cards=[{
            "type": "stash", "title": r.get("player"), "team": r.get("team"),
            "position": r.get("position"), "status": r.get("status"),
            "return_window": r.get("return_window"), "tier": r.get("stash_tier"),
            "source_disagreement": r.get("source_disagreement"),
        } for r in rows],
        sources=source_rows(data, ["ask_context"]),
        updated_at=(data.get("ask_context") or {}).get("generated_at"),
    )
def defense_answer(data):
    rows = list(ask_rows(data, "defense_streaming"))
    rows.sort(key=lambda r: num(r.get("weekly_stream_score"), 0), reverse=True)
    rows = rows[:6]
    if not rows:
        return answer("defense_stream", "No defense streaming board is available.", "WAITING", status="WAITING")
    top = rows[0]
    return answer(
        "defense_stream", f"{top.get('dst_player') or top.get('team')} is the top current D/ST stream.",
        nice(top.get("weekly_stream_tier")),
        why=[
            f"Next opponent: {top.get('next_opponent', '—')}",
            f"Weekly stream score {top.get('weekly_stream_score', '—')}",
            f"Multi-week hold score {top.get('multiweek_hold_score', '—')}",
        ],
        risk=["Streaming scores are research ranks, not guaranteed fantasy points."],
        cards=[{
            "type": "defense", "title": r.get("dst_player") or r.get("team"),
            "opponent": r.get("next_opponent"), "weekly_score": r.get("weekly_stream_score"),
            "weekly_tier": r.get("weekly_stream_tier"), "hold_score": r.get("multiweek_hold_score"),
            "hold_tier": r.get("multiweek_hold_tier"),
        } for r in rows],
        sources=source_rows(data, ["ask_context"]),
        updated_at=(data.get("ask_context") or {}).get("generated_at"),
    )


def dfs_answer(question, data):
    q = qtext(question)
    platform = "DRAFTKINGS" if "draftkings" in q or " dk " in f" {q} " else "FANDUEL" if "fanduel" in q else None
    rows = [r for r in ask_rows(data, "dfs")
            if clean(r.get("sport")).upper() == "NFL" and r.get("projected_fantasy_points") is not None]
    if platform:
        rows = [r for r in rows if clean(r.get("platform")).upper() == platform]
    rows.sort(key=lambda r: num(r.get("projected_fantasy_points"), 0), reverse=True)
    rows = rows[:8]
    if not rows:
        return answer("dfs", "No current projected DFS pool is available.", "WAITING", status="WAITING")
    top = rows[0]
    return answer(
        "dfs",
        f"{top.get('player')} has the highest current {nice(platform) + ' ' if platform else ''}projection in the Ask snapshot.",
        "PROJECTED",
        why=[
            f"{top.get('projected_fantasy_points')} projected points",
            f"{top.get('salary', '—')} salary",
            f"{num(top.get('audit_value_per_1000'), 0):.2f} pts/$1K",
            nice(top.get("contest_archetype")),
        ],
        risk=["DFS projections can move with late news and inactives."],
        cards=[{
            "type": "dfs", "title": r.get("player"), "platform": r.get("platform"),
            "team": r.get("team"), "position": r.get("position"),
            "salary": r.get("salary"), "projection": r.get("projected_fantasy_points"),
            "value": r.get("audit_value_per_1000"), "archetype": r.get("contest_archetype"),
        } for r in rows],
        sources=source_rows(data, ["ask_context"]),
        updated_at=(data.get("ask_context") or {}).get("generated_at"),
    )
def news_answer(question, data):
    payload = data.get("fantasy_news") or {}
    articles = list(payload.get("articles") or [])
    q = qtext(question)
    words = [w for w in re.split(r"\s+", q) if len(w) >= 4]
    matched = []
    for article in articles:
        text = f"{article.get('title', '')} {' '.join(article.get('impact_tags') or [])}".lower()
        if any(word in text for word in words):
            matched.append(article)
    rows = (matched or articles)[:8]
    if not rows:
        return answer("news", "No current article feed is available.", "WAITING", status="WAITING")
    top = rows[0]
    return answer(
        "news", top.get("title"), "REPORTING",
        why=[f"Source: {top.get('source')}"] + [f"Impact: {tag}" for tag in (top.get("impact_tags") or [])],
        risk=["Reporting can be superseded by newer official status updates."],
        cards=[{
            "type": "news", "title": r.get("title"), "source": r.get("source"),
            "url": r.get("url"), "published_at": r.get("published_at"),
            "tags": r.get("impact_tags") or [],
        } for r in rows],
        sources=source_rows(data, ["fantasy_news"]),
        updated_at=payload.get("generated_at"),
    )


def route_ask(question, data):
    q = qtext(question)
    if not q:
        return answer(
            "help",
            "Ask about scores, betting research, props, Survivor, fantasy, waivers, DFS or player news.",
            "READY",
            followups=["Best NFL bets", "Best props today", "Who should I start?", "Top waiver adds", "Survivor pick"],
            sources=source_rows(data, ["nfl_scores", "nfl_decisions", "ask_context", "fantasy_news"]),
        )

    if re.search(r"\b(score|scores|live score|who is winning|box score|game score)\b", q):
        return score_answer(question, data)
    if re.search(r"\b(parlay|two leg|2 leg)\b", q):
        return parlay_answer(data)
    if "survivor" in q:
        return survivor_answer(data)
    if re.search(r"\b(waiver|waivers|faab|free agent)\b", q):
        return waivers_answer(data)
    if re.search(r"\b(stash|ir stash|returning from ir|return window)\b", q):
        return stash_answer(data)
    if re.search(r"\b(defense stream|d/st|dst|streaming defense|defense to stream)\b", q):
        return defense_answer(data)
    if re.search(r"\b(dfs|fanduel|draftkings|lineup|daily fantasy)\b", q):
        return dfs_answer(question, data)
    if re.search(r"\b(start|sit|flex|start/sit)\b", q):
        return start_sit_answer(question, data)
    if re.search(r"\b(prop|props|passing yards|rushing yards|receiving yards|receptions|touchdown|interceptions)\b", q):
        return props_answer(question, data)
    if re.search(r"\b(best bet|best bets|moneyline|spread|total|odds|bet|pick)\b", q):
        return betting_answer(question, data)
    if re.search(r"\b(news|injury|practice|report|beat writer|player news)\b", q):
        return news_answer(question, data)
    if re.search(r"\b(mlb|baseball)\b", q):
        return score_answer(question, data)

    if player_matches(question, ask_rows(data, "weekly_fantasy")):
        return start_sit_answer(question, data)

    return answer(
        "help",
        "That question does not map to a connected data lane yet.",
        "UNKNOWN",
        why=["No connected intent matched this question."],
        risk=["The analyst will not invent an answer when the required lane is not wired."],
        followups=["Best NFL bets", "Best props", "Live scores", "Top waiver adds", "Survivor pick"],
        sources=source_rows(data, ["nfl_scores", "nfl_decisions", "ask_context", "fantasy_news"]),
        status="UNKNOWN",
    )
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIST), **kwargs)

    def log_message(self, fmt, *args):
        print(f"[commercial] {self.address_string()} {fmt % args}")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            data = load_all()
            return self.send_json(200, {
                "status": "ok",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sources": {key: bool(value) for key, value in data.items()},
            })
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/ask":
            return self.send_json(404, {"status": "NOT_FOUND"})

        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            question = clean(body.get("question") or body.get("message"))
            data = load_all()
            payload = route_ask(question, data)
            payload["question"] = question
            payload["generated_at"] = datetime.now(timezone.utc).isoformat()
            return self.send_json(200, payload)
        except Exception as exc:
            return self.send_json(400, {
                "status": "ERROR",
                "take": "The sports analyst could not process that request.",
                "error": repr(exc),
            })


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Sports Zenith commercial server listening on {PORT}")
    server.serve_forever()
