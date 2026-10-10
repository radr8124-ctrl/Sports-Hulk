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

async function syntheticOwner(page,width=390){
 await page.setViewportSize({width,height:844})
 // Block ALL synthetic QA requests from ever reaching production, even if a
 // future teammate adds a new endpoint to the test harness.
 await page.route('**/api/**',async route=>{
  const u=new URL(route.request().url())
  expect(u.origin).toBe(new URL(local).origin)
  if(u.pathname==='/api/survivor/pool-manager'){
   return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({can_manage:false})})
  }
  return route.fulfill({status:401,contentType:'application/json',body:JSON.stringify({status:'TEST_BARRIER_NO_MUTATIONS'})})
 })
 const response=await page.goto(local,{waitUntil:'domcontentloaded'})
 if(response)expect(response.status()).toBe(200)
 await page.getByRole('region',{name:'My Survivor past picks'}).waitFor()
 return page.getByRole('region',{name:'My Survivor past picks'})
}

test('four recorded weeks and five preserved private picks appear immediately before edit, not just latest week',async({page})=>{
 const root=await syntheticOwner(page)
 await expect(root).toHaveAttribute('data-past-history-status','RECORDED_HISTORY_COMPLETE')
 await expect(root.getByText('5 PICKS · 4 WEEKS')).toBeVisible()
 await expect(root.locator('[data-past-week]')).toHaveCount(4)
 await expect(root.locator('[data-past-pick]')).toHaveCount(5)
 for(const [week,team] of [[1,'Los Angeles Chargers'],[2,'San Francisco 49ers'],
  [3,'Kansas City Chiefs'],[3,'Buffalo Bills'],[4,'Minnesota Vikings']]){
  const group=root.locator(`[data-past-week="${week}"]`)
  await expect(group.locator(`[data-past-pick="${team}"]`)).toContainText('SURVIVED')
 }
 await expect(root).toContainText('Week 5: No pick saved in Zenith')
 const layout=await page.evaluate(()=>({
  timelineTop:document.querySelector('[data-survivor-past-picks]').getBoundingClientRect().top,
  editorTop:document.querySelector('[aria-label="Save this week Survivor picks"]').getBoundingClientRect().top,
  overflow:document.documentElement.scrollWidth-innerWidth,
 }))
 expect(layout.timelineTop).toBeLessThan(layout.editorTop)
 expect(layout.overflow).toBeLessThanOrEqual(1)
 await root.locator('summary').click()
 await expect(root).toContainText('This pick is marked confirmed on the imported official pool sheet')
 await expect(root).toContainText('External submission information is unavailable in the saved record')
})

test('recorded past results remain readable across phone, tablet and desktop widths',async({page})=>{
 for(const width of [320,390,430,768,1280]){
  const root=await syntheticOwner(page,width)
  const rect=await root.boundingBox()
  const metrics=await page.evaluate(()=>({width:document.documentElement.scrollWidth,inner:innerWidth,
   total:document.querySelectorAll('[data-survivor-past-picks] [data-past-pick]').length,
   weeks:document.querySelectorAll('[data-survivor-past-picks] [data-past-week]').length}))
  expect(metrics.total).toBe(5)
  expect(metrics.weeks).toBe(4)
  expect(metrics.width-metrics.inner).toBeLessThanOrEqual(1)
  expect(rect.width).toBeLessThanOrEqual(width)
  if(width===390)await root.screenshot({path:'/tmp/zenith_survivor_full_past_picks_390_oct10.png'})
 }
})

test('anonymous real production remains unable to see previous private ticket history',async({request,page})=>{
 const path='https://sportszenith.com/'
 const res=await request.get(path+'api/survivor/state')
 expect(res.status()).toBe(401)
 expect((await res.text()).includes('Los Angeles Chargers')).toBe(false)
 await page.goto(path+'#survivor',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('region',{name:'My Survivor past picks'})).toHaveCount(0)
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})
