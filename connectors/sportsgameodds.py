import os, requests
BASE="https://api.sportsgameodds.com/v2"
class SportsGameOddsClient:
    def __init__(self, api_key=None, timeout=25):
        self.api_key=api_key or os.getenv("SPORTSGAMEODDS_API_KEY","")
        self.timeout=timeout
    @property
    def connected(self): return bool(self.api_key.strip())
    def _get(self,path,params=None):
        if not self.connected: raise RuntimeError("SPORTSGAMEODDS_API_KEY is not set.")
        r=requests.get(BASE+path,params=params or {},headers={"x-api-key":self.api_key},timeout=self.timeout)
        r.raise_for_status()
        out=r.json()
        if out.get("success") is False: raise RuntimeError(out.get("error") or "SportsGameOdds request failed")
        return out
    def events(self, league_id, starts_after=None, starts_before=None, limit=100):
        p={"leagueID":league_id,"oddsAvailable":"true","ended":"false","limit":limit}
        if starts_after: p["startsAfter"]=starts_after
        if starts_before: p["startsBefore"]=starts_before
        return self._get("/events",p)
    def usage(self): return self._get("/account/usage")
