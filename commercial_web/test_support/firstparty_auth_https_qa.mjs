// Self-contained loopback HTTPS QA: real browser cookies, fake account only.
// NEVER connects to production or the real identity provider. Certs live in an
// ephemeral test directory and are removed when the Playwright suite ends.
import https from 'node:https'
import {createReadStream,readFileSync} from 'node:fs'
import fs from 'node:fs/promises'
import path from 'node:path'
import os from 'node:os'
import {execFileSync} from 'node:child_process'
import {build as viteBuild} from 'vite'
import {handleFirstPartyAuthProxy} from '../first_party_auth_proxy.js'

const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..')
const user={id:'00000000-0000-4000-8000-000000000042',email:'qa-returning-member@example.test',emailVerified:true,profile:{name:'Returning QA Member'}}
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json','.png':'image/png','.svg':'image/svg+xml'}
const cookie='insforge_refresh_token=SYNTHETIC_PROXY_COOKIE_TEST; Path=/api/auth; HttpOnly; Secure; SameSite=None; Max-Age=604800'
const clearCookie='insforge_refresh_token=; Path=/api/auth; HttpOnly; Secure; SameSite=None; Max-Age=0'
const jwt=()=>{
 const b=x=>Buffer.from(JSON.stringify(x)).toString('base64url')
 return [b({alg:'HS256',typ:'JWT'}),b({sub:user.id,email:user.email,exp:Math.round(Date.now()/1000)+3*3600}),'SYNTHETIC_LOCAL_TEST_ONLY'].join('.')
}

export async function startSyntheticAuthHttps(){
 const temp=await fs.mkdtemp(path.join(os.tmpdir(),'zenith-ios-auth-proxy-'))
 const stage=path.join(temp,'dist'),key=path.join(temp,'tls.key'),crt=path.join(temp,'tls.crt')
 try{
  execFileSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes',
   '-keyout',key,'-out',crt,'-days','1','-subj','/CN=127.0.0.1',
   '-addext','subjectAltName=IP:127.0.0.1'],{stdio:'ignore',timeout:12000})
  await fs.chmod(key,0o600)
  // Preserve active production dist! Vite never builds into live directory.
  await viteBuild({root,logLevel:'error',build:{outDir:stage,emptyOutDir:true}})
 }catch(error){await fs.rm(temp,{recursive:true,force:true});throw error}
 let metrics={refreshes:0,recovered:0,signins:0,signouts:0,calls:[]}
 const provider=async(url,{method,headers,body}={})=>{
  const route=new URL(url).pathname
  metrics.calls.push({route,method,had_refresh_cookie:Boolean(headers?.cookie?.includes('insforge_refresh_token=SYNTHETIC_PROXY_COOKIE_TEST'))})
  const answer=(status,json,setCookie)=>{
   const h=new Headers({'content-type':'application/json'})
   if(setCookie)h.append('set-cookie',setCookie)
   return new Response(JSON.stringify(json),{status,headers:h})
  }
  if(route==='/api/auth/public-config')return answer(200,{requireEmailVerification:false})
  if(route==='/api/auth/email/send-otp')return answer(200,{success:true})
  if(route==='/api/auth/sessions'){
   const pay=JSON.parse(body.toString('utf8'))
   if(pay.method!=='otp'||pay.otp!=='123456'||pay.email!==user.email)return answer(401,{error:'AUTH_UNAUTHORIZED'})
   metrics.signins++
   return answer(200,{accessToken:jwt(),user,csrfToken:'SYNTHETIC_CSRF'},cookie)
  }
  if(route==='/api/auth/refresh'){
   metrics.refreshes++
   if(!headers?.cookie?.includes('insforge_refresh_token=SYNTHETIC_PROXY_COOKIE_TEST')){
    return answer(401,{error:'AUTH_UNAUTHORIZED',message:'No synthetic session'},clearCookie)
   }
   metrics.recovered++
   return answer(200,{accessToken:jwt(),user,csrfToken:'SYNTHETIC_CSRF'},cookie)
  }
  if(route==='/api/auth/logout'){
   metrics.signouts++
   return answer(200,{success:true},clearCookie)
  }
  return answer(404,{error:'TEST_ONLY_AUTH_ROUTE_NOT_AVAILABLE'})
 }
 const server=https.createServer({key:readFileSync(key),cert:readFileSync(crt)},async(req,res)=>{
  const url=new URL(req.url,'https://127.0.0.1')
  if(req.method==='GET'&&url.pathname==='/qa-stats'){
   res.writeHead(200,{'content-type':'application/json','cache-control':'no-store'})
   return res.end(JSON.stringify(metrics))
  }
  if(req.method==='POST'&&url.pathname==='/qa-stats/reset'){
   metrics={refreshes:0,recovered:0,signins:0,signouts:0,calls:[]}
   res.writeHead(200,{'content-type':'application/json'});return res.end('{}')
  }
  if(url.pathname.startsWith('/api/auth')){
   return handleFirstPartyAuthProxy(req,res,{
    providerUrl:'https://synthetic-identity-provider.invalid',
    anonKey:'SYNTHETIC_ANON_KEY_ONLY',fetchImpl:provider,
   })
  }
  if(url.pathname.startsWith('/api/')){
   res.writeHead(401,{'content-type':'application/json'})
   return res.end('{"status":"SYNTHETIC_PRIVATE_ACCOUNT_NOT_AVAILABLE"}')
  }
  const requested=url.pathname==='/'?'/index.html':url.pathname
  let file=path.resolve(stage,'.'+requested)
  if(!file.startsWith(stage+path.sep)){
   res.writeHead(403);return res.end()
  }
  try{await fs.stat(file)}catch{
   if(url.pathname.includes('.')){res.writeHead(404);return res.end()}
   file=path.join(stage,'index.html')
  }
  res.writeHead(200,{'content-type':mime[path.extname(file)]||'application/octet-stream','cache-control':'no-store'})
  createReadStream(file).on('error',()=>res.destroy()).pipe(res)
 })
 try{
  await new Promise((resolve,reject)=>server.listen(0,'127.0.0.1',e=>e?reject(e):resolve()))
 }catch(error){await fs.rm(temp,{recursive:true,force:true});throw error}
 const port=server.address().port
 return {
  origin:`https://127.0.0.1:${port}/`,
  async close(){
   await new Promise(resolve=>server.close(()=>resolve()))
   await fs.rm(temp,{recursive:true,force:true})
  },
 }
}
