// Read-only real-browser network failure regression for the live Zenith site.
// Uses browser connectivity emulation; this is not a physical iPhone/Android test.
const { chromium } = require('playwright')
const assert = require('node:assert/strict')

async function main() {
  const browser = await chromium.launch({headless:true,args:['--no-sandbox']})
  try {
    const context = await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true,serviceWorkers:'allow'})
    let cloudflareRumIntercepted=0
    await context.route(url=>url.hostname==='sportszenith.com' && url.pathname==='/cdn-cgi/rum',route=>{
      cloudflareRumIntercepted++
      return route.fulfill({status:204,body:''})
    })
    const page=await context.newPage(), errors=[], unexpectedWrites=[]
    page.on('pageerror',e=>errors.push(e.message))
    page.on('request',req=>{
      const u = new URL(req.url())
      if (u.hostname==='sportszenith.com' && !['GET','HEAD'].includes(req.method()) && u.pathname!=='/cdn-cgi/rum')
        unexpectedWrites.push(req.method()+' '+u.pathname)
    })
    const live=await page.goto('https://sportszenith.com/#scores',{waitUntil:'domcontentloaded',timeout:16000})
    assert.equal(live.status(),200)
    await page.waitForTimeout(200)
    const script=await page.evaluate(()=>document.querySelector('script[src*="pwa-init"]')?.getAttribute('src'))
    assert.equal(script,'/pwa-init.js?v=network-safety-2','live page not using the cache-busted network guard')
    const before=await page.evaluate(()=>({
      gate:!!document.getElementById('sports-zenith-connection-gate'),
      rootVisibility:document.getElementById('root').style.visibility,
    }))
    assert.equal(before.gate,false)

    await context.setOffline(true)
    await page.waitForTimeout(200)
    const offline=await page.evaluate(()=>({
      online:navigator.onLine,
      gated:!!document.getElementById('sports-zenith-connection-gate'),
      rootHidden:document.getElementById('root').style.visibility==='hidden',
      hiddenForAssistiveTech:document.getElementById('root').getAttribute('aria-hidden')==='true',
      notice:document.getElementById('sports-zenith-connection-gate')?.innerText.slice(0,300),
    }))
    assert.equal(offline.online,false)
    assert.equal(offline.gated,true)
    assert.equal(offline.rootHidden,true)
    assert.equal(offline.hiddenForAssistiveTech,true)
    assert.match(offline.notice,/scores, sportsbook prices and predictions are hidden/i)

    await page.goto('https://sportszenith.com/#survivor',{waitUntil:'domcontentloaded',timeout:16000})
    const route=await page.evaluate(()=>({
      hash:location.hash,
      gated:!!document.getElementById('sports-zenith-connection-gate'),
      rootHidden:document.getElementById('root').style.visibility==='hidden',
    }))
    assert.equal(route.hash,'#survivor')
    assert.equal(route.gated,true)
    assert.equal(route.rootHidden,true)

    await context.setOffline(false)
    await page.waitForTimeout(1800)
    const recovered=await page.evaluate(()=>({
      online:navigator.onLine,
      gated:!!document.getElementById('sports-zenith-connection-gate'),
      rootHidden:document.getElementById('root').style.visibility==='hidden',
      hash:location.hash,
    }))
    assert.equal(recovered.online,true)
    assert.equal(recovered.gated,false,'off-screen guard did not clear after verified API reconnect')
    assert.equal(recovered.rootHidden,false)
    assert.equal(recovered.hash,'#survivor')
    assert.deepEqual(errors,[])
    assert.deepEqual(unexpectedWrites,[])
    console.log('PASS: real HTTPS browser, offline event masks previous scores; offline navigation stays gated')
    console.log('PASS: reconnect checks Zenith API and refreshes the route before removing the gate')
    console.log('PASS: zero JavaScript errors; zero application POST/write requests')
    console.log('Cloudflare automatic RUM telemetry intercepted during test:',cloudflareRumIntercepted)
    await context.close()
  } finally {await browser.close()}
}
main().catch(e=>{console.error('FAILED: Sports Zenith live offline protection',e.message);process.exitCode=1})
