from pathlib import Path
import pandas as pd
from datetime import timezone
import sys

ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "nfl_live" / "derived"

sys.path.insert(0, str(ROOT))

from connectors.open_meteo import OpenMeteoClient

SRC = OUT / "NFL_SURVIVOR_CONTEXT.csv"

if not SRC.exists():
    raise SystemExit("NFL_SURVIVOR_CONTEXT.csv missing")

df = pd.read_csv(SRC)
df["start"] = pd.to_datetime(df["start"], utc=True)

# Coordinates only for current known venues.
# No guessing beyond canonical venue locations.
VENUES = {
    "Hard Rock Stadium": (25.9580, -80.2389),
    "Levi's Stadium": (37.4030, -121.9700),
    "Northwest Stadium": (38.9076, -76.8645),
    "Highmark Stadium": (42.7738, -78.7870),
    "Soldier Field": (41.8623, -87.6167),
    "Acrisure Stadium": (40.4468, -80.0158),
    "Maracanã Stadium": (-22.9122, -43.2302),
    "EverBank Stadium": (30.3239, -81.6373),
    "MetLife Stadium": (40.8135, -74.0745),
    "Huntington Bank Field": (41.5061, -81.6995),
    "Empower Field at Mile High": (39.7439, -105.0201),
    "Raymond James Stadium": (27.9759, -82.5033),
}

client = OpenMeteoClient()

rows = []

for _, row in df.iterrows():
    out = row.to_dict()

    indoor = row.get("venue_indoor")

    if str(indoor).lower() == "true":
        out.update({
            "weather_status": "INDOOR",
            "temperature_f": None,
            "precipitation_in": None,
            "precip_probability": None,
            "wind_mph": None,
            "wind_gust_mph": None,
            "weather_code": None,
        })
        rows.append(out)
        continue

    venue = row.get("venue_name")
    coords = VENUES.get(venue)

    if not coords:
        out["weather_status"] = "NO_COORDINATES"
        rows.append(out)
        continue

    kickoff = row["start"]
    date_str = kickoff.strftime("%Y-%m-%d")

    result = client.forecast(
        coords[0],
        coords[1],
        date_str,
        date_str,
    )

    if result["http_status"] != 200:
        out["weather_status"] = f"HTTP_{result['http_status']}"
        rows.append(out)
        continue

    hourly = result["data"].get("hourly", {})
    times = pd.to_datetime(
        hourly.get("time", []),
        utc=True,
        errors="coerce",
    )

    if len(times) == 0:
        out["weather_status"] = "NO_HOURLY_DATA"
        rows.append(out)
        continue

    idx = abs(times - kickoff).argmin()

    def val(key):
        arr = hourly.get(key) or []
        return arr[idx] if idx < len(arr) else None

    out.update({
        "weather_status": "LIVE_FORECAST",
        "temperature_f": val("temperature_2m"),
        "precipitation_in": val("precipitation"),
        "precip_probability": val("precipitation_probability"),
        "wind_mph": val("wind_speed_10m"),
        "wind_gust_mph": val("wind_gusts_10m"),
        "wind_direction": val("wind_direction_10m"),
        "weather_code": val("weather_code"),
    })

    rows.append(out)

weather = pd.DataFrame(rows)

weather.to_csv(
    OUT / "NFL_SURVIVOR_CONTEXT_WEATHER.csv",
    index=False,
)

print("WEATHER ROWS:", len(weather))
print()

cols = [
    c for c in [
        "survivor_team",
        "venue_name",
        "venue_indoor",
        "weather_status",
        "temperature_f",
        "precip_probability",
        "wind_mph",
        "wind_gust_mph",
    ]
    if c in weather.columns
]

print(weather[cols].to_string(index=False))

print()
print("RESULT: WEATHER_READY")
