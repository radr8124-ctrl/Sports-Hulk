from __future__ import annotations

import requests


class OpenMeteoClient:
    BASE = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout=25):
        self.timeout = timeout

    def forecast(self, lat, lon, start_date, end_date):
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": ",".join([
                "temperature_2m",
                "precipitation",
                "precipitation_probability",
                "wind_speed_10m",
                "wind_gusts_10m",
                "wind_direction_10m",
                "weather_code",
            ]),
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "UTC",
            "start_date": start_date,
            "end_date": end_date,
        }

        r = requests.get(
            self.BASE,
            params=params,
            timeout=self.timeout,
            headers={"User-Agent": "Sports-HULK/1.0"},
        )

        return {
            "http_status": r.status_code,
            "data": r.json() if r.status_code == 200 else None,
            "text": r.text[:1000],
        }
