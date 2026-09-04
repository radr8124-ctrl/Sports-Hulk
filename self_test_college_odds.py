from odds_merge import normalize_team, merge_college_rows, find_match

rows=[{
    "start":"2026-09-01",
    "away":"North Carolina",
    "home":"TCU",
    "CORE_gap_home_minus_away": 3.2,
    "SRS_gap_home_minus_away": 2.7,
}]
odds=[{
    "id":"abc",
    "home_team":"TCU Horned Frogs",
    "away_team":"North Carolina Tar Heels",
    "commence_time":"2026-09-01T20:00:00Z",
    "bookmakers":[{
        "title":"Book",
        "markets":[
            {"key":"h2h","outcomes":[
                {"name":"TCU Horned Frogs","price":-130},
                {"name":"North Carolina Tar Heels","price":110},
            ]},
            {"key":"spreads","outcomes":[
                {"name":"TCU Horned Frogs","price":-110,"point":-2.5},
                {"name":"North Carolina Tar Heels","price":-110,"point":2.5},
            ]},
            {"key":"totals","outcomes":[
                {"name":"Over","price":-110,"point":51.5},
                {"name":"Under","price":-110,"point":51.5},
            ]},
        ],
    }],
}]

m, score = find_match("TCU", "North Carolina", odds)
assert m is not None, f"match failed, score={score}"

merged=merge_college_rows(rows,odds)
assert merged[0]["Odds_matched"] is True
assert merged[0]["Home_spread"] == -2.5
assert merged[0]["Total"] == 51.5
assert merged[0]["Home_moneyline"] == -130
assert merged[0]["Away_moneyline"] == 110

print("SPORTS HULK COLLEGE ODDS HOTFIX SELF-TEST: PASS")
print("Sample matchup score:", merged[0]["Odds_match_score"])
