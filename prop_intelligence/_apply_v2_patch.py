from pathlib import Path
import py_compile

ROOT=Path("/home/ubuntu/sports-hulk")
P=ROOT/"prop_intelligence"/"build_prop_intelligence.py"
if not P.exists():
    raise SystemExit("Missing prop_intelligence/build_prop_intelligence.py")
s=P.read_text()

s=s.replace(
    '"parlay_nfl": ROOT / "parlay_live" / "derived" / "NFL_PARLAY_MARKET_RAW.csv",',
    '"parlay_nfl": ROOT / "parlay_live" / "derived" / "NFL_PARLAY_MARKET_RAW.csv",\n'
    '    "parlay_mlb": ROOT / "parlay_live" / "derived" / "MLB_PARLAY_MARKET_RAW.csv",'
)

repls = {
'"passing_yards": ["player_pass_yds","player_passing_yards","passing_yards"],':
'"passing_yards": ["player_pass_yds","player_passing_yards","passing_yards","pass_yards","prophetx_player_total_passing_yards"],',
'"passing_tds": ["player_pass_tds","player_passing_tds","passing_tds"],':
'"passing_tds": ["player_pass_tds","player_passing_tds","passing_tds","passing_touchdowns","player_passing_touchdowns"],',
'"pass_completions": ["player_pass_completions","player_completions","pass_completions"],':
'"pass_completions": ["player_pass_completions","player_completions","pass_completions","passing_completions"],',
'"pass_attempts": ["player_pass_attempts","player_passing_attempts","pass_attempts"],':
'"pass_attempts": ["player_pass_attempts","player_passing_attempts","pass_attempts","passing_attempts"],',
'"interceptions": ["player_pass_interceptions","player_interceptions","interceptions"],':
'"interceptions": ["player_pass_interceptions","player_interceptions","interceptions","passing_interceptions"],',
'"rushing_yards": ["player_rush_yds","player_rushing_yards","rushing_yards"],':
'"rushing_yards": ["player_rush_yds","player_rushing_yards","rushing_yards","rush_yards"],',
'"rush_attempts": ["player_rush_attempts","player_rushing_attempts","rush_attempts"],':
'"rush_attempts": ["player_rush_attempts","player_rushing_attempts","rush_attempts","rushing_attempts"],',
'"receiving_yards": ["player_receiving_yards","player_rec_yds","player_reception_yds","receiving_yards"],':
'"receiving_yards": ["player_receiving_yards","player_rec_yds","player_reception_yds","receiving_yards","prophetx_player_total_receiving_yards"],',
'"receptions": ["player_receptions","receptions"],':
'"receptions": ["player_receptions","receptions","receiving_receptions","prophetx_player_total_receptions"],',
'"longest_reception": ["player_reception_longest","player_longest_rec","longest_reception"],':
'"longest_reception": ["player_reception_longest","player_longest_rec","longest_reception","receiving_longestreception","player_longest_reception"],',
'"rush_rec_yards": ["player_rush_reception_yds","rush_rec_yards"],':
'"rush_rec_yards": ["player_rush_reception_yds","rush_rec_yards","rushing_receiving_yards"],',
'"anytime_td": ["player_anytime_td","anytime_td"],':
'"anytime_td": ["player_anytime_td","anytime_td","player_anytime_touchdown_scorer","player_anytime_touchdowns"],',
'"total_bases": ["player_total_bases","batter_total_bases","total_bases"],':
'"total_bases": ["player_total_bases","batter_total_bases","total_bases","batting_totalbases"],',
'"hits": ["player_hits","batter_hits","hits"],':
'"hits": ["player_hits","batter_hits","hits","batting_hits"],',
'"home_runs": ["player_home_runs","batter_home_runs","home_runs"],':
'"home_runs": ["player_home_runs","batter_home_runs","home_runs","batting_homeruns"],',
'"rbis": ["player_rbis","batter_rbis","rbis"],':
'"rbis": ["player_rbis","batter_rbis","rbis","batting_rbi"],',
'"walks": ["player_walks","player_bat_walks","batter_walks","walks"],':
'"walks": ["player_walks","player_bat_walks","batter_walks","walks","batting_basesonballs"],',
'"singles": ["player_singles","batter_singles","singles"],':
'"singles": ["player_singles","batter_singles","singles","batting_singles"],',
'"doubles": ["player_doubles","batter_doubles","doubles"],':
'"doubles": ["player_doubles","batter_doubles","doubles","batting_doubles"],',
'"triples": ["player_triples","batter_triples","triples"],':
'"triples": ["player_triples","batter_triples","triples","batting_triples"],',
'"stolen_bases": ["player_stolen_bases","batter_stolen_bases","stolen_bases"],':
'"stolen_bases": ["player_stolen_bases","batter_stolen_bases","stolen_bases","batting_stolenbases"],',
'"hits_runs_rbis": ["player_hits_runs_rbis","batter_hits_runs_rbis","hits_runs_rbis"],':
'"hits_runs_rbis": ["player_hits_runs_rbis","batter_hits_runs_rbis","hits_runs_rbis","batting_hits_runs_rbi"],',
}
for a,b in repls.items():
    s=s.replace(a,b)

# Insert extra valid categories before anytime_td
if '"longest_rush":' not in s:
    needle='        "anytime_td": '
    idx=s.find(needle)
    if idx!=-1:
        extra=(
'        "longest_rush": ["rushing_longestrush","longest_rush","player_longest_rush"],\n'
'        "receiving_tds": ["rec_tds","receiving_tds","player_receiving_touchdowns"],\n'
'        "receiving_targets": ["rec_targets","receiving_targets","player_receiving_targets"],\n'
'        "pass_rush_yards": ["passing_rushing_yards","player_pass_rush_yards"],\n'
'        "sacks": ["sacks","player_sacks"],\n'
'        "field_goals_made": ["fieldgoals_made","field_goals_made","player_field_goal_made"],\n'
'        "kicking_points": ["kicking_totalpoints","kicking_points","player_kicking_points"],\n'
)
        s=s[:idx]+extra+s[idx:]

if '"runs_rbis":' not in s:
    needle='        "hits_runs_rbis": '
    idx=s.find(needle)
    if idx!=-1:
        extra=(
'        "runs_rbis": ["batting_runs_rbi","player_runs_rbis"],\n'
'        "batter_strikeouts": ["batting_strikeouts","batter_strikeouts"],\n'
)
        s=s[:idx]+extra+s[idx:]

# Canonical compact aliases for plus-separated provider labels.
old='def canonical_market(sport, raw):\n    r = normalize_name(raw).replace(" ","_")\n'
new='def canonical_market(sport, raw):\n    r = normalize_name(raw).replace(" ","_")\n    compact_aliases = {"batting_hits_runs_rbi":"hits_runs_rbis","batting_runs_rbi":"runs_rbis","rushing_receiving_yards":"rush_rec_yards","passing_rushing_yards":"pass_rush_yards"}\n    if r in compact_aliases:\n        return compact_aliases[r], None\n'
s=s.replace(old,new)

old='    n,r=normalize_provider(raw["parlay_nfl"],"NFL","PARLAY_NFL",sportsbook_only=True);normalized.append(n);rejects.append(r)\n'
new='    n,r=normalize_provider(raw["parlay_nfl"],"NFL","PARLAY_NFL",sportsbook_only=True);normalized.append(n);rejects.append(r)\n    n,r=normalize_provider(raw["parlay_mlb"],"MLB","PARLAY_MLB",sportsbook_only=True);normalized.append(n);rejects.append(r)\n'
s=s.replace(old,new)

s=s.replace(
'    sportsbook=all_norm[all_norm["source"].eq("PARLAY_NFL")].copy() if not all_norm.empty else pd.DataFrame()\n',
'    sportsbook=all_norm[all_norm["source"].isin(["PARLAY_NFL","PARLAY_MLB"])].copy() if not all_norm.empty else pd.DataFrame()\n'
)

s=s.replace(
'    print(f"Parlay NFL raw:       {len(raw[\'parlay_nfl\']):,}")\n',
'    print(f"Parlay NFL raw:       {len(raw[\'parlay_nfl\']):,}")\n    print(f"Parlay MLB raw:       {len(raw[\'parlay_mlb\']):,}")\n'
)

P.write_text(s)
py_compile.compile(str(P), doraise=True)
print("PROP INTELLIGENCE V2 PATCH: COMPILE PASS")
