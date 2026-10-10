#!/usr/bin/env bash
# Build away from the production dist/ directory. Publish hashed assets first,
# then replace only index.html atomically. NO production directory deletion.
# No private account state, models, collector JSON, or pool results are touched.
set -Eeuo pipefail
ROOT=/home/ubuntu/sports-hulk
APP="$ROOT/commercial_web"
LIVE="$APP/dist"
BACKUPS="$ROOT/.deploy_backups"
if [[ ${1:-} != '--publish' || $# -ne 1 ]]; then
  echo 'Usage: publish_sports_zenith_frontend_atomic.sh --publish' >&2
  exit 2
fi
exec 9>/tmp/zenith_frontend_publisher.lock
flock -n 9 || { echo 'Another Zenith frontend publisher already holds the lock' >&2; exit 75; }
test -f "$LIVE/index.html" && test -d "$LIVE/assets"
runid=$(date -u +%Y%m%dT%H%M%SZ)-$$
stage="$BACKUPS/frontend_staged_$runid"
receipt="$BACKUPS/frontend_publish_$runid"
mkdir -p "$stage" "$receipt"
cp -p "$LIVE/index.html" "$receipt/prechange_index.html"
sha256sum "$receipt/prechange_index.html" > "$receipt/prechange_index.sha256"
cd "$APP"
# Vite may empty the output directory. It must NEVER be the LIVE dist folder.
./node_modules/.bin/vite build --outDir "$stage" --emptyOutDir > "$receipt/build.log" 2>&1
[[ -s "$stage/index.html" && -d "$stage/assets" ]] || { echo 'Vite stage output invalid; production unchanged' >&2; exit 1; }
# Confirm the new HTML references actual generated assets before copying any.
node --input-type=module - "$stage" <<'JS'
import {readFileSync,statSync} from 'node:fs'
import path from 'node:path'
const root=process.argv[2]
const html=readFileSync(path.join(root,'index.html'),'utf8')
const refs=[...html.matchAll(/(?:src|href)="\/assets\/([A-Za-z0-9_.-]+)"/g)].map(x=>x[1])
if(!refs.length||!refs.some(x=>x.endsWith('.js'))||!refs.some(x=>x.endsWith('.css')))throw Error('Missing actual hashed JS/CSS source references')
for(const ref of refs){const p=path.join(root,'assets',ref);if(!statSync(p).isFile())throw Error('Staged asset missing: '+ref)}
console.log('Verified new Vite HTML references',refs.length,'real staged JS/CSS assets')
JS
# Never delete old hashed assets: an existing open iPhone tab may still request
# the old chunk on a later lazy import. Preserve live refreshed public JSON.
rsync -a "$stage/assets/" "$LIVE/assets/"
name=".index.next.$runid.html"
cp -p "$stage/index.html" "$LIVE/$name"
test -s "$LIVE/$name"
# Same-directory rename is atomic on the production filesystem; no missing index.
mv -f "$LIVE/$name" "$LIVE/index.html"
if ! cmp -s "$LIVE/index.html" "$stage/index.html";then
  echo 'Atomic index readback mismatch: requiring operator review' >&2
  exit 1
fi
sha256sum "$LIVE/index.html" > "$receipt/published_index.sha256"
printf 'PUBLISHED_ATOMICALLY %s\n' "$runid"
printf 'Production index remained at %s throughout asset deployment\n' "$LIVE/index.html"
printf 'BACKUP_INDEX %s\n' "$receipt/prechange_index.html"
printf 'BUILD_LOG %s\n' "$receipt/build.log"
