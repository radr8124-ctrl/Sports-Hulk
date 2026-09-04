from connectors.cfbd import CFBDClient
from college_logic import ratings_map, college_game_rows

c = CFBDClient(api_key="test")
assert c.connected

m = ratings_map([{"team":"A","overall":10.0},{"team":"B","overall":2.0}], "overall")
assert m["A"] == 10.0

rows = college_game_rows(
    [{"startDate":"2026-09-05T12:00:00Z","week":1,"homeTeam":"A","awayTeam":"B","homeConference":"X","awayConference":"Y"}],
    [{"team":"A","overall":10.0},{"team":"B","overall":2.0}],
    [{"team":"A","rating":8.0},{"team":"B","rating":3.0}],
)
assert rows[0]["CORE_gap_home_minus_away"] == 8.0
assert rows[0]["SRS_gap_home_minus_away"] == 5.0
print("SPORTS HULK CFBD UPDATE SELF-TEST: PASS")
