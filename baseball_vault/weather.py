from pathlib import Path
import argparse, json, urllib.parse, urllib.request
import pandas as pd

HERE=Path(__file__).resolve().parent
DERIVED=HERE/"derived"
LATEST=HERE/"latest"

# MLB park coordinates for active parks. This is deliberately stored in code so weather pulls are reproducible.
PARKS={
"Arizona Diamondbacks":(33.4455,-112.0667),"Atlanta Braves":(33.8907,-84.4677),
"Baltimore Orioles":(39.2839,-76.6217),"Boston Red Sox":(42.3467,-71.0972),
"Chicago Cubs":(41.9484,-87.6553),"Chicago White Sox":(41.8300,-87.6338),
"Cincinnati Reds":(39.0979,-84.5082),"Cleveland Guardians":(41.4962,-81.6852),
"Colorado Rockies":(39.7559,-104.9942),"Detroit Tigers":(42.3390,-83.0485),
"Houston Astros":(29.7573,-95.3555),"Kansas City Royals":(39.0517,-94.4803),
"Los Angeles Angels":(33.8003,-117.8827),"Los Angeles Dodgers":(34.0739,-118.2400),
"Miami Marlins":(25.7781,-80.2196),"Milwaukee Brewers":(43.0280,-87.9712),
"Minnesota Twins":(44.9817,-93.2776),"New York Mets":(40.7571,-73.8458),
"New York Yankees":(40.8296,-73.9262),"Athletics":(38.5802,-121.4997),
"Philadelphia Phillies":(39.9061,-75.1665),"Pittsburgh Pirates":(40.4469,-80.0057),
"San Diego Padres":(32.7073,-117.1566),"San Francisco Giants":(37.7786,-122.3893),
"Seattle Mariners":(47.5914,-122.3325),"St. Louis Cardinals":(38.6226,-90.1928),
"Tampa Bay Rays":(27.7682,-82.6534),"Texas Rangers":(32.7473,-97.0848),
"Toronto Blue Jays":(43.6414,-79.3894),"Washington Nationals":(38.8730,-77.0074)
}

def get_json(url,params):
    u=url+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(u,headers={"User-Agent":"Sports-HULK-Baseball/1.0"})
    with urllib.request.urlopen(req,timeout=90) as r: return json.loads(r.read().decode())

def main():
    a=argparse.ArgumentParser(); a.add_argument("--days",type=int,default=2); z=a.parse_args()
    f=LATEST/"MLB_SCHEDULE.csv"
    if not f.exists(): raise SystemExit("Run collect_nightly.py first.")
    s=pd.read_csv(f)
    rows=[]
    for _,g in s.iterrows():
        team=g.get("home_team"); coord=PARKS.get(team)
        if not coord: continue
        lat,lon=coord
        d=get_json("https://api.open-meteo.com/v1/forecast",{
          "latitude":lat,"longitude":lon,
          "hourly":"temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m,relative_humidity_2m",
          "temperature_unit":"fahrenheit","wind_speed_unit":"mph","forecast_days":z.days,"timezone":"UTC"})
        rows.append({"gamePk":g.get("gamePk"),"home_team":team,"gameDate":g.get("gameDate"),
                     "latitude":lat,"longitude":lon,"weather_json":json.dumps(d)})
    DERIVED.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_parquet(DERIVED/"MLB_WEATHER_RAW.parquet",index=False)
    print(f"Weather game rows: {len(rows):,}")
    print("SPORTS HULK MLB WEATHER: DONE")
if __name__=="__main__": main()
