import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_PREFLIGHT_BASE||'http://127.0.0.1:8510/'

test('unlinked visitors cannot enumerate player injury evidence or used teams',async({request})=>{
 for(const target of ['','?entry='+encodeURIComponent('ANNIE G 01')+'&team='+encodeURIComponent('Jacksonville Jaguars')]){
  const response=await request.get(BASE+'api/survivor/preflight'+target)
  expect(response.status()).toBe(401)
  const text=await response.text()
  expect(text).not.toContain('ANNIE G 01')
  expect(text).not.toContain('Saquon Barkley')
  expect(text).not.toContain('current_picks')
 }
})

test('anon survivor shows no private source browser or member injury statuses',async({page})=>{
 for (const width of [320,390,768]) {
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  await expect(page.getByRole('region',{name:'Survivor entry deadline'})).toBeVisible()
  await expect(page.getByRole('region',{name:'Survivor source-verified injury and odds evidence'})).toHaveCount(0)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
 }
})
