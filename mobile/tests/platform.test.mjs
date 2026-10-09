import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync, existsSync} from 'node:fs'
import {resolve} from 'node:path'
import {spawnSync} from 'node:child_process'
import {normalizeZenithApiOrigin} from '../../commercial_web/src/nativeApiBridge.js'

const root=resolve(import.meta.dirname,'..')
const conf=JSON.parse(readFileSync(resolve(root,'capacitor.config.json'),'utf8'))
const pkg=JSON.parse(readFileSync(resolve(root,'package.json'),'utf8'))
const android=readFileSync(resolve(root,'android/app/src/main/AndroidManifest.xml'),'utf8')
const gradle=readFileSync(resolve(root,'android/app/build.gradle'),'utf8')
const ios=readFileSync(resolve(root,'ios/App/App.xcodeproj/project.pbxproj'),'utf8')
const script=readFileSync(resolve(root,'scripts/build-web.mjs'),'utf8')

test('native platforms share one React frontend, not remote WebView server.url', () => {
  assert.equal(conf.appName,'Sports Zenith')
  assert.equal(conf.webDir,'www')
  assert.equal(conf.appId,'com.sportszenith.mobile')
  assert.equal(conf.server.url,undefined)
  assert.equal(conf.plugins.CapacitorHttp.enabled,true)
  assert.ok(existsSync(resolve(root,'../commercial_web/src/App.jsx')))
  assert.equal(pkg.dependencies['@capacitor/core'],'8.5.3')
  assert.equal(pkg.dependencies['@capacitor/android'],'8.5.3')
  assert.equal(pkg.dependencies['@capacitor/ios'],'8.5.3')
})

test('both platform source shells initialized with same provisional app identifier', () => {
  assert.match(gradle,/applicationId "com\.sportszenith\.mobile"/)
  assert.match(ios,/PRODUCT_BUNDLE_IDENTIFIER = com\.sportszenith\.mobile;/)
  assert.match(android, /android\.permission\.INTERNET/)
})

test('authenticated Android app does not permit automatic backup of local storage', () => {
  assert.match(android,/android:allowBackup="false"/)
  assert.doesNotMatch(android,/usesCleartextTraffic="true"/)
})

test('mobile release build refuses missing or raw-IP HTTP API', () => {
  const env={...process.env}
  delete env.ZENITH_MOBILE_API_ORIGIN
  const noEndpoint=spawnSync(process.execPath,[resolve(root,'scripts/build-web.mjs')],{cwd:root,env,encoding:'utf8',timeout:7000})
  assert.equal(noEndpoint.status,2,noEndpoint.stderr)
  assert.match(noEndpoint.stderr,/verified|HTTPS/)
  assert.equal(normalizeZenithApiOrigin('http://127.0.0.1:8510'),null)
  assert.equal(normalizeZenithApiOrigin('https://example.test'),'https://example.test')
})

test('native build directs the same original Vite React code to mobile/www, no model sources', () => {
  assert.match(script,/commercial_web/)
  assert.match(script,/VITE_MOBILE_API_ORIGIN/)
  assert.match(script,/--outDir/)
  assert.doesNotMatch(script,/mlb_live|betting_v2|nfl_live|CFB_RECOMMENDATION_LEDGER/)
})
