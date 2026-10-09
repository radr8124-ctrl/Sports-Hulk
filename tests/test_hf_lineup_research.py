"""Isolated Hugging Face lineup reaction source proof gates."""
import unittest
from copy import deepcopy

from intelligence_warehouse.provider_integrations.hf_lineup_research import audit_rows


def source():
    return {
        "event_id":"astros~2026-06-18 17:00:00",
        "team":"astros",
        "tweet_ts":"2026-06-18T17:00:00",
        "game_id":"m~verified-one",
        "player":"Player One",
        "market":"hits",
        "line":1.5,"side":"over","book":"fanduel",
        "ts":"2026-06-18T17:01:00","offset_sec":60,
        "odds":2.04,"is_suspended":False,"is_alt":False,
    }


def official():
    return [{"status":"VERIFIED_HISTORICAL","game_id":"m~verified-one",
             "official_game_pk":820001, "official_start":"2026-06-18T22:00:00+00:00",
             "player":"player one"}]


class TestHuggingFaceLineupSourceGate(unittest.TestCase):
    def test_exact_verified_event_remains_research_only(self):
        r=audit_rows([source()],official())[0]
        self.assertEqual(r["status"],"RESEARCH_CANDIDATE_NEEDS_LINEUP_TEAM_AND_PAIR_VERIFICATION")
        self.assertEqual(r["official_game_pk"],"820001")

    def test_unmatched_game_is_not_mapped_by_player_name(self):
        s=source();s["game_id"]="m~different"
        self.assertEqual(audit_rows([s],official())[0]["status"],"MISSING_UNIQUE_OFFICIAL_GAME_CROSSWALK")

    def test_conflicting_official_game_identity_never_guessed(self):
        a=official();a.append(dict(a[0], official_game_pk=820002))
        self.assertEqual(audit_rows([source()],a)[0]["status"],"MISSING_UNIQUE_OFFICIAL_GAME_CROSSWALK")

    def test_unverified_player_not_accepted(self):
        s=source();s["player"]="Another player"
        self.assertEqual(audit_rows([s],official())[0]["status"],"UNVERIFIED_OR_DIFFERENT_PLAYER")

    def test_wrong_relative_timestamp_declined(self):
        s=source();s["offset_sec"]=600
        self.assertEqual(audit_rows([s],official())[0]["status"],"SOURCE_TIME_CONTRADICTION")

    def test_expired_after_kickoff_not_accepted(self):
        s=source();s["tweet_ts"]="2026-06-18T22:00:00";s["ts"]="2026-06-18T22:01:00"
        self.assertEqual(audit_rows([s],official())[0]["status"],"NOT_VERIFIED_PREGAME")

    def test_suspended_quote_rejected(self):
        s=source();s["is_suspended"]=True
        self.assertEqual(audit_rows([s],official())[0]["status"],"SUSPENDED_QUOTE")

    def test_alternate_not_mainline(self):
        s=source();s["is_alt"]=True
        self.assertEqual(audit_rows([s],official())[0]["status"],"ALTERNATE_PROP_NOT_MAIN_LINE")

    def test_wrong_price_not_accepted(self):
        s=source();s["odds"]=1.0
        self.assertEqual(audit_rows([s],official())[0]["status"],"INVALID_SOURCE_FIELDS")

    def test_pre_tweet_quote_reference_only(self):
        s=source();s["ts"]="2026-06-18T16:59:00";s["offset_sec"]=-60
        self.assertEqual(audit_rows([s],official())[0]["status"],"PRE_ANNOUNCEMENT_REFERENCE_ONLY")


if __name__=="__main__":unittest.main()
