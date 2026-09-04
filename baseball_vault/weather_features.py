from pathlib import Path
import json
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"

def closest_hour(weather_json, game_date):
    try:
        w=json.loads(weather_json)
        times=pd.to_datetime(w.get("hourly",{}).get("time",[]),errors="coerce",utc=True)
        gd=pd.to_datetime(game_date,errors="coerce",utc=True)
        if len(times)==0 or pd.isna(gd): return {}
        idx=int(np.argmin(np.abs((times-gd).total_seconds())))
        h=w.get("hourly",{})
        def val(k):
            arr=h.get(k,[])
            return arr[idx] if idx < len(arr) else np.nan
        return {
            "temperature_f":val("temperature_2m"),
            "precipitation":val("precipitation"),
            "wind_mph":val("wind_speed_10m"),
            "wind_gust_mph":val("wind_gusts_10m"),
            "humidity_pct":val("relative_humidity_2m"),
            "weather_hour_utc":times[idx].isoformat()
        }
    except Exception:
        return {}

def build():
    f=DERIVED/"MLB_WEATHER_RAW.parquet"
    if not f.exists():
        print("No MLB_WEATHER_RAW.parquet yet. Run baseball_vault/weather.py first.")
        return
    d=pd.read_parquet(f)
    rows=[]
    for _,r in d.iterrows():
        x={"gamePk":r.get("gamePk"),"home_team":r.get("home_team"),"gameDate":r.get("gameDate")}
        x.update(closest_hour(r.get("weather_json","{}"),r.get("gameDate")))
        rows.append(x)
    out=pd.DataFrame(rows)
    out.to_csv(DERIVED/"MLB_WEATHER_FEATURES.csv",index=False)
    out.to_parquet(DERIVED/"MLB_WEATHER_FEATURES.parquet",index=False)
    print(f"Weather feature rows: {len(out):,}")
    print("SPORTS HULK MLB WEATHER FEATURES: DONE")

if __name__=="__main__":
    build()
