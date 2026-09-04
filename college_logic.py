from datetime import datetime, timezone

def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def upcoming_games(games, days_back=1, days_forward=10):
    now = datetime.now(timezone.utc)
    out = []
    for g in games or []:
        dt = _parse_dt(g.get("startDate") or g.get("startTime"))
        if dt is None:
            continue
        delta = (dt - now).total_seconds() / 86400.0
        if -days_back <= delta <= days_forward:
            out.append(g)
    return sorted(out, key=lambda g: g.get("startDate") or "")

def ratings_map(rows, key_name="overall"):
    out = {}
    for r in rows or []:
        team = r.get("team")
        if not team:
            continue
        value = r.get(key_name)
        if value is None and key_name == "overall":
            value = r.get("rating")
        out[team] = value
    return out

def college_game_rows(games, core_rows=None, srs_rows=None):
    core = ratings_map(core_rows or [], "overall")
    srs = ratings_map(srs_rows or [], "rating")
    rows = []
    for g in games or []:
        home = g.get("homeTeam")
        away = g.get("awayTeam")
        h_core, a_core = core.get(home), core.get(away)
        h_srs, a_srs = srs.get(home), srs.get(away)
        core_gap = round(float(h_core) - float(a_core), 2) if h_core is not None and a_core is not None else None
        srs_gap = round(float(h_srs) - float(a_srs), 2) if h_srs is not None and a_srs is not None else None
        rows.append({
            "start": g.get("startDate"),
            "week": g.get("week"),
            "away": away,
            "home": home,
            "away_conf": g.get("awayConference"),
            "home_conf": g.get("homeConference"),
            "neutral": g.get("neutralSite"),
            "venue": g.get("venue"),
            "home_CORE": h_core,
            "away_CORE": a_core,
            "CORE_gap_home_minus_away": core_gap,
            "home_SRS": h_srs,
            "away_SRS": a_srs,
            "SRS_gap_home_minus_away": srs_gap,
        })
    return rows
