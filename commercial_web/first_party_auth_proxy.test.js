import test from 'node:test'
import assert from 'node:assert/strict'
import {Readable} from 'node:stream'
import {handleFirstPartyAuthProxy, rewriteRefreshSetCookie, parseAllowedCookieHeader, AUTH_PROXY_ALLOWED_ROUTES} from './first_party_auth_proxy.js'

const base='https://4skbjfut.us-east.insforge.app'
const fakes=[]
function makeRequest(method,path,headers={},body=''){
 const data=Readable.from(body?[Buffer.from(body)]:[])
 data.method=method
 data.url=path
 data.headers={host:'sportszenith.com',...(method==='POST'?{origin:'https://sportszenith.com','content-type':'application/json'}:{}),...headers}
 return data
}
function makeReply(){
 return {status:null,headers:null,body:'',
  writeHead(status,headers){this.status=status;this.headers=headers},
  end(chunk=''){this.body+=String(chunk)},
 }
}
async function simulate(method,url,{headers={},body='',upstreamStatus=200,upstreamCookies=[],upstreamBody='{}',fetchImpl}={}){
 const req=makeRequest(method,url,headers,body),res=makeReply()
 const proxyFetch=fetchImpl||(async (source,options)=>{
  fakes.push({url:source,headers:options.headers,method:options.method,body:options.body})
  const h=new Headers({'content-type':'application/json'})
  for(const c of upstreamCookies)h.append('set-cookie',c)
  return new Response(upstreamBody,{status:upstreamStatus,headers:h})
 })
 await handleFirstPartyAuthProxy(req,res,{providerUrl:base,anonKey:'test-anon-key',fetchImpl:proxyFetch})
 return {res}
}

test('only narrowly allowlisted auth routes and methods, never arbitrary provider/DB paths',async()=>{
 assert.deepEqual(Object.keys(AUTH_PROXY_ALLOWED_ROUTES).sort(),[
  'GET /api/auth/public-config','GET /api/auth/sessions/current',
  'POST /api/auth/email/send-otp','POST /api/auth/logout',
  'POST /api/auth/refresh','POST /api/auth/sessions',
 ].sort())
 fakes.length=0
 for(const [method,path] of [
  ['GET','/api/auth/users'],['POST','/api/auth/users'],
  ['POST','/api/database/records/survivor_entries'],
  ['GET','/api/auth/admin/users'],['DELETE','/api/auth/sessions'],
  ['GET','/api/auth/refresh'],['POST','/api/auth/refresh?client_type=mobile'],
 ]){
  const {res}=await simulate(method,path)
  if(path.startsWith('/api/auth'))assert.equal(res.status,404,`${method} ${path}`)
 }
 assert.equal(fakes.length,0)
})

test('same-origin verification forwards only auth allowlisted POST to exact pinned provider URL',async()=>{
 fakes.length=0
 const {res}=await simulate('POST','/api/auth/email/send-otp',{
  body:JSON.stringify({email:'test@example.com'}),
  headers:{'user-agent':'Synthetic QA','x-evil-credentials':'shadow-secret','x-api-key':'invalid-user-override'},
  upstreamBody:JSON.stringify({success:true}),
 })
 assert.equal(res.status,200)
 assert.deepEqual(JSON.parse(res.body),{success:true})
 assert.equal(fakes.length,1)
 assert.equal(fakes[0].url,base+'/api/auth/email/send-otp')
 assert.equal(fakes[0].headers['x-api-key'],'test-anon-key')
 assert.equal(fakes[0].headers['x-evil-credentials'],undefined)
 assert.equal(fakes[0].headers['user-agent'],undefined)
 assert.equal(fakes[0].method,'POST')
 assert.equal(res.headers['cache-control'],'private, no-store, max-age=0')
})

test('SDK refresh and logout POST without body or Content-Type are allowed and retain cookie',async()=>{
 fakes.length=0
 for(const pathname of ['/api/auth/refresh','/api/auth/logout']){
  const {res}=await simulate('POST',pathname,{
   headers:{'content-type':undefined,cookie:'insforge_refresh_token=SYNTHETIC_COOKIE'},
   upstreamBody:JSON.stringify({success:true}),
  })
  assert.equal(res.status,200,pathname)
  assert.equal(fakes.at(-1).headers.cookie,'insforge_refresh_token=SYNTHETIC_COOKIE')
 }
 assert.equal(fakes.length,2)
})

test('cross-site POST, malicious Origin, and overly large payloads are rejected without provider calls',async()=>{
 fakes.length=0
 const blocked=await simulate('POST','/api/auth/refresh',{headers:{origin:'https://evil.test'}})
 assert.equal(blocked.res.status,403)
 const blockedFetch=await simulate('POST','/api/auth/refresh',{headers:{'sec-fetch-site':'cross-site'}})
 assert.equal(blockedFetch.res.status,403)
 const huge=await simulate('POST','/api/auth/sessions',{body:'X'.repeat(20_000)})
 assert.equal(huge.res.status,413)
 assert.equal(fakes.length,0)
})

test('only HttpOnly, Secure, SameSite=Lax first-party refresh cookie with no Domain or token leakage',async()=>{
 const original='insforge_refresh_token=MY_TEST_REFRESH_TOKEN; Path=/api/auth; Expires=Sun, 18 Oct 2026 23:07:46 GMT; HttpOnly; Secure; SameSite=None; Domain=external.example'
 const safe=rewriteRefreshSetCookie(original)
 assert.match(safe,/^insforge_refresh_token=MY_TEST_REFRESH_TOKEN;/)
 assert.match(safe,/Path=\/api\/auth/)
 assert.match(safe,/HttpOnly; Secure; SameSite=Lax/)
 assert.match(safe,/Expires=Sun, 18 Oct 2026/)
 assert.doesNotMatch(safe,/Domain=|SameSite=None/)
 assert.equal(rewriteRefreshSetCookie('evil=do-not-proxy; HttpOnly'),null)
 const {res}=await simulate('POST','/api/auth/sessions',{body:'{"method":"otp"}',
  upstreamBody:JSON.stringify({accessToken:'MOCKED_TOKEN',user:{id:'MOCKED'}}),
  upstreamCookies:[original,'other_browser_tracking=abc;Path=/;Secure'],
 })
 assert.equal(res.status,200)
 assert.equal(res.headers['set-cookie'].length,1)
 assert.equal(res.headers['set-cookie'][0],safe)
 assert.equal(JSON.parse(res.body).accessToken,'MOCKED_TOKEN')
})

test('only refresh cookie and benign CSRF forwarded, not other first party cookies or auth headers',async()=>{
 assert.equal(parseAllowedCookieHeader('insforge_refresh_token=abc; analytics_cookie=x; session=secret'),
  'insforge_refresh_token=abc')
 fakes.length=0
 const {res}=await simulate('POST','/api/auth/refresh',{
  headers:{cookie:'insforge_refresh_token=GOOD; analytics_cookie=BAD; another_secret=NO',
   'x-csrf-token':'test-csrf-token'},
  upstreamStatus:401,upstreamBody:'{"error":"UNAUTHORIZED"}',
  upstreamCookies:['insforge_refresh_token=; Path=/api/auth; Max-Age=0; HttpOnly; Secure; SameSite=None'],
 })
 assert.equal(res.status,401)
 assert.equal(fakes.length,1)
 assert.equal(fakes[0].headers.cookie,'insforge_refresh_token=GOOD')
 assert.equal(fakes[0].headers['x-csrf-token'],'test-csrf-token')
 assert.doesNotMatch(JSON.stringify(fakes[0].headers),/BAD|NO/)
 assert.match(res.headers['set-cookie'][0],/Max-Age=0/)
})

test('unavailable provider fails closed, does not leak origin or raw secret or claim auth success',async()=>{
 const {res}=await simulate('POST','/api/auth/refresh',{
  fetchImpl:async()=>{throw Error('secret private upstream network config')},
 })
 assert.equal(res.status,502)
 assert.match(res.body,/temporarily unavailable/i)
 assert.doesNotMatch(res.body,/secret|insforge\.app|token/)
})
