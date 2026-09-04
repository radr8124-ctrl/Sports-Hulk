"""Regression contract for the Sports HULK front end.

This is intentionally source-level. It catches the regressions that caused the
September UI loop without needing a browser or live APIs.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
APP = (ROOT / "app.py").read_text()
UI = (ROOT / "hulk_final_ui.py").read_text()
PROP = (ROOT / "prop_intelligence/hulk_prop_ui.py").read_text()


def require(cond, message):
    if not cond:
        raise AssertionError(message)


# One source of truth for dashboard routing: hulk_final_ui intercepts dashboards.
require('elif mode=="⚾ MLB": dashboard_shell(mode,rows_mlb())' in UI, "MLB dashboard must use rows_mlb only")
require('elif mode=="🏈 NFL": dashboard_shell(mode,rows_nfl())' in UI, "NFL dashboard must use rows_nfl only")
require('elif mode=="🏟️ College Football": dashboard_shell(mode,rows_cfb())' in UI, "CFB dashboard must use rows_cfb only")

# Every daily sport board must enforce the ET-date filter.
for fn in ("rows_mlb", "rows_nfl", "rows_cfb"):
    m = re.search(rf"def {fn}\(\):(?P<body>.*?)(?=\ndef |\Z)", UI, flags=re.S)
    require(m is not None, f"{fn} missing")
    require("is_today(start)" in m.group("body"), f"{fn} must filter today's ET slate")

# The old player-prop pages must not continue rendering after the new intelligence UI.
for sport in ("MLB", "NFL"):
    needle = f'render_prop_intelligence("{sport}")'
    pos = APP.find(needle)
    require(pos >= 0, f"{sport} prop intelligence call missing")
    require("st.stop()" in APP[pos:pos+140], f"{sport} old prop page must stop after intelligence renderer")

# Prop surface must be selective and must not call Hulk Prop Score a probability.
require("maximum 5" in PROP, "Prop page must cap best daily props")
require("not a calibrated win probability" in PROP, "Prop-score probability disclaimer missing")
require("No HULK EDGE qualifies right now" in PROP, "Prop page must allow a no-edge state")

# Do not fabricate hard-coded system percentages in the commercial dashboard.
require("vals=[76,69,64,61]" not in UI, "Hard-coded system performance percentages must not return")

# No college player props in the top-level navigation contract.
require("CFB Player Props" not in APP, "College player props are not supported")

print("SPORTS HULK UI CONTRACT: PASS")

# September 4 product contract: one-shop command center and league structure.
require('"MLB Dashboard"' not in APP[APP.find('elif mode == "⚾ MLB"'):APP.find('elif mode == "🏈 NFL"')], "Legacy MLB Dashboard must stay out of the MLB menu")
require('"NFL Weather"' in APP, "NFL Weather must be in NFL navigation")
require('"CFB Over / Unders"' in APP, "CFB totals page must be in CFB navigation")
require('"CFB PrizePicks"' not in APP, "College PrizePicks/player props must remain disabled")
require('"Top 300 Cheat Sheet"' in APP, "Fantasy draft board must be Top 300")
require('def command_center()' in UI and 'EVERYTHING THAT MATTERS.' in UI, "Main Sports Hulk Command Center missing")
require('def survivor_page()' in UI and 'SURVIVOR_ENTRIES.json' in UI, "Multi-entry Survivor manager missing")
require('def prizepicks_page(sport=None)' in UI, "PrizePicks Standard player-first page missing")
require('def nfl_weather_page()' in UI, "NFL weather research page missing")
require('def cfb_totals_page()' in UI, "CFB totals research page missing")
require('def top300_page()' in UI, "Top 300 Fantasy cheat sheet missing")

print("SPORTS HULK PHASE 1 PRODUCT CONTRACT: PASS")

# Phase 2 product contract: league-aware fantasy + real historical explorer.
require('def fantasy_command_center()' in UI, "Fantasy Command Center missing")
require('def active_league_context()' in UI, "Active league context helper missing")
require('def trade_finder_page()' in UI, "Trade Finder foundation missing")
require('def historical_explorer_page()' in UI, "Historical Explorer missing")
require('"Historical Explorer"' in APP, "Historical Explorer must be in Betting navigation")
require('"Trade Finder"' in APP, "Trade Finder must be in Fantasy navigation")
require('free_agents' in UI and 'roster' in UI, "League-aware roster/free-agent state missing")
require('Yahoo will use OAuth' in UI, "Yahoo OAuth architecture note missing")
require('browser-extension bridge' in UI, "ESPN extension architecture note missing")
require('does not fabricate pitch context' in UI, "Historical explorer must not invent unavailable MLB pitch context")
print("SPORTS HULK PHASE 2 PRODUCT CONTRACT: PASS")


# Phase 3 product contract: one-game research + real tracker/CLV + PrizePicks comparison.
require('"Command Center"' in APP, "Betting home must be named Command Center")
require('"Game Research"' in APP and 'def game_research_page()' in UI, "One-game deep dive missing")
require('"Bet Tracker"' in APP and 'def bet_tracker_page()' in UI, "Bet Tracker missing")
require('"Performance Lab"' in APP and 'def performance_lab_page()' in UI, "Performance Lab missing")
require('HULK_BET_TRACKER.json' in UI, "Bet tracker persistence missing")
require('def _bet_clv' in UI and 'Closing line' in UI, "CLV capture/calculation missing")
require('PRIZEPICKS × HULK RESEARCH' in UI and 'SPORTSBOOK MEDIAN' in UI, "PrizePicks sportsbook-consensus comparison missing")
require('not a calibrated win probability' in UI, "PrizePicks Hulk score disclaimer missing")
require('QUICK DEEP DIVE' in UI, "Command Center quick deep-dive actions missing")
print("SPORTS HULK PHASE 3 PRODUCT CONTRACT: PASS")

# Phase 4 final polish contract
assert "NFL Command Center" in APP, "NFL menu should use Command Center language"
assert "CFB Command Center" in APP, "CFB menu should use Command Center language"
assert "league_action_strip" in UI, "league dashboards need one-click core actions"
assert "This week's pick is already" in UI, "Survivor should warn on used-team reuse"
assert 'metric("Visible Lines"' in UI, "PrizePicks should summarize visible lines"
print("PHASE 4 CONTRACT: PASS")
