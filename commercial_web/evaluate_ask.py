#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime, timezone
import json
import re
import urllib.request

BASE = "http://127.0.0.1:8510/api/ask"
ROOT = Path("/home/ubuntu/sports-hulk")
OUT = ROOT / "reports" / "ASK_SPORTS_HULK_EVAL.json"

CASES = [
    {"q": "What is the Colts score?", "intent": "live_score", "status": "CURRENT"},
    {"q": "Show me live scores", "intent": "live_scores", "status": "CURRENT"},
    {"q": "What is the best NFL bet?", "intent": "best_bet", "status": "CURRENT", "no_high_juice_default": True},
    {"q": "Best spread bet", "intent": "best_bet", "status": "CURRENT"},
    {"q": "Best total bet", "intent": "best_bet", "status": "CURRENT"},
    {"q": "Best moneyline bet", "intent": "best_bet", "status": "CURRENT"},
    {"q": "Best props today", "intent": "props", "status": "CURRENT"},
    {"q": "Survivor pick", "intent": "survivor", "status": "CURRENT"},
    {"q": "Who should I start?", "intent": "start_sit", "status": "CURRENT", "needs_context": True},
    {"q": "Should I start Josh Allen or Lamar Jackson?", "intent": "start_sit", "status": "CURRENT", "named_compare": ["Josh Allen", "Lamar Jackson"]},
    {"q": "Top waiver adds", "intent": "waivers", "status": "CURRENT"},
    {"q": "Who should I stash on IR?", "intent": "stash", "status": "CURRENT"},
    {"q": "Best defense to stream", "intent": "defense_stream", "status": "CURRENT"},
    {"q": "Best DraftKings projection", "intent": "dfs", "status": "CURRENT"},
    {"q": "What player news matters most right now?", "intent": "news", "status": "CURRENT", "no_promo": True},
    {"q": "Any injury news?", "intent": "news", "status": "CURRENT", "no_promo": True},
    {"q": "Who will win the Super Bowl in 2035?", "intent": "help", "status": "UNKNOWN"},
]


def ask(question):
    req = urllib.request.Request(
        BASE,
        data=json.dumps({"question": question}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(req, timeout=10).read())


def main():
    results = []
    failures = []

    for case in CASES:
        payload = ask(case["q"])
        checks = {
            "intent": payload.get("intent") == case["intent"],
            "status": payload.get("status") == case["status"],
            "take_present": bool(str(payload.get("take") or "").strip()),
            "no_null_why": all(x is not None for x in (payload.get("why") or [])),
            "no_null_risk": all(x is not None for x in (payload.get("risk") or [])),
        }

        if case.get("needs_context"):
            checks["needs_context"] = (
                payload.get("confidence") == "NEEDS PLAYER CONTEXT"
                and "Tell me the players" in str(payload.get("take") or "")
            )

        if case.get("named_compare"):
            take = str(payload.get("take") or "")
            checks["named_compare"] = all(name in take for name in case["named_compare"])

        if case.get("no_promo"):
            take = str(payload.get("take") or "")
            checks["no_promo"] = not bool(
                re.search(r"promo|bonus|claim|sportsbook|betting app|free bet", take, re.I)
            )

        if case.get("no_high_juice_default"):
            cards = payload.get("cards") or []
            first = cards[0] if cards else {}
            market = str(first.get("market") or "").upper()
            line = first.get("line")
            checks["no_high_juice_default"] = not (
                market == "MONEYLINE"
                and isinstance(line, (int, float))
                and abs(line) >= 250
            )

        passed = all(checks.values())
        record = {
            "question": case["q"],
            "expected_intent": case["intent"],
            "actual_intent": payload.get("intent"),
            "expected_status": case["status"],
            "actual_status": payload.get("status"),
            "take": payload.get("take"),
            "confidence": payload.get("confidence"),
            "checks": checks,
            "passed": passed,
        }
        results.append(record)
        if not passed:
            failures.append(record)

    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": len(failures),
        "automatic_model_adjustment": False,
        "unknown_stays_unknown_tested": True,
        "results": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False))

    print(json.dumps({
        "cases": receipt["cases"],
        "passed": receipt["passed"],
        "failed": receipt["failed"],
        "output": str(OUT),
    }, indent=2))

    if failures:
        for failure in failures:
            print("FAIL:", failure["question"], failure["checks"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
