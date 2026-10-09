#!/usr/bin/env bash
# Repeatable public DNS/TLS/origin acceptance; prints no tunnel or user secrets.
set -euo pipefail

require_redirect="${1:-}"
if [[ -n "$require_redirect" && "$require_redirect" != "--require-redirect" ]]; then
  echo "Usage: $0 [--require-redirect]" >&2
  exit 2
fi

for host in sportszenith.com www.sportszenith.com; do
  address=$(dig @1.1.1.1 +time=4 +tries=1 +short "$host" A | head -n 1)
  if [[ -z "$address" ]]; then
    echo "FAIL: Public Cloudflare DNS missing for $host" >&2
    exit 3
  fi
  api_response=$(curl --fail --silent --show-error --max-time 12 "https://$host/api/health")
  python3 -c 'import json,sys; payload=json.load(sys.stdin); assert payload["status"]=="ok" and isinstance(payload.get("sources"),dict) and payload["sources"].get("nfl_scores") in [True,False]' <<< "$api_response"
  code_and_tls=$(curl --silent --show-error --max-time 12 --output /dev/null --write-out '%{http_code} %{ssl_verify_result}' "https://$host/")
  if [[ "$code_and_tls" != "200 0" ]]; then
    echo "FAIL: $host root must be HTTP 200 and have a valid public certificate; got $code_and_tls" >&2
    exit 4
  fi
  echo "PASS: $host DNS, certificate, API health and website"
  header_file=$(mktemp)
  trap 'rm -f "$header_file"' EXIT
  http_code=$(curl --silent --show-error --max-time 9 --output /dev/null --dump-header "$header_file" --write-out '%{http_code}' "http://$host/")
  location=$(grep -i '^location:' "$header_file" | tail -n 1 | tr -d '\r' || true)
  if [[ "$http_code" == "301" || "$http_code" == "302" || "$http_code" == "307" || "$http_code" == "308" ]]; then
    if [[ "$location" == *"https://$host"* ]]; then
      echo "PASS: HTTP upgrades to HTTPS for $host"
    else
      echo "FAIL: HTTP redirect destination is unexpected for $host: $location" >&2
      exit 5
    fi
  elif [[ "$require_redirect" == "--require-redirect" ]]; then
    echo "FAIL: HTTP->HTTPS redirect is not yet enabled for $host (HTTP $http_code)" >&2
    exit 6
  else
    echo "WARN: Enable Always Use HTTPS in Cloudflare for $host (HTTP $http_code)"
  fi
  rm -f "$header_file"
  trap - EXIT
done

auth_status=$(curl --silent --show-error --max-time 12 --output /dev/null --write-out '%{http_code}' "https://sportszenith.com/api/account/preferences")
if [[ "$auth_status" != "401" ]]; then
  echo "FAIL: unauthenticated account/preferences endpoint returned $auth_status instead of 401" >&2
  exit 7
fi
echo "PASS: authenticated account route rejects anonymous users"

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
if [[ "$(systemctl --user is-active sports-zenith-cloudflared.service)" != "active" ]] ||
   [[ "$(systemctl --user is-enabled sports-zenith-cloudflared.service)" != "enabled" ]]; then
  echo "FAIL: persistent Sports Zenith tunnel user service not active+enabled" >&2
  exit 8
fi
echo "PASS: tunnel user service active and enabled"
echo "RESULT: HTTPS production domain checks passed; redirect warnings (if any) are outstanding."
