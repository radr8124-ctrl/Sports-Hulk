import os
import requests

BASE = "https://api.collegefootballdata.com"

class CFBDClient:
    def __init__(self, api_key=None, timeout=30):
        self.api_key = api_key or os.getenv("COLLEGEFOOTBALLDATA_API_KEY", "") or os.getenv("CFBD_API_KEY", "")
        self.timeout = timeout

    @property
    def connected(self):
        return bool(self.api_key.strip())

    def _get(self, path, params=None):
        if not self.connected:
            raise RuntimeError("COLLEGEFOOTBALLDATA_API_KEY is not set.")
        r = requests.get(
            BASE + path,
            params=params or {},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def games(self, year, week=None, season_type="regular", classification="fbs"):
        params = {"year": int(year), "seasonType": season_type, "classification": classification}
        if week is not None:
            params["week"] = int(week)
        return self._get("/games", params)

    def core_ratings(self, year):
        return self._get("/ratings/core", {"year": int(year)})

    def srs_ratings(self, year):
        return self._get("/ratings/srs", {"year": int(year)})
