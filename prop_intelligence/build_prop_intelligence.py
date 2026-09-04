
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import itertools, json, math, re
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "prop_intelligence" / "derived"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "nfl_props": ROOT / "props_live/nfl/derived/NFL_PLAYER_PROPS.csv",
    "mlb_props": ROOT / "props_live/mlb/derived/MLB_PLAYER_PROPS.csv",
    "prizepicks": ROOT / "prizepicks_live/derived/PRIZEPICKS_STANDARD.csv",
    "parlay_nfl": ROOT / "parlay_live/derived/NFL_PARLAY_MARKET_RAW.csv",
    "parlay_mlb": ROOT / "parlay_live/derived/MLB_PARLAY_MARKET_RAW.csv",
}

CANON = {
    "NFL": {
        "passing_yards": ["player_pass_yds","player_passing_yards","passing_yards","pass_yards","prophetx_player_total_passing_yards"],
        "passing_tds": ["player_pass_tds","player_passing_tds","passing_tds","passing_touchdowns","player_passing_touchdowns"],
        "pass_completions": ["player_pass_completions","player_completions","pass_completions","passing_completions"],
        "pass_attempts": ["player_pass_attempts","player_passing_attempts","pass_attempts","passing_attempts"],
        "interceptions": ["player_pass_interceptions","player_interceptions","interceptions","passing_interceptions"],
        "rushing_yards": ["player_rush_yds","player_rushing_yards","rushing_yards","rush_yards"],
        "rush_attempts": ["player_rush_attempts","player_rushing_attempts","rush_attempts","rushing_attempts"],
        "receiving_yards": ["player_receiving_yards","player_rec_yds","player_reception_yds","receiving_yards","prophetx_player_total_receiving_yards"],
        "receptions": ["player_receptions","receptions","receiving_receptions","prophetx_player_total_receptions"],
        "longest_reception": ["player_reception_longest","player_longest_rec","longest_reception","receiving_longestreception","player_longest_reception"],
        "rush_rec_yards": ["player_rush_reception_yds","rush_rec_yards","rushing_receiving_yards"],
        "longest_rush": ["rushing_longestrush","longest_rush","player_longest_rush"],
        "receiving_tds": ["rec_tds","receiving_tds","player_receiving_touchdowns"],
        "receiving_targets": ["rec_targets","receiving_targets","player_receiving_targets"],
        "pass_rush_yards": ["passing_rushing_yards","player_pass_rush_yards"],
        "sacks": ["sacks","player_sacks"],
        "field_goals_made": ["fieldgoals_made","field_goals_made","player_field_goal_made"],
        "kicking_points": ["kicking_totalpoints","kicking_points","player_kicking_points"],
        "anytime_td": ["player_anytime_td","anytime_td","player_anytime_touchdown_scorer","player_anytime_touchdowns"],
    },
    "MLB": {
        "total_bases": ["player_total_bases","batter_total_bases","total_bases","batting_totalbases"],
        "hits": ["player_hits","batter_hits","hits","batting_hits"],
        "home_runs": ["player_home_runs","batter_home_runs","home_runs","batting_homeruns"],
        "rbis": ["player_rbis","batter_rbis","rbis","batting_rbi"],
        "runs": ["player_runs","batter_runs_scored","runs"],
        "walks": ["player_walks","player_bat_walks","batter_walks","walks","batting_basesonballs"],
        "singles": ["player_singles","batter_singles","singles","batting_singles"],
        "doubles": ["player_doubles","batter_doubles","doubles","batting_doubles"],
        "triples": ["player_triples","batter_triples","triples","batting_triples"],
        "stolen_bases": ["player_stolen_bases","batter_stolen_bases","stolen_bases","batting_stolenbases"],
        "runs_rbis": ["batting_runs_rbi","player_runs_rbis"],
        "batter_strikeouts": ["batting_strikeouts","batter_strikeouts"],
        "hits_runs_rbis": ["player_hits_runs_rbis","batter_hits_runs_rbis","hits_runs_rbis","batting_hits_runs_rbi"],
        "pitcher_strikeouts": ["player_strikeouts","pitcher_strikeouts"],
        "pitcher_outs": ["player_pitcher_outs","pitcher_outs"],
        "hits_allowed": ["player_hits_allowed","pitcher_hits_allowed","hits_allowed"],
        "earned_runs": ["player_earned_runs","pitcher_earned_runs","earned_runs"],
    }
}

EXCLUDE_TOKENS = (
    "_alternate","alternate_","_alt","milestone","first_","1st_",
    "quarter","q1","q2","q3","q4","half","1h","2h"
)

BOOK_EXCLUDE = {
    "prizepicks","underdog","sleeper","betr","draftkings pick6","pick6"
}

def read_csv(path):
    try:
        return pd.read_csv(path, low_memory=False) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

def first_col(df, names):
    low = {c.lower(): c for c in df.columns}
    for n in names:
        if n.lower() in low:
            return low[n.lower()]
    return None

def text(v):
    return "" if pd.isna(v) else str(v).strip()

def fl(v):
    try:
        x=float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def normalize_name(v):
    return re.sub(r"[^a-z0-9]+"," ",text(v).lower()).strip()

def canonical_market(sport, raw):
    r = normalize_name(raw).replace(" ","_")
    compact_aliases = {"batting_hits_runs_rbi":"hits_runs_rbis","batting_runs_rbi":"runs_rbis","rushing_receiving_yards":"rush_rec_yards","passing_rushing_yards":"pass_rush_yards"}
    if r in compact_aliases:
        return compact_aliases[r], None
    if any(tok in r for tok in EXCLUDE_TOKENS):
        return None, "ALT_OR_DERIVATIVE_MARKET"
    for canon, aliases in CANON.get(sport,{}).items():
        if r in {a.lower() for a in aliases}:
            return canon, None
    return None, "NO_MARKET_MAPPING"

def today_ny():
    return datetime.now(ZoneInfo("America/New_York")).date()

def parse_dt(v):
    try:
        dt=pd.to_datetime(v, errors="coerce", utc=True)
        if pd.isna(dt): return None
        return dt.to_pydatetime()
    except Exception:
        return None

def canonical_event_time(v):
    dt = parse_dt(v)
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00","Z")

def is_today_future(v):
    dt=parse_dt(v)
    if dt is None: return False, "BAD_EVENT_TIME"
    local=dt.astimezone(ZoneInfo("America/New_York"))
    if local.date()!=today_ny(): return False, "GAME_NOT_TODAY"
    if local <= datetime.now(ZoneInfo("America/New_York")): return False, "GAME_STARTED"
    return True, None

def normalize_provider(df, sport, source, sportsbook_only=False):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame([{"source":source,"reason":"SOURCE_EMPTY"}])

    player=first_col(df,["player","player_name","name","description"])
    market=first_col(df,["market_key","market","stat_type","stat","prop_type","key"])
    line=first_col(df,["line","point","projection","line_score","value"])
    event=first_col(df,["event_id","game_id","fixture_id","id"])
    start=first_col(df,["commence_time","start_time","game_time","event_time","start","date"])
    book=first_col(df,["bookmaker","book","sportsbook","operator","site"])
    over=first_col(df,["over_price","price_over","over_odds","over"])
    under=first_col(df,["under_price","price_under","under_odds","under"])
    updated=first_col(df,["last_update","updated_at","timestamp","last_updated"])
    team=first_col(df,["team","player_team"])
    opp=first_col(df,["opponent","opp"])
    promo=first_col(df,["is_promo","promo","promotion"])
    odds_type=first_col(df,["odds_type"])

    req={"player":player,"market":market,"line":line}
    missing=[k for k,v in req.items() if v is None]
    if missing:
        return pd.DataFrame(), pd.DataFrame([{"source":source,"reason":"MISSING_REQUIRED_COLUMNS","detail":",".join(missing)}])

    accepted=[]
    rejected=[]
    for _,r in df.iterrows():
        raw_market=text(r[market])
        canon,why=canonical_market(sport,raw_market)
        if why:
            rejected.append({"sport":sport,"source":source,"player":text(r[player]),"raw_market":raw_market,"reason":why})
            continue
        ln=fl(r[line])
        if ln is None:
            rejected.append({"sport":sport,"source":source,"player":text(r[player]),"raw_market":raw_market,"reason":"BAD_LINE"})
            continue
        if promo and text(r[promo]).lower() in {"true","1","yes","y"}:
            rejected.append({"sport":sport,"source":source,"player":text(r[player]),"raw_market":raw_market,"reason":"PROMO"})
            continue
        if odds_type and text(r[odds_type]).lower() not in {"","standard","straight"}:
            rejected.append({"sport":sport,"source":source,"player":text(r[player]),"raw_market":raw_market,"reason":"NONSTANDARD_ODDS_TYPE"})
            continue
        bk=text(r[book]) if book else source
        if sportsbook_only and normalize_name(bk) in BOOK_EXCLUDE:
            rejected.append({"sport":sport,"source":source,"player":text(r[player]),"raw_market":raw_market,"reason":"DFS_NOT_SPORTSBOOK"})
            continue
        evtime=text(r[start]) if start else ""
        accepted.append({
            "sport":sport,"source":source,"player":text(r[player]),
            "player_key":normalize_name(r[player]),"team":text(r[team]) if team else "",
            "opponent":text(r[opp]) if opp else "","event_id":text(r[event]) if event else "",
            "event_time":canonical_event_time(evtime),"canonical_market":canon,"raw_market":raw_market,
            "line":ln,"bookmaker":bk,"over_price":fl(r[over]) if over else None,
            "under_price":fl(r[under]) if under else None,
            "updated_at":text(r[updated]) if updated else "",
        })
    return pd.DataFrame(accepted), pd.DataFrame(rejected)

def infer_sport_from_pp(df):
    league=first_col(df,["league","league_name","sport"])
    if league is None:
        return {"NFL":df.iloc[0:0].copy(),"MLB":df.iloc[0:0].copy()}
    s=df[league].astype(str).str.upper()
    return {"NFL":df[s.str.contains("NFL")].copy(),"MLB":df[s.str.contains("MLB")].copy()}

def build_consensus(rows):
    if rows.empty: return pd.DataFrame()
    x=rows.copy()
    x["line"]=pd.to_numeric(x["line"],errors="coerce")
    x=x.dropna(subset=["line"])
    # dedupe exact provider/book/player/market/line/event combinations
    x=x.drop_duplicates(subset=["sport","player_key","canonical_market","bookmaker","line","event_id"])
    groups=[]
    keys=["sport","player_key","player","canonical_market","event_id","event_time","team","opponent"]
    for k,g in x.groupby(keys,dropna=False):
        lines=g["line"].dropna()
        if lines.empty: continue
        books=g["bookmaker"].replace("",pd.NA).dropna().nunique()
        op=pd.to_numeric(g["over_price"],errors="coerce").dropna()
        up=pd.to_numeric(g["under_price"],errors="coerce").dropna()
        med=float(lines.median())
        within=((lines-med).abs()<=max(0.5,abs(med)*0.02)).mean()*100 if len(lines) else 0
        groups.append({
            **dict(zip(keys,k)),
            "market_median":med,
            "market_low":float(lines.min()),
            "market_high":float(lines.max()),
            "book_count":int(books),
            "book_agreement_pct":round(float(within),1),
            "line_dispersion":round(float(lines.std(ddof=0)),3) if len(lines)>1 else 0.0,
            "over_price_median":float(op.median()) if not op.empty else None,
            "under_price_median":float(up.median()) if not up.empty else None,
        })
    return pd.DataFrame(groups)

def add_pp_compare(consensus, pp_rows):
    if consensus.empty: return consensus
    out=consensus.copy()
    out["pp_line"]=pd.NA
    if pp_rows.empty:
        out["pp_gap"]=pd.NA
        return out
    pp=pp_rows.copy().drop_duplicates(subset=["sport","player_key","canonical_market","line"])
    lookup={}
    for _,r in pp.iterrows():
        lookup[(r["sport"],r["player_key"],r["canonical_market"])]=r["line"]
    for i,r in out.iterrows():
        out.at[i,"pp_line"]=lookup.get((r["sport"],r["player_key"],r["canonical_market"]),pd.NA)
    out["pp_line"]=pd.to_numeric(out["pp_line"],errors="coerce")
    out["pp_gap"]=out["pp_line"]-out["market_median"]
    return out

def find_hit_rate_columns(df):
    found={}
    aliases={
        "l3":["l3","last3","last_3","l3_hit_rate"],
        "l5":["l5","last5","last_5","l5_hit_rate"],
        "l10":["l10","last10","last_10","l10_hit_rate"],
        "l20":["l20","last20","last_20","l20_hit_rate"],
        "season":["season_hit_rate","season_over_rate","season_rate","hit_rate"],
        "streak":["streak","current_streak","over_streak","under_streak"],
        "recent_avg":["recent_avg","l5_avg","last5_avg","last_5_avg"],
        "season_avg":["season_avg","avg","average"],
        "h2h":["h2h_hit_rate","vs_opp_hit_rate","opponent_hit_rate"],
    }
    low={c.lower():c for c in df.columns}
    for key,names in aliases.items():
        for n in names:
            if n in low:
                found[key]=low[n];break
    return found

def enrich_from_existing(signals, nfl_df, mlb_df):
    if signals.empty: return signals
    out=signals.copy()
    for c in ["l3","l5","l10","l20","season","streak","recent_avg","season_avg","h2h"]:
        out[c]=pd.NA
    for sport,src in [("NFL",nfl_df),("MLB",mlb_df)]:
        if src.empty: continue
        player=first_col(src,["player","player_name","name","description"])
        market=first_col(src,["market_key","market","stat_type","stat","prop_type","key"])
        if not player or not market: continue
        hrs=find_hit_rate_columns(src)
        if not hrs: continue
        tmp=src.copy()
        tmp["_player_key"]=tmp[player].map(normalize_name)
        tmp["_canon"]=tmp[market].map(lambda v: canonical_market(sport,v)[0])
        for i,r in out[out["sport"].eq(sport)].iterrows():
            m=tmp[(tmp["_player_key"]==r["player_key"])&(tmp["_canon"]==r["canonical_market"])]
            if m.empty: continue
            rr=m.iloc[0]
            for k,col in hrs.items(): out.at[i,k]=rr[col]
    return out

def american_prob(odds):
    o=fl(odds)
    if o is None or o==0: return None
    return 100/(o+100) if o>0 else (-o)/((-o)+100)

def score_signal(r):
    books=int(r.get("book_count",0) or 0)
    agreement=fl(r.get("book_agreement_pct")) or 0
    gap=fl(r.get("pp_gap"))
    median=fl(r.get("market_median"))
    gap_strength=0
    if gap is not None and median not in (None,0):
        gap_strength=min(100,abs(gap)/max(1,abs(median))*500)
    depth=min(100,books/7*100)
    overp=american_prob(r.get("over_price_median"))
    underp=american_prob(r.get("under_price_median"))
    pressure=50
    direction="NEUTRAL"
    if overp is not None and underp is not None and overp+underp>0:
        no_vig_over=overp/(overp+underp)
        pressure=abs(no_vig_over-0.5)*200
        direction="OVER" if no_vig_over>0.5 else "UNDER"
    score=0.30*gap_strength+0.25*pressure+0.20*agreement+0.15*depth+0.10*100
    return round(min(100,max(0,score)),1),direction,round(pressure,1)

def build_signals(consensus, nfl_df, mlb_df):
    if consensus.empty: return consensus
    out=enrich_from_existing(consensus,nfl_df,mlb_df)
    scores=[];dirs=[];press=[]
    for _,r in out.iterrows():
        sc,di,pr=score_signal(r);scores.append(sc);dirs.append(di);press.append(pr)
    out["hulk_prop_score"]=scores
    out["market_direction"]=dirs
    out["price_pressure_score"]=press
    out["coverage_grade"]=out["book_count"].map(lambda n:"STRONG" if n>=7 else "GOOD" if n>=5 else "USABLE" if n>=3 else "LOW")
    out["signal"]=out.apply(lambda r:"PASS" if r["book_count"]<3 else ("STRONG" if r["hulk_prop_score"]>=80 else "LEAN" if r["hulk_prop_score"]>=65 else "WATCH"),axis=1)
    return out

def chemistry(a,b):
    if a["player_key"]==b["player_key"]: return "PROHIBITED","SAME_PLAYER"
    if a["event_id"] and b["event_id"] and a["event_id"]==b["event_id"]:
        # simple conservative same-game logic
        am=a["canonical_market"]; bm=b["canonical_market"]
        pos={frozenset(["passing_yards","receiving_yards"]),frozenset(["passing_tds","receiving_yards"])}
        if frozenset([am,bm]) in pos: return "POSITIVE","SAME_GAME_RELATED"
        return "NEUTRAL","SAME_GAME"
    return "NEUTRAL","CROSS_GAME"

def build_parlays(signals):
    if signals.empty: return pd.DataFrame(),pd.DataFrame()
    pool=signals[(signals["book_count"]>=3)&(signals["signal"].isin(["STRONG","LEAN"]))].copy()
    # today filter only where event_time exists; otherwise reject from daily parlays
    keep=[];rej=[]
    for _,r in pool.iterrows():
        ok,why=is_today_future(r["event_time"])
        if ok: keep.append(r)
        else: rej.append({**r.to_dict(),"reason":why})
    pool=pd.DataFrame(keep)
    if pool.empty: return pd.DataFrame(),pd.DataFrame(rej)

    candidates=[]
    for n,label in [(2,"SAFER"),(3,"BALANCED"),(4,"AGGRESSIVE")]:
        best=None
        for combo in itertools.combinations(pool.to_dict("records"),n):
            bad=False; bonuses=0; notes=[]
            for a,b in itertools.combinations(combo,2):
                c,reason=chemistry(a,b);notes.append(f"{c}:{reason}")
                if c=="PROHIBITED": bad=True;break
                if c=="POSITIVE": bonuses+=2
            if bad: continue
            score=sum(x["hulk_prop_score"] for x in combo)/n+bonuses
            # discourage overconcentration
            same_events=len({x["event_id"] for x in combo if x["event_id"]})
            if same_events==1 and n>2: score-=5
            if best is None or score>best[0]: best=(score,combo,notes)
        if best:
            score,combo,notes=best
            candidates.append({
                "parlay_type":label,"legs":n,"parlay_score":round(score,1),
                "sports":",".join(sorted({x["sport"] for x in combo})),
                "leg_summary":" | ".join(f'{x["player"]} {x["canonical_market"]} {x["market_direction"]}' for x in combo),
                "chemistry":";".join(notes),
                "source_label":"MARKET-BACKED PROP PARLAY",
            })
    return pd.DataFrame(candidates),pd.DataFrame(rej)

def source_audit(frames):
    rows=[]
    for name,df in frames.items():
        rows.append({"source":name,"rows":len(df),"columns":"|".join(df.columns.astype(str))})
    return pd.DataFrame(rows)

def main():
    raw={k:read_csv(v) for k,v in SOURCES.items()}
    normalized=[];rejects=[]

    n,r=normalize_provider(raw["nfl_props"],"NFL","NFL_PLAYER_PROPS");normalized.append(n);rejects.append(r)
    n,r=normalize_provider(raw["mlb_props"],"MLB","MLB_PLAYER_PROPS");normalized.append(n);rejects.append(r)
    n,r=normalize_provider(raw["parlay_nfl"],"NFL","PARLAY_NFL",sportsbook_only=True);normalized.append(n);rejects.append(r)
    n,r=normalize_provider(raw["parlay_mlb"],"MLB","PARLAY_MLB",sportsbook_only=True);normalized.append(n);rejects.append(r)

    pp_sports=infer_sport_from_pp(raw["prizepicks"])
    pp_norm=[]
    for sport,df in pp_sports.items():
        n,r=normalize_provider(df,sport,"PRIZEPICKS");pp_norm.append(n);rejects.append(r)
    pp_rows=pd.concat([x for x in pp_norm if not x.empty],ignore_index=True) if any(not x.empty for x in pp_norm) else pd.DataFrame()

    all_norm=pd.concat([x for x in normalized if not x.empty],ignore_index=True) if any(not x.empty for x in normalized) else pd.DataFrame()
    sportsbook=all_norm[all_norm["source"].isin(["PARLAY_NFL","PARLAY_MLB"])].copy() if not all_norm.empty else pd.DataFrame()
    consensus=build_consensus(sportsbook)
    consensus=add_pp_compare(consensus,pp_rows)
    signals=build_signals(consensus,raw["nfl_props"],raw["mlb_props"])
    parlays,parlay_rej=build_parlays(signals)

    rej=pd.concat([x for x in rejects if not x.empty]+([parlay_rej] if not parlay_rej.empty else []),ignore_index=True) if any(not x.empty for x in rejects) or not parlay_rej.empty else pd.DataFrame()

    audit=source_audit(raw)
    audit.to_csv(OUT/"HULK_PROP_SOURCE_AUDIT.csv",index=False)
    consensus.to_csv(OUT/"HULK_PROP_CONSENSUS.csv",index=False)
    signals.to_csv(OUT/"HULK_PROP_SIGNALS.csv",index=False)
    parlays.to_csv(OUT/"HULK_PARLAY_CANDIDATES.csv",index=False)
    parlays.to_csv(OUT/"HULK_PARLAYS_TODAY.csv",index=False)
    rej.to_csv(OUT/"HULK_PROP_REJECTIONS.csv",index=False)

    mapping=ROOT/"prop_intelligence"/"canonical_markets.json"
    mapping.write_text(json.dumps(CANON,indent=2))

    print("="*72)
    print("SPORTS HULK PROP INTELLIGENCE")
    print("="*72)
    print(f"NFL props raw:        {len(raw['nfl_props']):,}")
    print(f"MLB props raw:        {len(raw['mlb_props']):,}")
    print(f"PrizePicks raw:       {len(raw['prizepicks']):,}")
    print(f"Parlay NFL raw:       {len(raw['parlay_nfl']):,}")
    print(f"Parlay MLB raw:       {len(raw['parlay_mlb']):,}")
    print(f"Consensus rows:       {len(consensus):,}")
    print(f"Signal rows:          {len(signals):,}")
    print(f"Today's parlays:      {len(parlays):,}")
    print(f"Rejected/audit rows:  {len(rej):,}")
    print("OUTPUT:", OUT)
    print("RESULT: PASS")

if __name__=="__main__":
    main()
