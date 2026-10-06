#!/usr/bin/env bash
set -euo pipefail
umask 077

ROOT="/home/ubuntu/sports-hulk"
BACKUP_ROOT="/home/ubuntu/sports-zenith-backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="${BACKUP_ROOT}/.work-${STAMP}"
OUT="${BACKUP_ROOT}/sports-zenith-state-${STAMP}.tar.gz"

mkdir -p "$BACKUP_ROOT" "$WORK"
chmod 700 "$BACKUP_ROOT"

cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

mkdir -p "$WORK/data" "$WORK/commercial_web" "$WORK/intelligence_warehouse"

if command -v sqlite3 >/dev/null 2>&1 && [ -f "$ROOT/data/sports_members.sqlite3" ]; then
  sqlite3 "$ROOT/data/sports_members.sqlite3" ".backup '$WORK/data/sports_members.sqlite3'"
elif [ -f "$ROOT/data/sports_members.sqlite3" ]; then
  cp "$ROOT/data/sports_members.sqlite3" "$WORK/data/"
fi

if [ -f "$ROOT/commercial_web/private_member_links.json" ]; then
  cp "$ROOT/commercial_web/private_member_links.json" "$WORK/commercial_web/"
fi

copy_if_exists() {
  local rel="$1"
  if [ -e "$ROOT/$rel" ]; then
    mkdir -p "$WORK/$(dirname "$rel")"
    cp -a "$ROOT/$rel" "$WORK/$rel"
  fi
}

copy_if_exists "intelligence_warehouse/public_performance/OFFICIAL_RECORD_POLICY.json"
copy_if_exists "intelligence_warehouse/public_performance/OFFICIAL_PUBLISHED_PICKS.jsonl"
copy_if_exists "intelligence_warehouse/fantasy_accountability/FANTASY_V2_FORWARD_LEDGER.jsonl"
copy_if_exists "intelligence_warehouse/fantasy_accountability/FANTASY_V2_FORWARD_SUMMARY.json"
copy_if_exists "intelligence_warehouse/survivor_accountability/SURVIVOR_V2_FORWARD_SUMMARY.json"
copy_if_exists "intelligence_warehouse/dfs_accountability/DFS_FORWARD_GRADES.json"
copy_if_exists "intelligence_warehouse/selectivity_shadow/SELECTIVITY_SHADOW_LEDGER.jsonl"
copy_if_exists "intelligence_warehouse/registry/SNAPSHOT_LEDGER.csv"

for f in "$ROOT"/intelligence_warehouse/betting_v2/*FORWARD_LEDGER.jsonl          "$ROOT"/intelligence_warehouse/betting_v2/*FORWARD_SUMMARY.json          "$ROOT"/intelligence_warehouse/betting_v2/BETTING_V2_PICK_LEDGER.jsonl; do
  [ -f "$f" ] || continue
  rel="${f#$ROOT/}"
  mkdir -p "$WORK/$(dirname "$rel")"
  cp "$f" "$WORK/$rel"
done

cat > "$WORK/BACKUP_MANIFEST.txt" <<EOF
Sports Zenith protected-state backup
Created UTC: $STAMP
Host: $(hostname)
Purpose: recovery of private member state and permanent forward/accountability records.
Explicitly excludes .env files, API keys, node_modules, build output and public score snapshots.
EOF

tar -C "$WORK" -czf "$OUT" .
chmod 600 "$OUT"
sha256sum "$OUT" > "${OUT}.sha256"
chmod 600 "${OUT}.sha256"

find "$BACKUP_ROOT" -maxdepth 1 -type f \( -name 'sports-zenith-state-*.tar.gz' -o -name 'sports-zenith-state-*.tar.gz.sha256' \) -mtime +7 -delete

echo "$OUT"
