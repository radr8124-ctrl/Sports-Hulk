#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json
import math
import re
import pandas as pd

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "intelligence_warehouse" / "schedule"
LOAD_OUT = OUT / "TEAM_SCHEDULE_LOAD_CURRENT.csv"
SOS_OUT = OUT / "FUTURE_SCHEDULE_DIFFICULTY.csv"
ENV_OUT = OUT / "GAME_ENVIRONMENT_CURRENT.csv"
CATALOG_OUT = OUT / "SCHEDULE_FEATURE_CATALOG.csv"
RECEIPT = OUT / "SCHEDULE_INTELLIGENCE_RECEIPT.json"
ASOF = pd.Timestamp.now(tz="UTC")
TODAY = ASOF.normalize()
NOW = datetime.now(timezone.utc).isoformat()

def read(path):
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()

def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return re.sub(r"\s+", " ", str(v).strip())

def truthy(v):
    return str(v).strip().lower() in {"true","1","yes","y","final","off"}

def number(v):
    try:
        x = float(v)
        return None if math.isnan(x) else x
    except Exception:
        return None

def id_text(v):
    x = number(v)
    return str(int(x)) if x is not None else clean(v)

def day(v):
    try:
        return pd.to_datetime(v, utc=True).normalize()
    except Exception:
        return pd.NaT

def add_pair(rows, sport, game_id, game_date, away, home, away_name="",
             home_name="", completed=False, away_score=None, home_score=None,
             game_type="", **env):
    gd = day(game_date)
    if pd.isna(gd) or not clean(away) or not clean(home):
        return
    base = dict(sport=sport, game_id=clean(game_id), game_date=gd,
                completed=bool(completed), game_type=clean(game_type), **env)
    rows.append({
        **base, "team":clean(away), "team_name":clean(away_name) or clean(away),
        "opponent":clean(home), "opponent_name":clean(home_name) or clean(home),
        "side":"AWAY", "team_score":number(away_score), "opp_score":number(home_score)
    })
    rows.append({
        **base, "team":clean(home), "team_name":clean(home_name) or clean(home),
        "opponent":clean(away), "opponent_name":clean(away_name) or clean(away),
        "side":"HOME", "team_score":number(home_score), "opp_score":number(away_score)
    })

def nfl_rows(rows):
    d = read(ROOT/"nfl_live/derived/NFLVERSE_2026_SCHEDULE.csv")
    ctx = read(ROOT/"nfl_live/derived/NFL_SURVIVOR_HULK_CONTEXT.csv")
    context = {}
    if not ctx.empty and "espn_event_id" in ctx:
        for _, r in ctx.iterrows():
            context[id_text(r.get("espn_event_id"))] = r
    for _, r in d.iterrows():
        if number(r.get("season")) != 2026:
            continue
        c = context.get(id_text(r.get("espn")))
        roof = clean(r.get("roof")).lower()
        indoor = roof in {"dome","closed"}
        wstatus = "INDOOR" if indoor else "SCHEDULE_ONLY"
        env = dict(
            venue=clean(r.get("stadium")), venue_city="", venue_state="",
            environment_type="INDOOR" if indoor else "OUTDOOR",
            weather_status=wstatus, temperature_f=number(r.get("temp")),
            precipitation_in=None, precip_probability=None,
            wind_mph=number(r.get("wind")), wind_gust_mph=None,
            surface=clean(r.get("surface")),
            environment_source="nflverse_schedule"
        )
        if c is not None:
            env.update(
                venue=clean(c.get("venue_name")) or env["venue"],
                venue_city=clean(c.get("venue_city")),
                venue_state=clean(c.get("venue_state"))
            )
            env.update(
                weather_status=clean(c.get("weather_status")) or wstatus,
                temperature_f=number(c.get("temperature_f")),
                precipitation_in=number(c.get("precipitation_in")),
                precip_probability=number(c.get("precip_probability")),
                wind_mph=number(c.get("wind_mph")),
                wind_gust_mph=number(c.get("wind_gust_mph")),
                environment_source="nflverse+existing_weather_context"
            )
        done = (
            number(r.get("away_score")) is not None and
            number(r.get("home_score")) is not None
        )
        add_pair(
            rows, "NFL", r.get("game_id"), r.get("gameday"),
            r.get("away_team"), r.get("home_team"), completed=done,
            away_score=r.get("away_score"), home_score=r.get("home_score"),
            game_type=r.get("game_type"), **env
        )

def nba_rows(rows):
    frames = [
        read(ROOT/"nba_live/history/NBA_GAME_HISTORY.csv"),
        read(ROOT/"nba_live/derived/NBA_GAMES_CURRENT.csv")
    ]
    for d in frames:
        for _, r in d.iterrows():
            add_pair(
                rows, "NBA", r.get("event_id"), r.get("start"),
                r.get("away_team"), r.get("home_team"),
                r.get("away_team_name"), r.get("home_team_name"),
                truthy(r.get("completed")), r.get("away_score"), r.get("home_score"),
                r.get("season_type"), venue="", venue_city="", venue_state="",
                environment_type="INDOOR",
                weather_status="NOT_APPLICABLE_INDOOR",
                temperature_f=None, precipitation_in=None,
                precip_probability=None, wind_mph=None, wind_gust_mph=None,
                surface="", environment_source="league_schedule"
            )

def nhl_rows(rows):
    frames = [
        read(ROOT/"nhl_live/history/NHL_GAME_HISTORY.csv"),
        read(ROOT/"nhl_live/derived/NHL_GAMES_CURRENT.csv")
    ]
    for d in frames:
        for _, r in d.iterrows():
            add_pair(
                rows, "NHL", r.get("event_id"), r.get("start"),
                r.get("away_team"), r.get("home_team"),
                r.get("away_team_name"), r.get("home_team_name"),
                truthy(r.get("completed")), r.get("away_score"), r.get("home_score"),
                r.get("game_type"), venue=clean(r.get("venue")),
                venue_city="", venue_state="", environment_type="INDOOR",
                weather_status="NOT_APPLICABLE_INDOOR",
                temperature_f=None, precipitation_in=None,
                precip_probability=None, wind_mph=None, wind_gust_mph=None,
                surface="ice", environment_source="league_schedule"
            )

def mlb_rows(rows):
    master = read(ROOT/"baseball_vault/derived/MLB_GAME_MASTER.csv")
    for _, r in master.iterrows():
        if clean(r.get("status")).lower() != "final":
            continue
        add_pair(
            rows, "MLB", r.get("gamePk"), r.get("gameDate"),
            r.get("away_team"), r.get("home_team"), completed=True,
            away_score=r.get("away_score"), home_score=r.get("home_score"),
            game_type=r.get("gameType"), venue=clean(r.get("venue")),
            venue_city="", venue_state="", environment_type="VENUE_DEPENDENT",
            weather_status="HISTORICAL_NOT_NEEDED",
            temperature_f=None, precipitation_in=None,
            precip_probability=None, wind_mph=None, wind_gust_mph=None,
            surface="", environment_source="mlb_game_master"
        )
    sched = read(ROOT/"baseball_vault/latest/MLB_SCHEDULE.csv")
    weather = read(ROOT/"baseball_vault/derived/MLB_WEATHER_FEATURES.csv")
    wmap = {
        id_text(r.get("gamePk")):r for _,r in weather.iterrows()
    } if not weather.empty else {}
    for _, r in sched.iterrows():
        done = clean(r.get("status")).lower() == "final"
        w = wmap.get(id_text(r.get("gamePk")))
        wstatus = (
            "CURRENT_WEATHER_MATCHED"
            if w is not None else "CURRENT_WEATHER_UNAVAILABLE"
        )
        add_pair(
            rows, "MLB", r.get("gamePk"), r.get("gameDate"),
            r.get("away_team"), r.get("home_team"), completed=done,
            away_score=r.get("away_score"), home_score=r.get("home_score"),
            game_type=r.get("gameType"), venue=clean(r.get("venue")),
            venue_city="", venue_state="", environment_type="VENUE_DEPENDENT",
            weather_status=wstatus,
            temperature_f=number(w.get("temperature_f")) if w is not None else None,
            precipitation_in=number(w.get("precipitation")) if w is not None else None,
            precip_probability=None,
            wind_mph=number(w.get("wind_mph")) if w is not None else None,
            wind_gust_mph=number(w.get("wind_gust_mph")) if w is not None else None,
            surface="", environment_source="mlb_schedule+existing_weather_features"
        )

def college_rows(rows, sport):
    d = read(ROOT/f"{sport.lower()}_live/derived/{sport}_GAMES_CURRENT.csv")
    indoor = sport == "CBB"
    for _, r in d.iterrows():
        done = truthy(r.get("completed"))
        add_pair(
            rows, sport, r.get("event_id"), r.get("start"),
            r.get("away_team"), r.get("home_team"),
            r.get("away_team_name"), r.get("home_team_name"),
            done, r.get("away_score"), r.get("home_score"),
            r.get("season_type"), venue=clean(r.get("venue")),
            venue_city=clean(r.get("venue_city")),
            venue_state=clean(r.get("venue_state")),
            environment_type="INDOOR" if indoor else "VENUE_ONLY",
            weather_status=(
                "NOT_APPLICABLE_INDOOR"
                if indoor else "WEATHER_NOT_COLLECTED"
            ),
            temperature_f=None, precipitation_in=None,
            precip_probability=None, wind_mph=None, wind_gust_mph=None,
            surface="", environment_source="league_schedule"
        )

def build_games():
    rows = []
    nfl_rows(rows)
    nba_rows(rows)
    nhl_rows(rows)
    mlb_rows(rows)
    college_rows(rows, "CFB")
    college_rows(rows, "CBB")
    d = pd.DataFrame(rows)
    d = d.drop_duplicates(["sport","game_id","team"], keep="last")
    d["game_date"] = pd.to_datetime(d["game_date"], utc=True).dt.normalize()
    return d.sort_values(["sport","game_date","game_id","team"])

def generic_strength(games, sport, lookback):
    d = games[(games.sport.eq(sport)) & games.completed].copy()
    d = d[d.game_date.ge(TODAY-pd.Timedelta(days=lookback))]
    allowed = {
        "NFL":{"REG"}, "NBA":{"2","2.0"},
        "NHL":{"2","2.0"}, "MLB":{"R"}
    }
    if sport in allowed:
        d = d[d.game_type.astype(str).isin(allowed[sport])]
    d = d[d.team_score.notna() & d.opp_score.notna()]
    if d.empty:
        return pd.DataFrame()
    d["win"] = (d.team_score > d.opp_score).astype(float)
    d["margin"] = d.team_score - d.opp_score
    g = d.groupby("team", as_index=False).agg(
        games=("game_id","nunique"),
        win_pct=("win","mean"),
        avg_margin=("margin","mean")
    )
    g["raw_strength"] = g.win_pct*100 + g.avg_margin*1.5
    g["strength_score"] = g.raw_strength.rank(
        pct=True, method="average"
    )*100
    g["strength_source"] = "recent_completed_games"
    g["sport"] = sport
    return g[[
        "sport","team","games","win_pct","avg_margin",
        "strength_score","strength_source"
    ]]

def context_strength(sport):
    p = ROOT/f"{sport.lower()}_live/decision/{sport}_TEAM_CONTEXT.csv"
    d = read(p)
    if d.empty:
        return pd.DataFrame()
    if sport == "CFB":
        d["raw_strength"] = (
            pd.to_numeric(d["current_win_rate"],errors="coerce")*100 +
            pd.to_numeric(d["current_avg_margin"],errors="coerce").fillna(0)*1.5
        )
        source = "current_team_context"
    else:
        games = pd.to_numeric(
            d["current_games"],errors="coerce"
        ).fillna(0)
        current = (
            pd.to_numeric(d["current_win_rate"],errors="coerce")*100 +
            pd.to_numeric(d["current_avg_margin"],errors="coerce").fillna(0)*1.5
        )
        prior = pd.to_numeric(d["prior_srs"],errors="coerce")
        prior = prior.fillna(
            pd.to_numeric(d["prior_elo"],errors="coerce")/30
        )
        d["raw_strength"] = current.where(games.ge(3), prior)
        source = "current_or_prior_baseline"
    d["strength_score"] = d["raw_strength"].rank(
        pct=True, method="average"
    )*100
    d["games"] = pd.to_numeric(
        d.get("current_games"),errors="coerce"
    ).fillna(0)
    d["win_pct"] = pd.to_numeric(
        d.get("current_win_rate"),errors="coerce"
    )
    d["avg_margin"] = pd.to_numeric(
        d.get("current_avg_margin"),errors="coerce"
    )
    d["strength_source"] = source
    d["sport"] = sport
    return d[[
        "sport","team","games","win_pct","avg_margin",
        "strength_score","strength_source"
    ]]

def build_strength(games):
    pieces = [
        generic_strength(games,"NFL",120),
        generic_strength(games,"NBA",400),
        generic_strength(games,"NHL",400),
        generic_strength(games,"MLB",230),
        context_strength("CFB"),
        context_strength("CBB")
    ]
    return pd.concat(
        [x for x in pieces if not x.empty], ignore_index=True
    )

def fatigue_score(gap_days, games4, games7, side, road_trip, sport):
    score = 0
    if gap_days is not None:
        if gap_days <= 1:
            score += 35
        elif gap_days <= 3:
            score += 25
        elif gap_days <= 4:
            score += 18
        elif gap_days <= 5:
            score += 10
        if sport in {"NFL","CFB"} and gap_days <= 5:
            score += 12
        if gap_days >= 8:
            score -= 8
    if games4 >= 4:
        score += 30
    elif games4 >= 3:
        score += 20
    if games7 >= 5:
        score += 15
    elif games7 >= 4:
        score += 8
    if side == "AWAY":
        score += 5
    if road_trip >= 3:
        score += 12
    elif road_trip >= 2:
        score += 6
    return int(max(0,min(100,score)))

def fatigue_label(score, has_last):
    if not has_last:
        return "LIMITED_SAMPLE"
    if score >= 55:
        return "HIGH_LOAD"
    if score >= 30:
        return "ELEVATED_LOAD"
    return "NORMAL_LOAD"

def build_load(games):
    future = games[
        (~games.completed) & games.game_date.ge(TODAY)
    ].copy()
    out = []
    for (sport, team), fg in future.groupby(["sport","team"]):
        fg = fg.sort_values(["game_date","game_id"])
        fg = fg.drop_duplicates("game_id")
        allg = games[
            games.sport.eq(sport) & games.team.eq(team)
        ].drop_duplicates("game_id")
        hist = allg[
            allg.completed & allg.game_date.le(TODAY)
        ].sort_values("game_date")
        nxt = fg.iloc[0]
        last_date = hist.game_date.iloc[-1] if len(hist) else pd.NaT
        gap = (
            int((nxt.game_date-last_date).days)
            if pd.notna(last_date) else None
        )
        rest = max(gap-1,0) if gap is not None else None
        w4 = allg[
            allg.game_date.between(
                nxt.game_date-pd.Timedelta(days=3),nxt.game_date
            )
        ]
        w7 = fg[
            fg.game_date.le(nxt.game_date+pd.Timedelta(days=6))
        ]
        seq = fg.head(5).side.tolist()
        road_trip = 0
        for side in seq:
            if side != "AWAY":
                break
            road_trip += 1
        score = fatigue_score(
            gap, w4.game_id.nunique(), w7.game_id.nunique(),
            nxt.side, road_trip, sport
        )
        if road_trip >= 3:
            travel = "EXTENDED_ROAD_TRIP"
        elif road_trip == 2:
            travel = "ROAD_TRIP"
        elif nxt.side == "AWAY":
            travel = "ROAD_GAME"
        elif len(seq)>=2 and seq[0]=="HOME" and seq[1]=="HOME":
            travel = "HOME_STAND"
        else:
            travel = "NORMAL_SEQUENCE"
        out.append(dict(
            sport=sport, team=team, team_name=nxt.team_name,
            last_game_date=(
                last_date.date().isoformat() if pd.notna(last_date) else ""
            ),
            next_game_date=nxt.game_date.date().isoformat(),
            next_opponent=nxt.opponent, next_side=nxt.side,
            gap_days=gap, rest_days=rest,
            back_to_back=bool(gap is not None and gap<=1),
            games_in_4_days_including_next=int(w4.game_id.nunique()),
            games_in_7_days_from_next=int(w7.game_id.nunique()),
            road_games_next_7=int((w7.side=="AWAY").sum()),
            home_games_next_7=int((w7.side=="HOME").sum()),
            road_trip_games_at_next=road_trip,
            next_5_sequence="-".join(
                "A" if x=="AWAY" else "H" if x=="HOME" else "N"
                for x in seq
            ),
            travel_sequence=travel,
            fatigue_load_score=score,
            fatigue_signal=fatigue_label(score,pd.notna(last_date)),
            score_is_probability=False,
            generated_at=NOW
        ))
    return pd.DataFrame(out)

def build_sos(games, strengths):
    future = games[
        (~games.completed) & games.game_date.ge(TODAY)
    ].copy()
    smap = {
        (r.sport,r.team):r.strength_score
        for _,r in strengths.iterrows()
        if pd.notna(r.strength_score)
    }
    out = []
    for (sport,team), fg in future.groupby(["sport","team"]):
        fg = fg.sort_values(
            ["game_date","game_id"]
        ).drop_duplicates("game_id").head(5)
        opp_scores = [smap.get((sport,x)) for x in fg.opponent]
        known = [
            float(x) for x in opp_scores
            if x is not None and not pd.isna(x)
        ]
        avg = sum(known)/len(known) if known else None
        if len(known) < 2:
            signal = "LIMITED_SAMPLE"
        elif avg >= 65:
            signal = "HARDER_THAN_LEAGUE_BASELINE"
        elif avg <= 35:
            signal = "EASIER_THAN_LEAGUE_BASELINE"
        else:
            signal = "BALANCED"
        out.append(dict(
            sport=sport, team=team,
            scheduled_games=int(len(fg)),
            games_evaluated=int(len(known)),
            horizon="NEXT_5_AVAILABLE_GAMES",
            next_opponents=" | ".join(
                fg.opponent.astype(str).tolist()
            ),
            opponent_strength_avg=(
                round(avg,2) if avg is not None else None
            ),
            opponent_strength_min=(
                round(min(known),2) if known else None
            ),
            opponent_strength_max=(
                round(max(known),2) if known else None
            ),
            future_schedule_signal=signal,
            score_is_probability=False,
            automatic_model_adjustment=False,
            generated_at=NOW
        ))
    return pd.DataFrame(out)

def build_environment(games):
    f = games[
        (~games.completed) & games.game_date.ge(TODAY)
    ].copy()
    cols = [
        "sport","game_id","game_date","team","opponent",
        "venue","venue_city","venue_state","environment_type",
        "weather_status","temperature_f","precipitation_in",
        "precip_probability","wind_mph","wind_gust_mph",
        "surface","environment_source"
    ]
    if f.empty:
        return pd.DataFrame(columns=cols)
    f = f.sort_values(
        ["sport","game_date","game_id"]
    ).drop_duplicates(["sport","game_id"])
    f["game_date"] = f.game_date.dt.date.astype(str)
    f["generated_at"] = NOW
    return f[cols+["generated_at"]]

def build_catalog():
    rows = []
    for sport in ["NFL","NBA","NHL","MLB","CFB","CBB"]:
        rows += [
            dict(
                sport=sport, capability="rest_and_schedule_density",
                status="LIVE", source="existing league schedule/history",
                exact_travel_miles=False
            ),
            dict(
                sport=sport, capability="future_opponent_difficulty",
                status="LIVE",
                source="existing schedule + team performance context",
                exact_travel_miles=False
            ),
            dict(
                sport=sport, capability="travel_sequence",
                status="LIVE", source="home/away schedule sequence",
                exact_travel_miles=False
            )
        ]
    rows += [
        dict(
            sport="NFL", capability="game_weather",
            status="LIVE_WITH_COVERAGE_GAPS",
            source="existing NFL weather context",
            exact_travel_miles=False
        ),
        dict(
            sport="MLB", capability="game_weather",
            status="PARTIAL", source="existing MLB weather features",
            exact_travel_miles=False
        ),
        dict(
            sport="CFB", capability="game_weather",
            status="GAP", source="venue present; weather not yet collected",
            exact_travel_miles=False
        )
    ]
    for sport in ["NFL","NBA","NHL","MLB","CFB","CBB"]:
        rows.append(dict(
            sport=sport, capability="exact_travel_distance",
            status="GAP", source="coordinates/routing source required",
            exact_travel_miles=False
        ))
    d = pd.DataFrame(rows)
    d["generated_at"] = NOW
    return d

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    games = build_games()
    strengths = build_strength(games)
    load = build_load(games)
    sos = build_sos(games, strengths)
    env = build_environment(games)
    cat = build_catalog()

    load.to_csv(LOAD_OUT,index=False)
    sos.to_csv(SOS_OUT,index=False)
    env.to_csv(ENV_OUT,index=False)
    cat.to_csv(CATALOG_OUT,index=False)

    receipt = {
        "generated_at":NOW,
        "as_of_utc":ASOF.isoformat(),
        "team_schedule_load_rows":int(len(load)),
        "schedule_rows_by_sport":(
            load.sport.value_counts().astype(int).to_dict()
            if len(load) else {}
        ),
        "fatigue_signal_counts":(
            load.fatigue_signal.value_counts().astype(int).to_dict()
            if len(load) else {}
        ),
        "future_schedule_rows":int(len(sos)),
        "future_schedule_signal_counts":(
            sos.future_schedule_signal.value_counts().astype(int).to_dict()
            if len(sos) else {}
        ),
        "game_environment_rows":int(len(env)),
        "environment_weather_status_counts":(
            env.weather_status.value_counts().astype(int).to_dict()
            if len(env) else {}
        ),
        "team_strength_reference_rows":int(len(strengths)),
        "catalog_rows":int(len(cat)),
        "explicit_gaps":cat[
            cat.status.eq("GAP")
        ][["sport","capability","source"]].to_dict("records"),
        "score_is_probability":False,
        "automatic_model_adjustment":False,
        "paid_provider_required":False
    }
    RECEIPT.write_text(
        json.dumps(receipt,indent=2,sort_keys=True)
    )
    print(
        "SCHEDULE LOAD:",len(load),
        receipt["schedule_rows_by_sport"]
    )
    print(
        "FATIGUE:",
        receipt["fatigue_signal_counts"]
    )
    print(
        "FUTURE SOS:",len(sos),
        receipt["future_schedule_signal_counts"]
    )
    print(
        "ENVIRONMENT:",len(env),
        receipt["environment_weather_status_counts"]
    )
    print("RESULT: SCHEDULE_INTELLIGENCE_READY")

if __name__ == "__main__":
    main()
