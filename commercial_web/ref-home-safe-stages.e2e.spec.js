import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
import {gunzipSync} from 'node:zlib'

const BASE=process.env.ZENITH_REF_DOCK_URL||'http://127.0.0.1:8510/'
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz',import.meta.url))).toString())
const clock=Date.parse(fixture.generated_at)+4*60_000
const areas=[
 {name:'signals',selector:'[aria-label="Home decision overview"]'},
 {name:'news',selector:'[aria-label="Home sports news"]'},
 {name:'picks',selector:'[aria-label="Home Fantasy Survivor and Brain Record"]'},
 {name:'learning',selector:'[aria-label="Home learning loop"]'},
]

async function setup(page,width=390) {
 await page.setViewportSize({width,height:844})
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.addInitScript(value=>Date.now=()=>value,clock)
 await page.route('**/ask_retrieval.json*',route=>route.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(fixture),
 }))
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await page.locator('.zenith-ref-mascot').waitFor({state:'visible'})
 await expect(page.locator('[aria-label="Home sports news"] [data-news-card]')).toHaveCount(4)
}

async function review(page,item) {
 await page.evaluate(selector=>document.querySelector(selector)?.scrollIntoView({block:'center',behavior:'instant'}),item.selector)
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await expect(ref).toHaveAttribute('data-section',item.name)
 await expect(ref).toHaveAttribute('data-mobile-docked','true')
 const stage=page.locator('[data-ref-safe-stage="'+item.name+'"]')
 await expect(stage).toBeVisible()
 const metrics=await page.evaluate(selector=>{
  const section=document.querySelector(selector)
  const stage=section.querySelector('[data-ref-safe-stage]')
  const aside=document.querySelector('[data-ref-companion]')
  const mascot=aside.querySelector('.zenith-ref-mascot')
  const r=mascot.getBoundingClientRect()
  const targetNodes=[...section.querySelectorAll('button,a,[data-news-card],[data-intelligence-card]')]
   .filter(e=>!aside.contains(e))
  const overlap=(a,b)=>Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left)) *
   Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top))
  const collisions=targetNodes.map(el=>({
   overlap:Math.round(overlap(r,el.getBoundingClientRect())),
   label:(el.textContent||'').replace(/\s+/g,' ').slice(0,30),
  })).filter(x=>x.overlap>0)
  const pos=getComputedStyle(aside)
  const nav=document.querySelector('nav[aria-label="Mobile primary navigation"]')
  return {
   docked:stage.contains(aside),position:pos.position,figureWidth:r.width,
   overlapArea:collisions.reduce((x,y)=>x+y.overlap,0),collisions,
   clearOfMobileNav:!nav||r.bottom<=nav.getBoundingClientRect().top+1||r.top>=nav.getBoundingClientRect().bottom,
   docOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
  }
 },item.selector)
 expect(metrics.docked).toBe(true)
 expect(metrics.position).toBe('absolute')
 expect(metrics.figureWidth).toBeGreaterThanOrEqual(108)
 expect(metrics.overlapArea).toBe(0)
 expect(metrics.clearOfMobileNav).toBe(true)
 expect(metrics.docOverflow).toBeLessThanOrEqual(1)
}

test('Ref performs from a safe on-page stage instead of covering the Home signal and News cards',async({page})=>{
 await setup(page)
 for(const area of areas)await review(page,area)
})

test('small phones keep full-body Ref and original clickable signal/news destinations',async({page})=>{
 await setup(page,320)
 for(const area of areas)await review(page,area)
 await expect(page.locator('[aria-label="Home decision overview"] [data-intelligence-card]')).toHaveCount(5)
 await expect(page.locator('[aria-label="Home sports news"] [data-news-card]')).toHaveCount(4)
 const links=await page.locator('[aria-label="Home sports news"] [data-news-card] a').evaluateAll(nodes=>nodes.map(a=>a.href))
 expect(links.every(x=>x.startsWith('http'))).toBe(true)
})

test('manual Ref controls still work from stage, and editing the controls undocks only when opened',async({page})=>{
 await setup(page)
 const news=areas[1]
 await page.evaluate(q=>document.querySelector(q).scrollIntoView({block:'center',behavior:'instant'}),news.selector)
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await expect(ref).toHaveAttribute('data-mobile-docked','true')
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await expect(ref).toHaveAttribute('data-expanded','true')
 await expect(ref).toHaveAttribute('data-mobile-docked','false')
 await ref.getByRole('button',{name:'The Ref throws a flag'}).click()
 await expect(ref).toHaveAttribute('data-signal','flag')
 await ref.getByRole('button',{name:'Close The Ref calls'}).click()
 await expect(ref).toHaveAttribute('data-mobile-docked','true')
})

test('desktop Ref remains fixed and preserves full-size sports magazine sideline',async({page})=>{
 await setup(page,1280)
 for(const area of areas){
  await page.evaluate(q=>document.querySelector(q).scrollIntoView({block:'center',behavior:'instant'}),area.selector)
  const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
  await expect(ref).toHaveAttribute('data-section',area.name)
  await expect(ref).toHaveAttribute('data-mobile-docked','false')
  const metrics=await ref.evaluate(node=>({parentInsideMain:document.querySelector('main')?.contains(node),position:getComputedStyle(node).position,width:node.querySelector('.zenith-ref-mascot').getBoundingClientRect().width}))
  expect(metrics.parentInsideMain).toBe(false)
  expect(metrics.position).toBe('fixed')
  expect(metrics.width).toBeGreaterThanOrEqual(145)
 }
})

test('News route without Home stages keeps its original companion and accessible controls',async({page})=>{
 await setup(page,390)
 await page.getByRole('button',{name:/All sports news/}).click()
 await expect(page).toHaveURL(/#news/)
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await expect(ref).toHaveAttribute('data-mobile-docked','false')
 await expect(ref.getByRole('button',{name:'Open The Ref animated sports companion'})).toBeVisible()
})

test('premium Home quicklinks remain swipeable, source-truthful and shorter than tall stacked mobile cards',async({page})=>{
 await setup(page,390)
 const section=page.getByRole('region',{name:'Home Fantasy Survivor and Brain Record'})
 const rail=section.locator('[data-home-snapshots-rail]')
 await expect(rail).toBeVisible()
 const cards=section.locator('[data-home-snapshot-card]')
 await expect(cards).toHaveCount(3)
 await expect(section.locator('[data-home-snapshot-card="survivor"]')).toBeVisible()
 const measurements=await page.evaluate(()=>{
  const section=document.querySelector('[aria-label="Home Fantasy Survivor and Brain Record"]')
  const rail=section.querySelector('[data-home-snapshots-rail]')
  return {height:section.getBoundingClientRect().height,swipe:rail.scrollWidth>rail.clientWidth+50,
   overflow:document.documentElement.scrollWidth-innerWidth}
 })
 expect(measurements.swipe).toBe(true)
 expect(measurements.height).toBeLessThan(565)
 expect(measurements.overflow).toBeLessThanOrEqual(1)
 await rail.evaluate(node=>node.scrollLeft=node.scrollWidth)
 await expect.poll(()=>rail.evaluate(node=>node.scrollLeft)).toBeGreaterThan(200)
 await expect(section.locator('[data-home-snapshot-card="brain"]')).toBeVisible()
 const body=await section.innerText()
 expect(body).not.toContain('ANNIE G 01')
 expect(body).toMatch(/Official|Brain Record/)
})

test('Learning Loop stays interactive without the Ref blocking any step or proof button',async({page})=>{
 await setup(page,390)
 const section=page.getByRole('region',{name:'Home learning loop'})
 await review(page,{name:'learning',selector:'[aria-label="Home learning loop"]'})
 const steps=section.getByRole('group',{name:'Choose a learning step'})
 await expect(steps.getByRole('button',{name:/Grade/})).toBeVisible()
 await steps.getByRole('button',{name:/Grade/}).click()
 await expect(steps.getByRole('button',{name:/Grade/})).toHaveAttribute('aria-pressed','true')
 await section.getByRole('button',{name:/See actual evidence and mistakes/}).click()
 await expect(page).toHaveURL(/#brain-record/)
})
