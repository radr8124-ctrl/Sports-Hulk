import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_SURVIVOR_THURSDAY_URL||'http://127.0.0.1:8510/'
const payload={source_name:'Synthetic Thursday report — test only',reported_text:'TEST PERSON 01 COWBOYS',attested_dallas_only:true}

test('private Thursday summary rejects anonymous access and leaks no participant names',async({request})=>{
 const reply=await request.get(BASE+'api/survivor/thursday/summary')
 expect(reply.status()).toBe(401)
 const text=await reply.text()
 expect(text).not.toContain('DAWN')
 expect(text).not.toContain('ANNIE G')
})

test('anonymous reported Dallas list cannot be previewed or confirmed',async({request})=>{
 for (const kind of ['preview','confirm']){
  const reply=await request.post(BASE+'api/survivor/thursday/'+kind,{data:payload})
  expect(reply.status()).toBe(401)
  expect(await reply.json()).toMatchObject({status:'AUTH_REQUIRED'})
 }
})

test('public Survivor route remains anonymous and shows no Thursday list contents',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
 await expect(page.getByRole('region',{name:'Survivor entry deadline'})).toBeVisible()
 expect(await page.getByRole('region',{name:'Thursday Dallas Survivor elimination tracker'}).count()).toBe(0)
 expect((await page.locator('body').innerText()).includes('DAWN & MIKE BUCK')).toBe(false)
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})
