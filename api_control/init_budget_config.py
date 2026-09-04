from pathlib import Path
import json

ROOT = Path("/home/ubuntu/sports-hulk")
CONFIG = ROOT / "api_control" / "api_budget_config.json"

if not CONFIG.exists():
    raise SystemExit("CONFIG FILE NOT CREATED")

data = json.loads(CONFIG.read_text())

print("=" * 80)
print("API BUDGET CONFIG CREATED")
print("=" * 80)

for provider, cfg in data["providers"].items():
    print(
        f"{provider:20} "
        f"limit={cfg.get('monthly_limit')} "
        f"priority={cfg.get('priority')}"
    )

print()
print("Reserve:", data.get("reserve_pct"), "%")
print("RESULT: PASS")
