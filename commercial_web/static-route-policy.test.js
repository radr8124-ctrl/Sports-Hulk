import test from 'node:test'
import assert from 'node:assert/strict'
import { missingStaticResourceKind, pathIsInsideDir } from './staticRoutePolicy.js'

test('existing client-side routes remain SPA navigations',()=>{
  for(const p of ['/','/research','/fantasy','/survivor','/some/unknown/route','/index.html']){
    assert.equal(missingStaticResourceKind(p),'SPA_FALLBACK',p)
  }
})

test('missing JSON and JS data now receive real 404 responses, never a 200 HTML page',()=>{
  for(const p of [
    '/props_v2_current.json','/this-is-not-a-real.json','/assets/bundle-missing.js',
    '/assets/theme.css','/favicon.ico','/missing.xml','/missing.csv',
  ]) assert.equal(missingStaticResourceKind(p),'STATIC_NOT_FOUND',p)
  assert.equal(missingStaticResourceKind('/thing.json?v=123'),'STATIC_NOT_FOUND')
})

test('unknown API endpoints are distinct from SPA fallback and cannot masquerade as healthy',()=>{
  for(const p of ['/api','/api/unknown','/api/not-a-real.json']){
    assert.equal(missingStaticResourceKind(p),'API_NOT_FOUND',p)
  }
})

test('static path containment requires path delimiter, not shared prefix',()=>{
  assert.equal(pathIsInsideDir('/home/site/dist','/home/site/dist/index.html'),true)
  assert.equal(pathIsInsideDir('/home/site/dist','/home/site/dist/assets/index.js'),true)
  assert.equal(pathIsInsideDir('/home/site/dist','/home/site/dist'),true)
  assert.equal(pathIsInsideDir('/home/site/dist','/home/site/dist-evil/index.html'),false)
  assert.equal(pathIsInsideDir('/home/site/dist','/home/site/dist/../.env'),false)
  assert.equal(pathIsInsideDir('/home/site/dist','/etc/passwd'),false)
})
