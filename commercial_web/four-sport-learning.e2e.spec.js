import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const fixture=JSON.parse(readFileSync(new URL('./public/zenith_sport_cohorts.json',import.meta.url),'utf8'))
const learning=JSON.parse(readFileSync(new URL('./public/zenith_learning_review.json',import.meta.url),'utf8'))
const url='http://127.0.0.1:8510/#brain-record'

async function open(page,cohort=fixture,width=390){
 await page.setViewportSize({width,height:844})
 await page.route('**/zenith_sport_cohorts.json*',r=>r.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(cohort),
 }))
 await page.route('**/zenith_learning_review.json*',r=>r.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(learning),
 }))
 await page.goto(url,{waitUntil:'domcontentloaded'})
 return page.getByRole('region',{name:'Four-sport official learning cohorts'})
}

test('Brain Record displays verified sport cohorts, not one pooled fake win rate',async({page})=>{
 const section=await open(page)
 await expect(section.getByRole('heading',{name:'Learning from hockey, CFB, NBA & MLB'})).toBeVisible()
 await expect(section.getByText('Hockey',{exact:true})).toBeVisible()
 await expect(section.getByText('College football',{exact:true})).toBeVisible()
 await expect(section.getByText('NBA preseason',{exact:true})).toBeVisible()
 await expect(section.getByText('MLB playoffs',{exact:true})).toBeVisible()
 await expect(section.getByText(new RegExp(fixture.source_verified_final_research_selections+' original research lines'))).toBeVisible()
 await expect(section.getByText(new RegExp(fixture.source_verified_distinct_final_games+' distinct games'))).toBeVisible()
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
 expect(overflow).toBeLessThanOrEqual(1)
})

test('Read-only recovery shows 549 NBA variants and model-proof guardrails',async({page})=>{
 const section=await open(page)
 await section.getByText('Why these results cannot yet improve the model').click()
 const nba=fixture.pending_official_final_recovery_by_sport.find(x=>x.sport==='NBA')
 await expect(section.getByText(new RegExp('NBA preseason: '+nba.derived_postgame_research_rows+' calculated outcomes'))).toBeVisible()
 await expect(section.getByText(new RegExp(nba.original_duplicate_line_variant_count+' duplicate/alternate variants'))).toBeVisible()
 await expect(section.getByText(/not proof those inputs were known at the original freeze/)).toBeVisible()
 await expect(section.getByText(/No live model coefficients were changed/)).toBeVisible()
 await expect(section.getByText(/A real mistake by sport/)).toBeVisible()
 await expect(section.getByText(/Cannot infer the cause from the final score alone/).first()).toBeVisible()
 await expect(section.getByText(/They are not extra independent games or approved bets/)).toBeVisible()
})

test('Invalid promotion, missing source hash or expired source fails closed',async({page})=>{
 for(const patch of [
  {model_bets_approved:1},
  {source_hashes:{...fixture.source_hashes,NHL_original_league_source_sha256:null}},
  {generated_at_utc:'2026-01-01T00:00:00Z'},
 ]){
  await page.unrouteAll({behavior:'ignoreErrors'})
  const section=await open(page,{...fixture,...patch})
  await expect(section.getByText(/Official source proof is missing or stale/)).toBeVisible()
  await expect(section.getByText('Hockey',{exact:true})).toHaveCount(0)
 }
})

test('Desktop shows four readable sports without changing original Brain Record',async({page})=>{
 const section=await open(page,fixture,1280)
 await expect(section.getByRole('heading',{name:'Learning from hockey, CFB, NBA & MLB'})).toBeVisible()
 await expect(page.getByRole('heading',{name:'How good is the brain?'})).toBeVisible()
 await expect(page.getByRole('heading',{name:'How Zenith learns from mistakes'})).toBeVisible()
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
 expect(overflow).toBeLessThanOrEqual(1)
})
