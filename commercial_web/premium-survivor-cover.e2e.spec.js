import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_SURVIVOR_PREMIUM_URL||'http://127.0.0.1:8510/'

test('Survivor desk premium cover never displays a private pick to anonymous visitors',async({page,request})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
 const cover=page.getByRole('region',{name:'Survivor premium command desk'})
 await expect(cover).toBeVisible()
 expect(await cover.evaluate(e=>getComputedStyle(e).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(cover.getByText('THE SURVIVOR DESK',{exact:true})).toBeVisible()
 await expect(cover.getByText('SIGN IN TO VIEW',{exact:true})).toBeVisible()
 await expect(cover.locator('[data-survivor-cover-metric="saved"]')).toContainText('—')
 await expect(cover.locator('[data-survivor-cover-metric="qualified"]')).toContainText('—')
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
 const reply=await request.get(BASE+'api/survivor/state')
 expect(reply.status()).toBe(401)
})

test('Survivor desk stays compact, deadline and editor remain in correct order',async({page})=>{
 for(const width of [320,390,430,768,1280]){
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  const cover=page.getByRole('region',{name:'Survivor premium command desk'})
  const deadline=page.getByRole('region',{name:'Survivor entry deadline'})
  await expect(cover).toBeVisible()
  await expect(deadline).toBeVisible()
  const size=await page.evaluate(()=>{
   const top=document.querySelector('[aria-label="Survivor premium command desk"]')
   const deadline=document.querySelector('[aria-label="Survivor entry deadline"]')
   return {coverTop:top.getBoundingClientRect().top,coverHeight:top.getBoundingClientRect().height,
    deadlineTop:deadline.getBoundingClientRect().top,overflow:document.documentElement.scrollWidth-innerWidth}
  })
  if(width<=430){ expect(size.coverHeight).toBeLessThan(290);expect(size.deadlineTop).toBeLessThan(550) }
  expect(size.coverTop).toBeLessThan(size.deadlineTop)
  expect(size.overflow).toBeLessThanOrEqual(1)
  await expect(deadline.getByText(/DOES NOT SUBMIT TO YOUR EXTERNAL POOL/)).toBeVisible()
  await expect(page.getByRole('region',{name:'Save this week Survivor picks'})).toHaveCount(0)
 }
})
