from __future__ import annotations

from pathlib import Path

import os
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


ROOT = Path("/home/ubuntu/sports-hulk")
load_dotenv(ROOT / ".env")


class PropLineClient:
    BASE_URL = "https://api.prop-line.com/v1"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        self.api_key = (api_key or os.getenv("PROPLINE_API_KEY") or "").strip()
        self.timeout = timeout

    @property
    def connected(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> Dict[str, str]:
        if not self.connected:
            raise RuntimeError("PROPLINE_API_KEY is missing")
        return {
            "X-API-Key": self.api_key,
            "Accept": "application/json",
            "User-Agent": "Sports-HULK/1.0",
        }

    @staticmethod
    def _quota_headers(response: requests.Response) -> Dict[str, Any]:
        # requests headers are case-insensitive
        names = [
            "X-Daily-Limit",
            "X-Daily-Used",
            "X-Daily-Remaining",
            "X-Daily-Reset",
            "RateLimit-Limit",
            "RateLimit-Remaining",
            "RateLimit-Reset",
            "RateLimit-Policy",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Retry-After",
        ]
        return {name: response.headers.get(name) for name in names}

    def freshness(self) -> Dict[str, Any]:
        r = requests.get(
            f"{self.BASE_URL}/freshness",
            timeout=self.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": "Sports-HULK/1.0",
            },
        )
        r.raise_for_status()
        return {
            "data": r.json(),
            "http_status": r.status_code,
        }

    def sports(self) -> Dict[str, Any]:
        r = requests.get(
            f"{self.BASE_URL}/sports",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return self._result(r)

    def odds(
        self,
        sport: str,
        markets: str = "h2h,spreads,totals",
    ) -> Dict[str, Any]:
        r = requests.get(
            f"{self.BASE_URL}/sports/{sport}/odds",
            headers=self._headers(),
            params={"markets": markets},
            timeout=self.timeout,
        )
        return self._result(r)

    def scores(self, sport: str) -> Dict[str, Any]:
        r = requests.get(
            f"{self.BASE_URL}/sports/{sport}/scores",
            headers=self._headers(),
            timeout=self.timeout,
        )
        return self._result(r)

    def _result(self, r: requests.Response) -> Dict[str, Any]:
        payload = None
        try:
            payload = r.json()
        except Exception:
            payload = None

        return {
            "http_status": r.status_code,
            "data": payload,
            "quota": self._quota_headers(r),
            "text": r.text[:1000],
        }
