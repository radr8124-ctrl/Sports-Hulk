"""Official NBA competition type must be source-evidenced, never guessed."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from nba_live.build_nba_core import season_info
from nba_live.decision.espn_competition_regime import (
    dates_to_query, fetch_scoreboard_events, label_decision,
    parse_scoreboard_event, season_type_value,
)
from nba_live.decision.enrich_nba_competition_regime import enrich


def fixture_event(event_id="401909089", *, start="2026-10-20T23:00Z",
                  away="PHI", home="NY", season_type=2):
    return {
        "id": event_id,
        "date": start,
        "season": {"year": 2027, "type": season_type},
        "competitions": [{"competitors": [
            {"homeAway": "away", "team": {"abbreviation": away}},
            {"homeAway": "home", "team": {"abbreviation": home}},
        ]}],
    }


def fixture_row(*, date="2026-10-20", start="2026-10-20 23:00:00+00:00",
                away="PHI", home="NYK"):
    return {
        "game_key": f"{date}|{away}|{home}",
        "start_dt": start,
        "away_team_canonical": away,
        "home_team_canonical": home,
        "market_canonical": "SPREAD", "decision": "EARLY_MARKET_WATCH",
    }


class FakeResponse:
    def __init__(self, data, status=200):
        self.data = data
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, by_date):
        self.by_date = by_date
        self.requested = []

    def get(self, url, *, params, timeout):
        assert "espn.com" in url and timeout > 0
        day = params["dates"]
        self.requested.append(day)
        response = self.by_date.get(day, {"events": []})
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


class OfficialSourceTests(unittest.TestCase):
    def test_espn_core_season_type_reference_is_explicit(self):
        event = {
            "season": {"$ref": "http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2027"},
            "seasonType": {"$ref": "http://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2027/types/1?lang=en"},
        }
        self.assertEqual(season_info(event), (2027, 1))
        event["seasonType"]["$ref"] = event["seasonType"]["$ref"].replace("/types/1?", "/types/2?")
        self.assertEqual(season_info(event), (2027, 2))

    def test_core_conflicting_metadata_is_not_trusted(self):
        event = {
            "season": {"year": 2027, "type": 1},
            "seasonType": {"$ref": "https://sports.core.api.espn.com/v2/sports/basketball/leagues/nba/seasons/2027/types/2"},
        }
        self.assertEqual(season_info(event), (2027, None))
        event["season"]["year"] = 2026
        self.assertEqual(season_info(event), (2026, None))

    def test_scoreboard_explicit_regular_preseason_postseason(self):
        for raw, label in [(1, "PRESEASON"), (2, "REGULAR"), (3, "POSTSEASON")]:
            with self.subTest(raw=raw):
                e = parse_scoreboard_event(fixture_event(season_type=raw))
                self.assertEqual(e["competition_regime"], label)
                self.assertEqual(e["season_type"], str(raw))

    def test_scoreboard_unrecognized_season_remains_unknown(self):
        for raw in ("regular season!", "2026-10-20", 4, None):
            self.assertEqual(season_type_value(raw), ("", "UNKNOWN"))

    def test_verified_game_uses_both_teams_and_real_start(self):
        row = fixture_row()
        event = parse_scoreboard_event(fixture_event())
        revised, reason = label_decision(row, [event])
        self.assertEqual(reason, "VERIFIED")
        self.assertEqual(revised["competition_regime"], "REGULAR")
        self.assertEqual(revised["season_type"], "2")
        self.assertEqual(revised["espn_event_id"], "401909089")
        self.assertEqual(row.get("season_type"), None)

    def test_preseason_alias_and_kickoff_drift(self):
        row = fixture_row(date="2026-10-07", start="2026-10-07T23:10:00+00:00", away="MIN", home="IND")
        event = parse_scoreboard_event(fixture_event("401914123", start="2026-10-07T23:00Z",
                                                      away="MIN", home="IND", season_type=1))
        labeled, reason = label_decision(row, [event])
        self.assertEqual(reason, "VERIFIED")
        self.assertEqual(labeled["competition_regime"], "PRESEASON")

    def test_wrong_teams_wrong_start_and_key_are_rejected(self):
        event = parse_scoreboard_event(fixture_event())
        for row, expected in [
            (fixture_row(away="CHI"), "NO_EXACT_EVENT"),
            (fixture_row(start="2026-10-20T22:00:00+00:00"), "NO_EXACT_EVENT"),
            (fixture_row(date="2026-10-21"), "GAME_KEY_MISMATCH"),
            (fixture_row(start="2026-10-20 23:00:00"), "INVALID_GAME"),
        ]:
            with self.subTest(reason=expected):
                labeled, reason = label_decision(row, [event])
                self.assertEqual(reason, expected)
                self.assertEqual(labeled["competition_regime"], "UNKNOWN")
                self.assertEqual(labeled["espn_event_id"], "")

    def test_existing_explicit_conflict_blocks_label(self):
        row = fixture_row()
        row.update(season_type="1", competition_regime="PRESEASON")
        result, reason = label_decision(row, [parse_scoreboard_event(fixture_event())])
        self.assertEqual(reason, "CONFLICTING_EXISTING_REGIME")
        self.assertEqual(result["competition_regime"], "UNKNOWN")

    def test_two_possible_events_are_ambiguous(self):
        events = [
            parse_scoreboard_event(fixture_event("aaa")),
            parse_scoreboard_event(fixture_event("bbb", start="2026-10-20T23:05Z")),
        ]
        result, reason = label_decision(fixture_row(), events)
        self.assertEqual(reason, "AMBIGUOUS")
        self.assertEqual(result["season_type"], "")

    def test_missing_provider_event_type_is_unknown(self):
        event = parse_scoreboard_event(fixture_event(season_type=None))
        result, reason = label_decision(fixture_row(), [event])
        self.assertEqual(reason, "NO_EXPLICIT_SEASON_TYPE")
        self.assertEqual(result["competition_regime"], "UNKNOWN")

    def test_date_query_is_for_event_discovery_only(self):
        rows = [fixture_row(start="2026-10-21T01:30:00+00:00",
                            date="2026-10-21", away="SAS", home="OKC")]
        self.assertEqual(dates_to_query(rows), ["20261020", "20261021"])

    def test_duplicated_conflicting_espn_id_cannot_be_used(self):
        e1, e2 = fixture_event(), fixture_event(season_type=1)
        session = FakeSession({
            "20261020": {"events": [e1]},
            "20261021": {"events": [e2]},
        })
        events, receipt = fetch_scoreboard_events(["20261020", "20261021"], session)
        self.assertEqual(len(events), 0)
        self.assertEqual(receipt["conflicting_event_ids"], 1)

    def test_failed_source_day_is_reported(self):
        session = FakeSession({"20261020": TimeoutError("offline")})
        events, receipt = fetch_scoreboard_events(["20261020", "20261021"], session)
        self.assertEqual(events, [])
        self.assertEqual(receipt["successful_dates"], ["20261021"])
        self.assertIn("20261020", receipt["failed_dates"])


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.decision_dir = self.root / "nba_live" / "decision"
        self.decision_dir.mkdir(parents=True)
        self.rows = [fixture_row(), fixture_row(away="TOR", home="CHI")]
        self.columns = list(self.rows[0])
        for name in ("NBA_GAME_DECISIONS.csv", "NBA_GAME_FINALISTS.csv"):
            with (self.decision_dir / name).open("w", newline="") as handle:
                out = csv.DictWriter(handle, fieldnames=self.columns)
                out.writeheader()
                out.writerows(self.rows[:1] if "FINALISTS" in name else self.rows)

    def session(self):
        return FakeSession({"20261020": {"events": [fixture_event()]}})

    def test_enrichment_preserves_other_fields_and_writes_receipt(self):
        report = enrich(self.root, self.session())
        self.assertEqual(report["status"], "READY")
        self.assertEqual(report["verified_games"], 1)
        self.assertEqual(report["unknown_games"], 1)
        for name in ("NBA_GAME_DECISIONS.csv", "NBA_GAME_FINALISTS.csv"):
            with (self.decision_dir / name).open() as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["competition_regime"], "REGULAR")
            self.assertEqual(rows[0]["decision"], "EARLY_MARKET_WATCH")
            self.assertEqual(rows[0]["competition_regime_source"], "ESPN_SITE_SCOREBOARD_EXACT_GAME")
        self.assertTrue((self.decision_dir / "receipts" / "NBA_REGIME_SOURCE_RECEIPT.json").exists())
        self.assertFalse(report["proof_promotion_permitted"])

    def test_total_espn_outage_keeps_decision_bytes_unchanged(self):
        path = self.decision_dir / "NBA_GAME_DECISIONS.csv"
        before = path.read_bytes()
        session = FakeSession({"20261019": TimeoutError("offline"), "20261020": TimeoutError("offline")})
        report = enrich(self.root, session)
        self.assertEqual(report["status"], "SOURCE_UNAVAILABLE")
        self.assertEqual(path.read_bytes(), before)

    def test_dry_run_never_modifies_csv_or_receipt(self):
        before = (self.decision_dir / "NBA_GAME_DECISIONS.csv").read_bytes()
        report = enrich(self.root, self.session(), dry_run=True)
        self.assertEqual(report["status"], "READY")
        self.assertEqual(before, (self.decision_dir / "NBA_GAME_DECISIONS.csv").read_bytes())
        self.assertFalse((self.decision_dir / "receipts").exists())

    def test_second_run_preserves_verified_provenance(self):
        first = enrich(self.root, self.session())
        second = enrich(self.root, self.session())
        self.assertEqual(first["verified_games"], second["verified_games"])
        with (self.decision_dir / "NBA_GAME_DECISIONS.csv").open() as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(row["season_type"], "2")
        self.assertEqual(row["competition_regime"], "REGULAR")


if __name__ == "__main__":
    unittest.main()
