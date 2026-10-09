import {spawnSync} from 'node:child_process'
import {existsSync, readFileSync, readdirSync} from 'node:fs'
import {resolve, dirname} from 'node:path'
import {fileURLToPath} from 'node:url'
import {normalizeZenithApiOrigin} from '../../commercial_web/src/nativeApiBridge.js'
import {stripNativeRuntimeSnapshots,assertNoNativeSnapshotJSON} from './snapshot-safety.mjs'

const mobile=resolve(dirname(fileURLToPath(import.meta.url)),'..')
const site=resolve(mobile,'../commercial_web')
const target=resolve(mobile,'www')
const origin=normalizeZenithApiOrigin(process.env.ZENITH_MOBILE_API_ORIGIN)
if (!origin) {
  console.error('Mobile bundle blocked: provide your authorized public HTTPS Zenith API as ZENITH_MOBILE_API_ORIGIN.')
  process.exit(2)
}
const main=resolve(site,'package.json')
if (!existsSync(main)) throw new Error('Shared Zenith website source missing.')
// Syntax-valid HTTPS is not enough: verify TLS, remote routing, and Zenith
// health data before embedding a destination into a production mobile bundle.
let health
try {
  const response=await fetch(origin+'/api/health',{
    signal:AbortSignal.timeout(6000),redirect:'error',cache:'no-store',
  })
  if (!response.ok || new URL(response.url).origin!==origin) throw new Error('Status/redirect')
  health=await response.json()
} catch {
  console.error('Mobile bundle blocked: HTTPS host failed real Sports Zenith /api/health verification.')
  process.exit(6)
}
if (health?.status!=='ok' || !health.sources ||
    typeof health.sources.nfl_scores!=='boolean' ||
    typeof health.sources.mlb_scores!=='boolean') {
  console.error('Mobile bundle blocked: HTTPS host is not the expected Sports Zenith API.')
  process.exit(7)
}
const runner=spawnSync('npm',['run','build','--','--outDir',target,'--emptyOutDir'],{
  cwd:site,stdio:'inherit',
  env:{...process.env,VITE_MOBILE_API_ORIGIN:origin},
})
if (runner.error || runner.status!==0) process.exit(runner.status || 3)
const snapshotsRemoved=stripNativeRuntimeSnapshots(target)
assertNoNativeSnapshotJSON(target)
console.log('Removed mutable website JSON snapshots from native package:',snapshotsRemoved.length)
const index=readFileSync(resolve(target,'index.html'),'utf8')
const assets=readdirSync(resolve(target,'assets'))
if (!index.includes('manifest.json') || !assets.some(x=>x.startsWith('index-')&&x.endsWith('.js'))) {
  console.error('Mobile React bundle missing required web assets. Do not sync native platforms.')
  process.exit(4)
}
const scripts=assets.filter(x=>x.endsWith('.js')).map(x=>readFileSync(resolve(target,'assets',x),'utf8')).join('\n')
if (!scripts.includes(origin)) {
  console.error('Mobile React bundle not configured to call the verified HTTPS server. Do not publish.')
  process.exit(5)
}
console.log('Zenith mobile React bundle staged. Real native device/auth testing and store approval still required.')
