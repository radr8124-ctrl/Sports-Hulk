from __future__ import annotations

import requests
from typing import Any, Dict, Optional


class ESPNPublicClient:
    NFL_SCOREBOARD = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/scoreboard"
    )

    NFL_SUMMARY = (
        "https://site.api.espn.com/apis/site/v2/"
        "sports/football/nfl/summary"
    )

    def __init__(self, timeout: int = 25):
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "Sports-HULK/1.0",
        }

    def _get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        r = requests.get(
            url,
            params=params or {},
            headers=self.headers,
            timeout=self.timeout,
        )

        payload = None
        try:
            payload = r.json()
        except Exception:
            pass

        return {
            "http_status": r.status_code,
            "data": payload,
            "text": r.text[:1000],
        }

    def scoreboard(self) -> Dict[str, Any]:
        return self._get(self.NFL_SCOREBOARD)

    def summary(self, event_id: str) -> Dict[str, Any]:
        return self._get(
            self.NFL_SUMMARY,
            params={"event": event_id},
        )
