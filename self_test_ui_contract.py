from pathlib import Path

ROOT = Path(__file__).resolve().parent

APP_FILE = ROOT / "app.py"
UI_FILE = ROOT / "hulk_final_ui.py"

APP = APP_FILE.read_text(encoding="utf-8")
UI = UI_FILE.read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


# ============================================================
# CORE FILE / ROUTING CONTRACT
# ============================================================

require(
    "render_dashboard_boost(mode, page)" in APP,
    "app.py must route dashboard rendering through hulk_final_ui",
)

require(
    "render_hulk_feature_page(mode, page)" in APP,
    "app.py must route feature pages through hulk_final_ui",
)

require(
    "def dashboard(" in UI,
    "hulk_final_ui.py must define dashboard()",
)

require(
    "def command_center(" in UI,
    "hulk_final_ui.py must define command_center()",
)


# ============================================================
# APPROVED COMMAND CENTER V2 CONTRACT
# ============================================================

required_command_center_markers = [
    "mock-hero",
    "mock-kpis",
    "mock-grid",
    "MARKET MOVEMENT",
    "HULK VS MARKET",
    "PLAYER PROPS SPOTLIGHT",
    "PARLAY CHEMISTRY",
    "PRIZEPICKS BOARD",
    "FANTASY / WAIVER WIRE",
    "QUICK DEEP DIVE",
]

for marker in required_command_center_markers:
    require(
        marker in UI,
        f"Approved Command Center V2 marker missing: {marker}",
    )


# ============================================================
# SPORTS / PRODUCT NAVIGATION CONTRACT
# ============================================================

required_app_pages = [
    "Command Center",
    "Game Research",
    "Bet Tracker",
    "Performance Lab",
    "Historical Explorer",
    "MLB PrizePicks",
    "NFL Weather",
    "CFB Over / Unders",
    "Top 300 Cheat Sheet",
]

for page in required_app_pages:
    require(
        page in APP,
        f"Required Sports HULK page missing from app.py: {page}",
    )


# ============================================================
# CFB GOVERNANCE
# ============================================================

require(
    "College Football" in APP,
    "College Football navigation must remain available",
)

require(
    "CFB" in UI,
    "CFB UI support must remain available",
)

# College football player props are intentionally unsupported.
require(
    "CFB Player Props" not in APP,
    "College Football must not expose player props",
)


# ============================================================
# MLB CONTRACT
# ============================================================

require(
    "MLB PrizePicks" in APP,
    "MLB PrizePicks must remain inside the MLB experience",
)

require(
    "MLB Best Bets" in APP,
    "MLB Best Bets page must remain available",
)


# ============================================================
# NFL CONTRACT
# ============================================================

require(
    "NFL Best Bets" in APP,
    "NFL Best Bets page must remain available",
)

require(
    "Survivor" in APP,
    "NFL Survivor must remain available",
)


# ============================================================
# FANTASY CONTRACT
# ============================================================

require(
    "Top 300 Cheat Sheet" in APP,
    "Fantasy Top 300 Cheat Sheet must remain available",
)

require(
    "My Leagues" in APP or "My Leagues" in UI,
    "Fantasy multi-league support must remain available",
)


# ============================================================
# RESEARCH / CLAIM GUARDRAILS
# ============================================================

require(
    "not a calibrated" in UI.lower(),
    "Prop score must remain clearly labeled as non-calibrated",
)

require(
    "No college player props" in UI
    or "no college player props" in UI.lower()
    or "CFB Player Props" not in APP,
    "CFB must not imply unsupported college player props",
)


print("========================================")
print("SPORTS HULK UI CONTRACT: PASS")
print("Approved Command Center V2 verified")
print("Core routing verified")
print("MLB / NFL / CFB / Fantasy guardrails verified")
print("========================================")
