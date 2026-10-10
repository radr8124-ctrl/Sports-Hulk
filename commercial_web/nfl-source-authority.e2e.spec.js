import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_NFL_AUTHORITY_URL||'http://127.0.0.1:8510/'

test('NFL source health returns source identity counts without approved selections',async({request})=>{
 const response=await request.get(BASE+'api/nfl/book-source-health')
 expect(response.status()).toBe(200)
 const data=await response.json()
 expect(data.official_upcoming_games).toBeGreaterThan(0)
 expect(data.original_primary_matching_games).toBeGreaterThanOrEqual(0)
 expect(data.research_recent_paired_games).toBeGreaterThanOrEqual(0)
 expect(data.executability_verified).toBe(false)
 expect(data.independent_model_edge_verified).toBe(false)
 expect(data.qualified_selection_count).toBe(0)
 expect(data.no_approved_bet_or_survivor_pick_created).toBe(true)
 expect(JSON.stringify(data)).not.toContain('ANNIE G')
})

test('Survivor shows true source authority and no private anonymous picks',async({page})=>{
 for(const width of [320,390,768]){
  await page.setViewportSize({width,height:844})
  await page.goto(BASE+'#survivor',{waitUntil:'domcontentloaded'})
  const region=page.getByRole('region',{name:'NFL bookmaker source authority status'})
  await expect(region).toContainText('Primary feed')
  await expect(region).toContainText('Research archive')
  if(width<=430)await expect(region.getByText('NOT LIVE',{exact:true})).toBeVisible()
  else await expect(region.getByText('NOT VERIFIED LIVE OFFERS',{exact:true})).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
 }
})

test('Best Bets discloses original feed age and the separate archived book research',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#best-bets',{waitUntil:'domcontentloaded'})
 const region=page.getByRole('region',{name:'NFL bookmaker source authority status'})
 await expect(region).toContainText('Primary feed')
 await region.locator('summary').click()
 await expect(region).toContainText('Propline')
 await expect(region).toContainText('SportWizzard')
 await expect(region).toContainText('No independent model edge')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})
