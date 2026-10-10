import {test,expect} from '@playwright/test'
import {createServer} from 'vite'
import {fileURLToPath} from 'node:url'
import path from 'node:path'
const ROOT=path.dirname(fileURLToPath(import.meta.url))
let vite,local

test.beforeAll(async()=>{
 vite=await createServer({root:ROOT,logLevel:'error',server:{host:'127.0.0.1',port:0,strictPort:false}})
 await vite.listen()
 local='http://127.0.0.1:'+vite.httpServer.address().port+'/review_harness_survivor/index.html'
})
test.afterAll(async()=>{await vite?.close()})
async function open(page,width=390){
 await page.setViewportSize({width,height:844})
 await page.route('**/api/**',async route=>{
  expect(new URL(route.request().url()).origin).toBe(new URL(local).origin)
  const r=route.request()
  expect(r.method()).toBe('GET') // no writes to real or mocked pool
  await route.fulfill({status:403,contentType:'application/json',body:'{"status":"SYNTHETIC_QA_ONLY"}'})
 })
 const response=await page.goto(local,{waitUntil:'domcontentloaded'})
 expect(response.status()).toBe(200)
 return page.getByRole('region',{name:'Survivor next round readiness'})
}

test('authenticated synthetic Survivor handoff shows missing organizer Week5 sheet, not fake Week6 qualification',async({page})=>{
 const box=await open(page)
 await expect(box).toHaveAttribute('data-next-round-status','AWAITING_OFFICIAL_WEEK5_SHEET')
 await expect(box).toContainText('Week 5 organizer confirmation still needed')
 await expect(box).toContainText('CONFIRMATION PENDING')
 await expect(box).toContainText('Latest official week')
 await expect(box).toContainText('Week 6 required')
 await expect(box).toContainText('The official pool sheet on file covers an earlier week')
 const coords=await page.evaluate(()=>({
  history:document.querySelector('[data-survivor-past-picks]').getBoundingClientRect().top,
  handoff:document.querySelector('[data-survivor-next-round-readiness]').getBoundingClientRect().top,
  editor:document.querySelector('[aria-label="Save this week Survivor picks"]').getBoundingClientRect().top,
 }))
 expect(coords.history).toBeLessThan(coords.handoff)
 expect(coords.handoff).toBeLessThan(coords.editor)
 await box.locator('summary').click()
 await expect(box).toContainText('Reported Thursday losses and research-only scores cannot certify this entry.')
})

test('the compact source/next-round card stays within iPhone and desktop widths',async({page})=>{
 for(const width of [320,390,430,768,1280]){
  const box=await open(page,width)
  await expect(box).toBeVisible()
  const rect=await box.boundingBox()
  expect(rect.width).toBeLessThanOrEqual(width)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  if(width===390)await box.screenshot({path:'/tmp/zenith_next_round_readiness_390_oct10.png'})
 }
})

test('real anonymous production does not publish private Week 5 or Week 6 handoff records',async({request,page})=>{
 const r=await request.get('https://sportszenith.com/api/survivor/state')
 expect(r.status()).toBe(401)
 const body=await r.text()
 expect(body).not.toContain('next_round_readiness')
 expect(body).not.toContain('ANNIE G')
 await page.goto('https://sportszenith.com/#survivor',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('region',{name:'Survivor next round readiness'})).toHaveCount(0)
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})
