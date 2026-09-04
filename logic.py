def implied(odds):
    try:o=float(odds)
    except:return None
    return (-o)/((-o)+100) if o<0 else 100/(o+100) if o>0 else None
def event_name(e):
    t=e.get("teams") or {}
    def nm(x):
        if not isinstance(x,dict): return None
        return (x.get("names") or {}).get("long") or x.get("name")
    a=nm(t.get("away") or t.get("awayTeam"))
    h=nm(t.get("home") or t.get("homeTeam"))
    return f"{a} @ {h}" if a and h else e.get("name") or e.get("eventID","Unknown")
def event_start(e):
    for k in ("startsAt","startTime","scheduled","startDate"):
        if e.get(k): return e[k]
    return ""
def iter_odds(e):
    for oid,obj in (e.get("odds") or {}).items():
        if isinstance(obj,dict):
            for book,rec in (obj.get("byBookmaker") or {}).items():
                if isinstance(rec,dict): yield oid,book,rec
def game_rows(e):
    rows=[]
    for oid,book,rec in iter_odds(e):
        low=oid.lower()
        if any(x in low for x in ("game-ml","game-sp","game-ou","moneyline","spread","total")):
            rows.append({"event":event_name(e),"start":event_start(e),"market":oid,"book":book,"odds":rec.get("odds"),"line":rec.get("line")})
    return rows
def survivor_top5(events):
    rows=[]
    for e in events:
        probs=[]
        for oid,book,rec in iter_odds(e):
            low=oid.lower()
            if "game-ml-home" in low or ("moneyline" in low and "home" in low):
                p=implied(rec.get("odds"))
                if p is not None: probs.append((p,rec.get("odds"),book))
        if probs:
            p,o,b=max(probs,key=lambda x:x[0])
            rows.append({"event":event_name(e),"market_implied_win_pct":round(p*100,1),"best_seen_home_ml":o,"book":b,"status":"MARKET-ONLY STARTER"})
    return sorted(rows,key=lambda r:r["market_implied_win_pct"],reverse=True)[:5]
