import {test,expect} from '@playwright/test'
const BASE=process.env.ZENITH_NFL_MODEL_BASE||'http://127.0.0.1:8510/'

test('read-only NFL model validation is publicly aggregate, with no private user records or false profit',async({request})=>{
 const res=await request.get(BASE+'api/nfl/model-validation',{timeout:16000})
 expect(res.status()).toBe(200)
 const body=await res.json()
 expect(body.status).toBe('AWAITING_INDEPENDENT_FINALS')
 expect(body.frozen_games).toBe(13)
 expect(body.official_final_games).toBe(0)
 expect(body.compared_games).toBe(0)
 expect(body.review_floor).toBe(30)
 expect(body.remaining_to_first_review).toBe(30)
 expect(body.independent_edge_proven).toBe(false)
 expect(body.official_bet_approved).toBe(false)
 expect(body.scores.raw_book_brier).toBeNull()
 expect(body.improvement_over_book).toBeNull()
 expect(body.retro_2025_result).toBe('NINE_FEATURE_MODEL_WORSE_THAN_RAW_BOOK')
 expect(body.forecast_source_sha256).toMatch(/^[a-f0-9]{64}$/)
 const text=JSON.stringify(body)
 expect(text).not.toContain('ANNIE G')
 expect(text).not.toContain('hulk_picks')
 expect(text).not.toContain('entry_name')
 expect(text).not.toContain('used_teams')
})

test('untrusted account query does not expose private entry details or shadow-pick names',async({request})=>{
 const res=await request.get(BASE+'api/nfl/model-validation?entry=ANNIE%20G%2001&include_private=true')
 expect(res.status()).toBe(200)
 const text=await res.text()
 expect(text).not.toContain('ANNIE G')
 expect(text).not.toContain('Dallas Cowboys')
 expect(text).not.toContain('market_baseline_picks')
})

test('Brain Record shows frozen vs matched outcomes without claiming a model advantage',async({page})=>{
 for (const width of [320,390,768,1280]){
  await page.setViewportSize({width,height:844})
  const response=await page.goto(BASE+'#brain-record',{waitUntil:'domcontentloaded',timeout:21000})
  if(response) expect(response.status()).toBe(200) // Same-page fragment reload may return null
  const section=page.getByRole('region',{name:'NFL model versus market validation'})
  await expect(section).toBeVisible()
  await expect(section.getByText('13',{exact:true}).first()).toBeVisible()
  await expect(section.getByText('0',{exact:true}).first()).toBeVisible()
  await expect(section.getByText(/2025.*worse than the raw bookmaker market/i)).toBeVisible()
  await expect(section.getByText(/No independent NFL model advantage has been proven/i)).toBeVisible()
  await expect(section.getByText(/Brier score and log loss are withheld until verified final game results/)).toBeVisible()
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
 }
})
