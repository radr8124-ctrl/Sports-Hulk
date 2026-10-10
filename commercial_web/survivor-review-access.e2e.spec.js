import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_SURVIVOR_REVIEW_BASE||'http://127.0.0.1:8510/'

test('anonymous Survivor review has immediate sign-in shortcut, no private status leaked',async({page,request})=>{
 for(const width of [320,390,430,768,1280]){
  await page.setViewportSize({width,height:844})
  const res=await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  if(res)expect(res.status()).toBe(200)
  const access=page.getByRole('region',{name:'Survivor review access shortcut'})
  const deadline=page.getByRole('region',{name:'Survivor entry deadline'})
  await expect(access).toBeVisible()
  await expect(access.getByText('Sign in to see your entry',{exact:true})).toBeVisible()
  const boxes=await page.evaluate(()=>{
   const deadline=document.querySelector('[aria-label="Survivor entry deadline"]')
   const card=document.querySelector('[aria-label="Survivor review access shortcut"]')
   return {deadlineTop:Math.round(deadline.getBoundingClientRect().top),accessTop:Math.round(card.getBoundingClientRect().top),accessHeight:Math.round(card.getBoundingClientRect().height),overflow:document.documentElement.scrollWidth-innerWidth}
  })
  expect(boxes.accessTop).toBeGreaterThan(boxes.deadlineTop)
  expect(boxes.accessTop).toBeLessThan(width<=430?740:1000)
  expect(boxes.overflow).toBeLessThanOrEqual(1)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
  await expect(page.getByRole('region',{name:'Save this week Survivor picks'})).toHaveCount(0)
 }
 expect((await request.get(BASE+'api/survivor/state')).status()).toBe(401)
 expect((await request.post(BASE+'api/survivor/save-picks',{data:{entry_name:'ANNIE G 01',week:5,teams:['Jacksonville Jaguars']}})).status()).toBe(401)
})
