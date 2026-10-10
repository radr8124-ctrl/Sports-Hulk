import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const actual=JSON.parse(readFileSync(new URL('./public/zenith_learning_review.json',import.meta.url),'utf8'))
const local='http://127.0.0.1:8510/#brain-record'
const clock=Date.parse('2026-10-10T01:22:00Z')

async function open(page, report=actual, width=390){
 await page.setViewportSize({width,height:844})
 await page.addInitScript(now=>{Date.now=()=>now},clock)
 await page.route('**/zenith_learning_review.json*',route=>route.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(report)
 }))
 await page.goto(local,{waitUntil:'domcontentloaded'})
 return page.getByRole('region',{name:'How Zenith learns from mistakes'})
}

test('Brain Record shows saved Oct4 original game losing spread, not just a hit rate',async({page})=>{
 const section=await open(page)
 await expect(section.getByRole('heading',{name:'How Zenith learns from mistakes'})).toBeVisible()
 await expect(section.getByText('Chiefs 30 — Raiders 27')).toBeVisible()
 await expect(section.getByText('Spread · Chiefs -5')).toBeVisible()
 await expect(section.getByText('KC won by 3 but needed 6+ to cover Chiefs -5.')).toBeVisible()
 await expect(section.getByText(/model_nine_feature_forecast_replayed_from_2026_week4/)).toHaveCount(0)
 await expect(section.getByText(/not proof of an independently calibrated model/)).toBeVisible()
 const width=await page.evaluate(()=>({
  screen:document.documentElement.clientWidth,page:document.documentElement.scrollWidth
 }))
 expect(width.page).toBeLessThanOrEqual(width.screen+1)
})

test('Frozen future model stays ungraded, loser category and shadow proof are distinct',async({page})=>{
 const section=await open(page)
 const snapshot=actual.snapshot
 await expect(section.getByText(new RegExp(`${snapshot.market_based_predictions_same_as_market} of ${snapshot.valid_settled_market_research}`))).toBeVisible()
 await expect(section.getByText(new RegExp(`${snapshot.frozen_nfl_nine_feature_games} frozen, ${snapshot.frozen_nfl_nine_feature_games_officially_settled} independently settled`))).toBeVisible()
 await expect(section.getByText(new RegExp(`${actual.pre_registered_calibration_shadow.ready_asof_future_predictions} prospective calibration challengers`))).toBeVisible()
 await expect(section.getByText(/no validated improvement yet/)).toBeVisible()
 const details=section.getByText('Show error categories, original source quality and learning gates')
 await details.click()
 await expect(section.getByText(/21 distinct games/)).toBeVisible()
 await expect(section.getByText(/not a verified postgame result timestamp/)).toBeVisible()
 await expect(section.getByText(/No original prediction, past result or live-model coefficient is overwritten/)).toBeVisible()
})

test('No fake record if original source contract is changed',async({page})=>{
 const section=await open(page,{...actual,
   frozen_forward_challenger_score:{
     ...actual.frozen_forward_challenger_score,
     automated_live_model_adjustment_allowed:true,
   },
 })
 await expect(section.getByText(/Learning evidence could not be validated/)).toBeVisible()
 await expect(section.getByText(/Chiefs 30/)).toHaveCount(0)
})

test('Large desktop still shows one compact panel without hiding original Brain Record',async({page})=>{
 const section=await open(page,actual,1280)
 await expect(section.getByRole('heading',{name:'How Zenith learns from mistakes'})).toBeVisible()
 await expect(page.getByRole('heading',{name:'How good is the brain?'})).toBeVisible()
 await expect(page.getByText('Official published record',{exact:true}).first()).toBeVisible()
})
