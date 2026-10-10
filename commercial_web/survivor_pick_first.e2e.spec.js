import {test,expect} from '@playwright/test'
const BASE='http://127.0.0.1:8510/'

test('mobile Survivor shows real deadline and warning before market analysis',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
 const deadline=page.getByRole('region',{name:'Survivor entry deadline'})
 await expect(deadline).toBeVisible()
 await expect(deadline.getByText(/Pool deadline: Saturday 6 PM Eastern/)).toBeVisible()
 await expect(deadline.getByText(/DOES NOT SUBMIT TO YOUR EXTERNAL POOL/)).toBeVisible()
 const metrics=await page.evaluate(()=>({
  top:document.querySelector('[aria-label="Survivor entry deadline"]')?.getBoundingClientRect().top,
  overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 }))
 expect(metrics.top).toBeLessThan(510)
 expect(metrics.overflow).toBeLessThanOrEqual(1)
 await expect(page.getByRole('region',{name:'Save this week Survivor picks'})).toHaveCount(0)
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})

test('unauthenticated save remains blocked; only owner token may save',async({page,request})=>{
 const result=await request.post(BASE+'api/survivor/save-picks',{
  data:{entry_name:'ANNIE G 01',week:5,teams:['Houston Texans']},
 })
 expect(result.status()).toBe(401)
 const payload=await result.json()
 expect(payload.status).toBe('AUTH_REQUIRED')
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
 await expect(page.getByText(/Sign in for your picks and used-team history/)).toBeVisible()
 await expect(page.getByRole('region',{name:'Survivor entry deadline'})).toBeVisible()
})
