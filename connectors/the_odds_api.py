from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


class TheOddsAPIClient:
    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 25):
        self.api_key = api_key or os.getenv("THE_ODDS_API_KEY")
        self.timeout = timeout

    @property
    def connected(self) -> bool:
        return bool(self.api_key)

    def _require_key(self):
        if not self.api_key:
            raise RuntimeError("THE_ODDS_API_KEY is missing")

    def sports(self) -> List[Dict[str, Any]]:
        self._require_key()
        r = requests.get(
            f"{self.BASE_URL}/sports/",
            params={"apiKey": self.api_key},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    def odds(
        self,
        sport: str,
        regions: str = "us",
        markets: str = "h2h,spreads,totals",
        odds_format: str = "american",
        date_format: str = "iso",
    ) -> Dict[str, Any]:
        self._require_key()
        r = requests.get(
            f"{self.BASE_URL}/sports/{sport}/odds/",
            params={
                "apiKey": self.api_key,
                "regions": regions,
                "markets": markets,
                "oddsFormat": odds_format,
                "dateFormat": date_format,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return {
            "data": r.json(),
            "usage": {
                "remaining": r.headers.get("x-requests-remaining"),
                "used": r.headers.get("x-requests-used"),
                "last": r.headers.get("x-requests-last"),
            },
        }

    def ncaaf_odds(self) -> Dict[str, Any]:
        return self.odds("americanfootball_ncaaf")
