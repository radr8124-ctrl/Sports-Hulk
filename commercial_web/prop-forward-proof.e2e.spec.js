import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const BASE=process.env.ZENITH_PLAYER_PROOF_URL||'http://127.0.0.1:8510/'
const current=JSON.parse(readFileSync(new URL('./public/prop_v2_current.json',import.meta.url),'utf8'))
const forward=JSON.parse(readFileSync(new URL('./public/prop_v2_forward.json',import.meta.url),'utf8'))
const noForm={status:'NO_MATCH',rows:[]}
const urls=['prop_v2_current.json','prop_v2_forward.json','nfl_prop_independent_research.json']

async function open(page,route,width=390,{fresh=current,record=forward}={}){
 await page.setViewportSize({width,height:844})
 await page.route('**/prop_v2_current.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(fresh)}))
 await page.route('**/prop_v2_forward.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(record)}))
 await page.route('**/nfl_prop_independent_research.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(noForm)}))
 const res=await page.goto(BASE+'#'+route,{waitUntil:'domcontentloaded'})
 const section=page.getByRole('region',{name:route==='props'?'Props forward result proof':'PrizePicks forward result proof'})
 await expect(section).toBeVisible()
 await expect(section).toHaveAttribute('data-proof-source-status','SOURCE_TRACKED_RESEARCH_ONLY')
 return {section,res}
}

test('Props leads with source-tracked sport-separated forward record, no pooled Brier or imagined edge',async({page})=>{
 const {section}=await open(page,'props')
 const settled=['NFL_PROP','NBA_PROP','NHL_PROP','MLB_PROP']
   .reduce((n,k)=>n+forward.by_lane[k].all_predictions.settled,0)
 await expect(section.getByRole('heading',{name:new RegExp(settled.toLocaleString()+' settled prop records')})).toBeVisible()
 await expect(section).toContainText('These are separate sport samples, not one pooled model advantage.')
 await expect(section).toContainText('Not a qualified bet')
 await expect(section.getByText(/Full entry payout proof/i)).toHaveCount(0)
 await section.locator('summary').click()
 await expect(section.locator('[data-forward-sport]')).toHaveCount(4)
 await expect(section.locator('[data-forward-sport="NHL"]')).toContainText('Model worse than market')
 await expect(section.locator('[data-forward-sport="NHL"]')).toContainText('simulated research only, not your actual profit')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})

test('Props selected NHL displays worse Brier difference beside settled count, not a winning model',async({page})=>{
 const {section}=await open(page,'props')
 const region=page.getByRole('region',{name:'Player props current line research'})
 await region.getByRole('button',{name:'NHL',exact:true}).click()
 const nhl=forward.by_lane.NHL_PROP.all_predictions
 await expect(section.getByText(new RegExp(nhl.settled.toLocaleString()+' settled prop records'))).toBeVisible()
 await expect(section.locator('[data-prop-proof-verdict]')).toContainText('Model worse than market')
 await expect(section.locator('[data-prop-proof-verdict]')).toContainText('Brier difference +'+nhl.v2_minus_market_brier.toFixed(5))
 await section.locator('summary').click()
 await expect(section.locator('[data-forward-sport="NHL"]')).toContainText('Reference-price paper ROI')
 await expect(section.locator('[data-forward-sport="NHL"]')).toContainText('not your actual profit')
})

test('PrizePicks explains no verified full-entry payout and hides tempting paper ROI even when positive',async({page})=>{
 const {section}=await open(page,'prizepicks')
 const region=page.getByRole('region',{name:'PrizePicks current line research'})
 await region.getByRole('button',{name:'NHL',exact:true}).click()
 const value=forward.by_lane.NHL_PRIZEPICKS.all_predictions.roi_pct
 await expect(section).toContainText('Individual legs do not prove full-entry payout')
 await section.locator('summary').click()
 await expect(section).toContainText('Leg-level pricing-proxy ROI is deliberately not displayed')
 expect((await section.innerText()).includes(`+${value}%`)).toBe(false)
 await expect(section).toContainText('Not a qualified bet')
})

test('No NBA settled results cannot show a fake zero-win model verdict',async({page})=>{
 const {section}=await open(page,'props')
 await page.getByRole('region',{name:'Player props current line research'})
   .getByRole('button',{name:'NBA',exact:true}).click()
 await expect(section).toContainText('0 settled prop records')
 await expect(section).toContainText('No independently settled observations')
 await expect(section).not.toContainText('Model worse than market')
})

test('version conflict with current/forward source hides all displayed grades rather than guessing',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const bad=structuredClone(forward);bad.model_version='UNTRUSTED_DIFFERENT_MODEL'
 await page.route('**/prop_v2_current.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(current)}))
 await page.route('**/prop_v2_forward.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(bad)}))
 await page.route('**/nfl_prop_independent_research.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(noForm)}))
 await page.goto(BASE+'#props',{waitUntil:'domcontentloaded'})
 const section=page.getByRole('region',{name:'Props forward result proof'})
 await expect(section).toHaveAttribute('data-proof-source-status','SOURCE_VERSION_CONFLICT')
 await expect(section).toContainText('Performance figures are withheld')
 await expect(section).not.toContainText('Reference-price paper ROI')
})

test('mobile proof stays short with source details expandable and no side-scroll',async({page})=>{
 for(const width of [320,390,430]){
  for(const route of ['props','prizepicks']){
   const {section}=await open(page,route,width)
   const box=await section.boundingBox()
   expect(box?.height||1000).toBeLessThan(210)
   expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  }
 }
})
