import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {runInNewContext} from 'node:vm'
import { normalizeZenithApiOrigin, nativeZenithUrl, createZenithNativeFetch } from './src/nativeApiBridge.js'

const manifest = JSON.parse(readFileSync(new URL('./public/manifest.json',import.meta.url),'utf8'))
const sw = readFileSync(new URL('./public/sw.js',import.meta.url),'utf8')
const pwaInit = readFileSync(new URL('./public/pwa-init.js',import.meta.url),'utf8')
const html = readFileSync(new URL('./index.html',import.meta.url),'utf8')
const siteOrigin = 'https://zenith.example.test'

test('web manifest describes the existing site in standalone mobile mode', () => {
  assert.equal(manifest.short_name, 'Sports Zenith')
  assert.equal(manifest.start_url, '/')
  assert.equal(manifest.scope, '/')
  assert.equal(manifest.display, 'standalone')
  assert.equal(manifest.prefer_related_applications, false)
  for (const size of [192,512]) {
    const icon = manifest.icons.find(i => i.sizes === `${size}x${size}` && i.purpose === 'any')
    assert.ok(icon)
    const file = new URL('.'+icon.src,import.meta.url)
    const image = readFileSync(new URL('public/'+icon.src.slice(1),import.meta.url))
    assert.equal(image.toString('ascii',1,4),'PNG')
    assert.equal(image.readUInt32BE(16),size)
    assert.equal(image.readUInt32BE(20),size)
  }
  assert.ok(manifest.icons.some(i=>i.purpose==='maskable' && i.sizes==='512x512'))
  assert.match(html,/rel="manifest"/)
  assert.match(html,/rel="apple-touch-icon"/)
})

test('actual website PWA script registers only secure browser origins, never raw IP or native', () => {
  const urls=[]
  const execute=(protocol,hostname,{native=false,worker=true}={})=>{
    const window={
      location:{protocol,hostname},
      Capacitor:native?{isNativePlatform:()=>true}:undefined,
      addEventListener:(type,callback)=>{ if(type==='load')callback() },
    }
    const navigator=worker?{serviceWorker:{register:(url)=>{urls.push(url);return Promise.resolve()}}}:{}
    runInNewContext(pwaInit,{window,navigator})
  }
  execute('https:','zenith.example.test')
  assert.deepEqual(urls,['/sw.js'])
  execute('http:','192.0.2.1')
  execute('https:','zenith.example.test',{native:true})
  execute('https:','zenith.example.test',{worker:false})
  assert.deepEqual(urls,['/sw.js'])
  execute('http:','127.0.0.1')
  assert.deepEqual(urls,['/sw.js','/sw.js'])
})

test('service worker caches only offline fallback, never live scores, users, odds or app shell', () => {
  assert.match(sw,/req\.mode !== 'navigate'/)
  assert.match(sw,/url\.pathname\.startsWith\('\/api\/'\)/)
  assert.match(sw,/fetch\(req, \{cache: 'no-store'\}\)/)
  assert.doesNotMatch(sw,/cache\.put/)
  assert.doesNotMatch(sw,/\.json/)
  assert.doesNotMatch(sw,/caches\.match\(req\)/)
})

test('native API origin must be public HTTPS hostname, no credentials or path', () => {
  assert.equal(normalizeZenithApiOrigin(siteOrigin),siteOrigin)
  for (const unsafe of ['http://zenith.example.test','https://127.0.0.1','https://localhost',
                        'https://user:pass@zenith.example.test',
                        'https://zenith.example.test/admin','https://zenith.example.test?token=secret',
                        'file:///foo','',undefined]) {
    assert.equal(normalizeZenithApiOrigin(unsafe),null,String(unsafe))
  }
})

test('native routing changes only Zenith backend and read-only root JSON data', () => {
  assert.equal(nativeZenithUrl('/api/survivor/save-picks',siteOrigin),siteOrigin+'/api/survivor/save-picks')
  assert.equal(nativeZenithUrl('/nfl_scores.json?ts=123',siteOrigin),siteOrigin+'/nfl_scores.json?ts=123')
  assert.equal(nativeZenithUrl('/forward_proof_current.json',siteOrigin),siteOrigin+'/forward_proof_current.json')
  for (const untouched of ['/assets/index-digest.js','/manifest.json','/sw.js',
                          'https://other.example.test/api/health','//bad.example.test/api',
                          '/../api/private','/sports/nfl.json','/']) {
    assert.equal(nativeZenithUrl(untouched,siteOrigin),untouched,untouched)
  }
})

test('native fetch retains bearer headers and POST body; website fetch is untouched', async () => {
  const results=[]
  const original=async (url,opt)=>{results.push([url,opt]);return {ok:true}}
  const plain=createZenithNativeFetch(original,siteOrigin,false)
  assert.equal(plain,original)
  assert.throws(()=>createZenithNativeFetch(original,'http://127.0.0.1:8510',true),/verified HTTPS/)
  const native=createZenithNativeFetch(original,siteOrigin,true)
  const opts={method:'POST',headers:{Authorization:'Bearer TEST_ONLY'},body:JSON.stringify({picks:[]})}
  await native('/api/survivor/save-picks',opts)
  await native('https://unrelated.example/auth',{})
  assert.equal(results[0][0],siteOrigin+'/api/survivor/save-picks')
  assert.equal(results[0][1],opts)
  assert.equal(results[1][0],'https://unrelated.example/auth')
})
