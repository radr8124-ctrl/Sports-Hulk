// First-party, HTTP-only InsForge auth-cookie relay for iPhone Safari.
// Only the six public self-service auth endpoints are exposed. NO admin,
// database, arbitrary URLs, redirects, account browsing or user impersonation.
// The provider's refresh cookie is kept HttpOnly + Secure on sportszenith.com.

export const AUTH_PROXY_ALLOWED_ROUTES=Object.freeze({
 'GET /api/auth/public-config':true,
 'GET /api/auth/sessions/current':true,
 'POST /api/auth/email/send-otp':true,
 'POST /api/auth/sessions':true,
 'POST /api/auth/refresh':true,
 'POST /api/auth/logout':true,
})
const MAX_REQUEST_BYTES=8192
const MAX_RESPONSE_BYTES=65536
const COOKIE_NAME='insforge_refresh_token'

export function parseAllowedCookieHeader(header){
 if(typeof header!=='string')return ''
 const parts=header.split(';')
 for(const part of parts){
  const match=/^\s*insforge_refresh_token=([^\s;,\r\n]*)\s*$/.exec(part)
  if(match&&match[1].length<=5000)return `${COOKIE_NAME}=${match[1]}`
 }
 return ''
}

export function rewriteRefreshSetCookie(original){
 if(typeof original!=='string'||original.length>9000)return null
 const [head,...parts]=original.split(';').map(x=>x.trim())
 const matches=/^insforge_refresh_token=([^\r\n;]*)$/.exec(head||'')
 if(!matches||matches[1].length>5000)return null
 const extra=[]
 for(const item of parts){
  const maxAge=/^Max-Age=(-?\d{1,12})$/i.exec(item)
  if(maxAge)extra.push('Max-Age='+maxAge[1])
  const expires=/^Expires=(.+)$/i.exec(item)
  if(expires){
   const moment=Date.parse(expires[1])
   if(Number.isFinite(moment))extra.push('Expires='+new Date(moment).toUTCString())
  }
 }
 // Secure always; HttpOnly refresh credentials never available to page scripts.
 // SameSite=Lax permits same-site calls but denies cross-site CSRF POST cookies.
 return [head,'Path=/api/auth',...extra,'HttpOnly','Secure','SameSite=Lax'].join('; ')
}

function sendJson(res,status,body){
 res.writeHead(status,{
  'content-type':'application/json; charset=utf-8',
  'cache-control':'private, no-store, max-age=0',
  'x-content-type-options':'nosniff',
  'x-frame-options':'DENY',
  'referrer-policy':'no-referrer',
 })
 res.end(JSON.stringify(body))
}
async function safeReadBody(req){
 const result=[]
 let size=0
 for await(const part of req){
  const buf=Buffer.isBuffer(part)?part:Buffer.from(part)
  size+=buf.length
  if(size>MAX_REQUEST_BYTES)throw Error('AUTH_BODY_TOO_LARGE')
  result.push(buf)
 }
 return Buffer.concat(result)
}
function safeOrigin(req){
 const host=String(req.headers?.host||'')
 if(!host||host.length>255||/[\s/\\]/.test(host))return false
 const origin=req.headers?.origin
 if(origin){
  try{
   if(new URL(origin).host.toLowerCase()!==host.toLowerCase())return false
  }catch{return false}
 }
 const site=String(req.headers?.['sec-fetch-site']||'').toLowerCase()
 return !['cross-site','same-site'].includes(site)
}

export async function handleFirstPartyAuthProxy(req,res,{
 providerUrl,anonKey,fetchImpl=fetch,
}={}){
 const requestUrl=String(req.url||'')
 let location
 try{location=new URL(requestUrl,'http://localhost')}
 catch{sendJson(res,400,{status:'BAD_REQUEST'});return true}
 if(!location.pathname.startsWith('/api/auth'))return false
 const key=String(req.method||'')+' '+location.pathname
 if(location.search||!Object.hasOwn(AUTH_PROXY_ALLOWED_ROUTES,key)){
  sendJson(res,404,{status:'AUTH_ROUTE_NOT_AVAILABLE'});return true
 }
 if(!providerUrl||!anonKey||!/^https:\/\/[^/]+$/.test(providerUrl)){
  sendJson(res,503,{status:'AUTH_NOT_CONFIGURED'});return true
 }
 if(!safeOrigin(req)){
  sendJson(res,403,{status:'AUTH_REQUEST_ORIGIN_DENIED'});return true
 }
 const isPost=req.method==='POST'
 const length=Number(req.headers?.['content-length']||0)
 if(!Number.isFinite(length)||length>MAX_REQUEST_BYTES){
  sendJson(res,413,{status:'AUTH_REQUEST_TOO_LARGE'});return true
 }
 // Email OTP and session creation require JSON credentials. InsForge's
 // browser refresh/logout POST requests intentionally carry NO body or
 // content-type, so rejecting those would sign out every returning Safari tab.
 const requiresJson=['POST /api/auth/email/send-otp','POST /api/auth/sessions'].includes(key)
 if(requiresJson&&!/^application\/json(?:\s*;|\s*$)/i.test(String(req.headers?.['content-type']||''))){
  sendJson(res,415,{status:'AUTH_JSON_REQUIRED'});return true
 }
 let body
 try{body=isPost?await safeReadBody(req):undefined}
 catch{sendJson(res,413,{status:'AUTH_REQUEST_TOO_LARGE'});return true}
 if(isPost&&body.length && (!requiresJson || !body.toString('utf8').trim().startsWith('{'))){
  sendJson(res,400,{status:'AUTH_BODY_NOT_JSON_OBJECT'});return true
 }
 const cookie=parseAllowedCookieHeader(req.headers?.cookie)
 const headers={
  'x-api-key':anonKey,
  'accept':'application/json',
  ...(isPost?{'content-type':'application/json'}:{}),
  ...(cookie?{cookie}:{}),
 }
 const csrf=req.headers?.['x-csrf-token']
 if(typeof csrf==='string'&&/^[A-Za-z0-9_\-+/=.]{1,512}$/.test(csrf)){
  headers['x-csrf-token']=csrf
 }
 const auth=req.headers?.authorization
 if(key==='GET /api/auth/sessions/current' &&
    typeof auth==='string'&&/^Bearer [A-Za-z0-9._~+/-]{10,8192}$/.test(auth)){
   headers.authorization=auth
 }
 try{
  // Constant pinned provider host: never proxy a user-provided URL.
  const response=await fetchImpl(providerUrl+location.pathname,{
   method:req.method,headers,
   ...(isPost?{body:body.length?body:undefined}:{}),
   redirect:'manual',signal:AbortSignal.timeout(12000),
  })
  const safeCode=response.status
  if(safeCode<200||safeCode>=500||safeCode>=300&&safeCode<400){
   sendJson(res,502,{status:'AUTH_PROVIDER_TEMPORARILY_UNAVAILABLE'});return true
  }
  const bytes=Buffer.from(await response.arrayBuffer())
  if(bytes.length>MAX_RESPONSE_BYTES){
   sendJson(res,502,{status:'AUTH_PROVIDER_RESPONSE_INVALID'});return true
  }
  const content=String(response.headers.get('content-type')||'')
  if(!content.includes('json')){
   sendJson(res,502,{status:'AUTH_PROVIDER_RESPONSE_INVALID'});return true
  }
  const responseHeaders={
   'content-type':'application/json; charset=utf-8',
   'cache-control':'private, no-store, max-age=0',
   'x-content-type-options':'nosniff',
   'x-frame-options':'DENY',
   'referrer-policy':'no-referrer',
  }
  const originalCookies=response.headers.getSetCookie?.()||[]
  const mappedCookies=originalCookies.map(rewriteRefreshSetCookie).filter(Boolean)
  if(mappedCookies.length)responseHeaders['set-cookie']=mappedCookies
  res.writeHead(safeCode,responseHeaders)
  res.end(bytes)
  return true
 }catch{
  sendJson(res,502,{status:'AUTH_PROVIDER_TEMPORARILY_UNAVAILABLE',
   message:'The account service is temporarily unavailable. Please try again.'})
  return true
 }
}
