// Read-only production cross-platform browser smoke for Sports Zenith.
// This script never sends OTPs, saves picks, or makes sportsbook wagers.
const { chromium } = require('playwright')
const { writeFileSync, mkdirSync } = require('node:fs')
const { join, resolve } = require('node:path')
const assert = require('node:assert/strict')

const LIVE = 'https://sportszenith.com'
const pathToReport = process.argv[2] || 'reports/SPORTS_ZENITH_PRODUCTION_READ_ONLY_BROWSER_SMOKE.json'
const routes = [
  ['Home', ''], ['Scores', 'scores'], ['Best Bets', 'best-bets'],
  ['Props', 'props'], ['PrizePicks', 'prizepicks'], ['Parlays', 'parlays'],
  ['Bet Lab', 'bet-lab'], ['Fantasy', 'fantasy'],
  ['Survivor', 'survivor'], ['News', 'news'],
  ['Brain Record', 'brain-record'], ['Research', 'research'], ['Ask', 'ask'],
]
const profiles = [
  ['iPhone-small-simulated', 320, 694, true],
  ['iPhone-regular-simulated', 390, 844, true],
  ['tablet-simulated', 768, 1024, true],
  ['desktop-chromium', 1280, 900, false],
]
const q = (v) => String(v || '').replace(/\s+/g, ' ').slice(0, 115)
const uniqueErrors = (items) => [...new Set(items)]
const results = { schema: 'ZENITH_LIVE_READONLY_BROWSER_SMOKE_V1', started_at: new Date().toISOString(), origin: LIVE,
  routes: routes.map(x=>x[0]), results:[], read_only:true, wrote_picks:false,
  sent_otp:false, placed_wagers:false, platform_compilation_attempted:false }

async function smoke() {
  const browser = await chromium.launch({headless:true,args:['--no-sandbox']})
  try {
    for (const [name,w,h,mobile] of profiles) {
      const context = await browser.newContext({
        viewport: {width:w,height:h},
        isMobile: mobile, hasTouch: mobile, deviceScaleFactor: mobile?2:1,
        serviceWorkers:'allow', ignoreHTTPSErrors:false,
      })
      // Cloudflare injects RUM telemetry POSTs into public pages. Block them
      // in tests so this is strictly read-only toward the production domain.
      let blockedCloudflareTelemetry = 0
      await context.route(url => url.hostname === 'sportszenith.com' && url.pathname === '/cdn-cgi/rum', route=>{
        blockedCloudflareTelemetry += 1
        return route.fulfill({status:204,body:''})
      })
      const page = await context.newPage()
      const errors=[], externalPosts=[]
      page.on('pageerror',e=>errors.push(q(e.message)))
      page.on('request',req=>{
        const url = new URL(req.url())
        // Playwright fires request events even for the route-fulfilled telemetry.
        if (url.hostname === 'sportszenith.com' && url.pathname === '/cdn-cgi/rum') return
        if (!['GET','HEAD'].includes(req.method()) && url.hostname.endsWith('sportszenith.com'))
          externalPosts.push({method:req.method(),pathname:url.pathname})
      })
      for (const [label,hash] of routes) {
        const before=errors.length
        const url=LIVE+'/' + (hash ? '#'+hash : '')
        let response, status=0, data={}
        try {
          response=await page.goto(url,{waitUntil:'domcontentloaded',timeout:16000})
          status=response?.status() || 200
          await page.waitForFunction(()=>{
            const main=document.querySelector('main')
            return Boolean(main && (main.innerText?.length||0)>80)
          },{timeout:5000}).catch(()=>{})
          await page.waitForTimeout(375)
          data=await page.evaluate(()=>({
            hash:location.hash, title:document.title,
            charCount:document.querySelector('main')?.innerText?.length || 0,
            mainPreview:document.querySelector('main')?.innerText?.slice(0,100)||'',
            horizontalOverflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),
            mobileNavVisible: (()=>{const el=document.querySelector('nav[aria-label="Mobile primary navigation"]');return Boolean(el && getComputedStyle(el).display!=='none')})(),
            heading:document.querySelector('main h1')?.innerText?.slice(0,120)||null,
          }))
        } catch(err) {data.error=q(err?.message)}
        const entry={
          profile:name, viewport:w, route:label, expectedHash:hash, observedHash:data.hash||'',
          status, mainCharacters:data.charCount??0, firstHeading:q(data.heading),
          mobileNavVisible:data.mobileNavVisible||false, overflowPx:data.horizontalOverflow||0,
          error:data.error || null, newPageErrors:uniqueErrors(errors.slice(before)),
        }
        entry.pass=Boolean(status===200 && !entry.error && entry.mainCharacters>90 &&
          entry.observedHash === (hash?'#'+hash:'') &&
          entry.newPageErrors.length===0 &&
          entry.mobileNavVisible === (w<1024))
        results.results.push(entry)
        console.log((entry.pass?'PASS':'FAIL'),name,label,
          'content',entry.mainCharacters,'overflow',entry.overflowPx,'errors',entry.newPageErrors.length,
          entry.error||'')
      }
      if (name==='iPhone-regular-simulated') {
        try {
          await page.goto(LIVE+'/',{waitUntil:'domcontentloaded',timeout:12000})
          const button=page.getByRole('button',{name:'Sign in to Sports Zenith'}).first()
          await button.click({timeout:7000})
          const dialog=page.getByRole('dialog')
          const visible=await dialog.isVisible({timeout:7000})
          const inputs=await page.locator('input').count()
          results.authModal={view:'phone',opened:visible,numberOfInputs:inputs,
            OTP_sent:false,actual_account_login_tested:false}
          assert(visible,'Sign-in modal missing in mobile UI')
          console.log('PASS',name,'Sign in opens without sending OTP',inputs)
        }catch(e){results.authModal={opened:false,reason:q(e.message),OTP_sent:false};console.log('FAIL Sign in modal:',q(e.message))}
        try {
          await page.goto(LIVE+'/',{waitUntil:'domcontentloaded',timeout:12000})
          await page.evaluate(()=>navigator.serviceWorker.ready)
          const state=await page.evaluate(async()=>{
            const regs=await navigator.serviceWorker.getRegistrations(),names=await caches.keys()
            const paths=[]
            for(const n of names) {
              const cache=await caches.open(n)
              paths.push(...(await cache.keys()).map(req=>new URL(req.url).pathname))
            }
            return {registered:regs.length>0,cachedPaths:paths.sort()}
          })
          results.pwa={...state,staleDataCached:state.cachedPaths.some(p=>p.endsWith('.json')||p.startsWith('/api/'))}
          assert(state.registered && !results.pwa.staleDataCached)
          console.log('PASS PWA registration and no live JSON/secure data cached')
        }catch(e){results.pwa={error:q(e.message)}; console.log('FAIL PWA cache:',q(e.message))}
      }
      results[name]={browserRuntimeErrors:uniqueErrors(errors),productionWriteRequests:externalPosts,blockedCloudflareTelemetry}
      console.log('PROFILE_DONE',name,'errors=',errors.length,'writeRequests=',externalPosts.length,'telemetryIntercepted=',blockedCloudflareTelemetry)
      await context.close()
    }
  } finally {await browser.close()}
  results.finished_at=new Date().toISOString()
  results.passedRoutes=results.results.filter(x=>x.pass).length
  results.failedRoutes=results.results.length-results.passedRoutes
  results.totalRoutes=results.results.length
  results.testStatus=(results.failedRoutes===0 && results.pwa?.registered &&
    !results.pwa?.staleDataCached && results.authModal?.opened &&
    Object.entries(results).filter(([k])=>k.endsWith('simulated')||k==='desktop-chromium')
      .every(([,v])=>v.productionWriteRequests.length===0))?'PASS':'REVIEW_REQUIRED'
  const file=resolve(process.cwd(),'..',pathToReport)
  mkdirSync(require('node:path').dirname(file),{recursive:true})
  writeFileSync(file,JSON.stringify(results,null,2)+'\n')
  console.log('FINAL',results.testStatus,'routes',results.passedRoutes,'/',results.totalRoutes,'report',file)
  if(results.testStatus!=='PASS')process.exitCode=1
}
smoke().catch(e=>{console.error('SMOKE_HARNESS_FAILED',q(e.stack||e.message));process.exitCode=1})
