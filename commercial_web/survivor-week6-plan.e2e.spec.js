import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_WEEK6_BASE||'http://127.0.0.1:8510/'

test('Week 6 schedule choices remain private to authenticated linked entry',async({request})=>{
 const response=await request.get(BASE+'api/survivor/week6-plan')
 expect(response.status()).toBe(401)
 expect(await response.json()).toMatchObject({status:'AUTH_REQUIRED'})
})

test('untrusted entry query never reveals other pool member source or used teams',async({request})=>{
 const response=await request.get(BASE+'api/survivor/week6-plan?entry='+encodeURIComponent('ANNIE G 01'))
 expect(response.status()).toBe(401)
 const text=await response.text()
 expect(text).not.toContain('Minnesota Vikings')
 expect(text).not.toContain('ANNIE G')
 expect(text).not.toContain('source_sha256')
})

test('logged-out Survivor does not mount private Week 6 interactive planner',async({page})=>{
 for(const width of [320,390,768]){
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  await expect(page.getByRole('region',{name:'Survivor entry deadline'})).toBeVisible()
  await expect(page.getByRole('region',{name:'Week 6 two-pick what-if planner'})).toHaveCount(0)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
 }
})
