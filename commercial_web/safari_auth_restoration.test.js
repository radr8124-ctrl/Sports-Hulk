import test from 'node:test'
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
const auth=readFileSync(new URL('./src/AuthShell.jsx',import.meta.url),'utf8')
const client=readFileSync(new URL('./src/insforge.js',import.meta.url),'utf8')
const server=readFileSync(new URL('./server.js',import.meta.url),'utf8')

test('returning Safari account does not depend on a localStorage flag to restore a verified cookie',()=>{
 assert.doesNotMatch(auth,/const AUTH_HINT\s*=/)
 assert.doesNotMatch(auth,/localStorage\.(getItem|setItem|removeItem)/)
 assert.match(auth,/insforge\.auth\.getCurrentUser\(\)/)
 assert.match(auth,/Promise\.allSettled\(/)
 assert.match(auth,/refreshUser\(\),/)
 assert.match(auth,/refreshInFlight\.current/)
})
test('auth session retries on iPhone bfcache/visibility without clearing user for transient network failures',()=>{
 assert.match(auth,/document\.addEventListener\('visibilitychange'/)
 assert.match(auth,/window\.addEventListener\('pageshow'/)
 assert.match(auth,/event\.persisted/)
 assert.match(auth,/Number\(error\.statusCode\)/)
 assert.match(auth,/version !== sessionGeneration\.current/)
 assert.doesNotMatch(auth,/catch\s*\{\s*setUser\(null\)/)
})
test('main web application uses first-party origin, never stores JWT or refresh token in localStorage',()=>{
 assert.match(client,/window\.location\.origin/)
 assert.match(client,/import\.meta\.env\.PROD/)
 assert.match(client,/baseUrl:firstPartyAuthOrigin \|\| baseUrl/)
 assert.doesNotMatch(client,/localStorage|sessionStorage|setCookie/)
 assert.match(server,/handleFirstPartyAuthProxy/)
 assert.match(server,/anonKey:process\.env\.VITE_INSFORGE_ANON_KEY/)
})
test('backend still demands bearer JWT for original private Survivor APIs; no cookie-only bypass',()=>{
 const privateSource=server.slice(server.indexOf('async function authenticatedUser('),server.indexOf('function poolManagerPermitted'))
 assert.match(privateSource,/scopedInsForgeClient\(req\)/)
 assert.match(server,/function bearerToken\(req\)/)
 assert.doesNotMatch(privateSource,/Cookie|cookie|AUTH_HINT/)
})
