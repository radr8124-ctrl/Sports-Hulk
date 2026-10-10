import {test,expect} from '@playwright/test'

const BASE=process.env.ZENITH_PLAYER_PREMIUM_URL||'http://127.0.0.1:8510/'
const future='2027-11-12T19:00:00Z'
const makeRow=(lane,id,player,decision='PASS_INSUFFICIENT_HISTORY')=>({
 lane,sport:'NFL',event_id:'SYN-TEST-'+id,player,player_key:'synthetic'+id,
 market_subtype:'PLAYER_TOTAL_RECEPTIONS',side:'OVER',line:2.5,
 event_start:future,american_odds:lane==='PROP'?-110:null,
 market_reference_probability_pct:53.2,probability_source:'MARKET_REFERENCE',
 v2_probability_pct:53.2,conservative_probability_pct:48.2,conservative_edge_pct_points:-5,
 data_quality_grade:'B',data_quality_book_count:3,historical_edge_confidence:'NO_INDEPENDENT_EDGE',
 selection_rule_status:'NO_INDEPENDENT_MODEL_EDGE',shadow_decision:decision,
 competition_regime:'REGULAR',
})
const entries=[
 makeRow('PROP','P1','Synthetic Pass Catcher','PASS_NO_PROVEN_MODEL_EDGE'),
 makeRow('PROP','P2','Synthetic Research Runner','SHADOW_MONITOR'),
 makeRow('PRIZEPICKS','PP1','Synthetic Pick-Em Receiver','PASS_NO_PROVEN_MODEL_EDGE'),
 makeRow('PRIZEPICKS','PP2','Synthetic Pick-Em Tight End','SHADOW_MONITOR'),
]
const model={status:'CURRENT',generated_at:'2026-10-10T12:00:00Z',summary:{candidates:entries.length,shadow_plays:0,shadow_monitors:2,passes:2},picks:entries}

async function open(page,route,width=390,payload=model){
 await page.setViewportSize({width,height:844})
 await page.route('**/prop_v2_current.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)}))
 await page.route('**/nfl_prop_independent_research.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({status:'NO_MATCH',rows:[]})}))
 const res=await page.goto(BASE+'#'+route,{waitUntil:'domcontentloaded'})
 const root=page.getByRole('region',{name:route==='props'?'Player props current line research':'PrizePicks current line research'})
 const cover=root.locator('[data-premium-player-cover]')
 await expect(cover).toBeVisible()
 return {root,cover,res}
}

test('Props cover is premium ink with accurate lane-only proof counts and no invented PLAY',async({page})=>{
 const {cover,root}=await open(page,'props')
 expect(await cover.evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(cover.getByText('THE PLAYER LINEUP',{exact:true})).toBeVisible()
 await expect(cover.getByRole('heading',{name:'Props'})).toBeVisible()
 await expect(cover.locator('[data-prop-cover-metric="lines"]')).toContainText('2')
 await expect(cover.locator('[data-prop-cover-metric="monitors"]')).toContainText('1')
 await expect(cover.locator('[data-prop-cover-metric="plays"]')).toContainText('0')
 await expect(cover).toContainText('Research only')
 await expect(root.getByText(/None has cleared the independent prediction or payout proof/)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})

test('PrizePicks cover separates research lines from actual entry payout proof',async({page})=>{
 const {cover,root}=await open(page,'prizepicks')
 expect(await cover.evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(cover.getByText('THE PICK-EM DESK',{exact:true})).toBeVisible()
 await expect(cover.getByRole('heading',{name:'PrizePicks'})).toBeVisible()
 await expect(cover.locator('[data-prop-cover-metric="lines"]')).toContainText('2')
 await expect(cover.locator('[data-prop-cover-metric="plays"]')).toContainText('0')
 await expect(cover).toContainText('Entry payout is not proven')
 await expect(root.getByText('Payout proof required',{exact:true})).toBeVisible()
 await expect(root.getByText(/Full pick-em payout and correlation are not yet validated/).first()).toBeVisible()
})

test('premium Props and PrizePicks player cards preserve line meaning and hidden evidence',async({page})=>{
 for(const [route,name] of [['props','Synthetic Pass Catcher'],['prizepicks','Synthetic Pick-Em Receiver']]){
  const {root}=await open(page,route)
  const card=root.locator('[data-premium-player-card]').filter({hasText:name}).first()
  await expect(card).toBeVisible()
  await expect(card).toContainText('MORE 2.5'.replace('MORE',''+(route==='props'?'Over':'MORE')))
  await expect(card).toContainText(/Market fair probability/)
  await expect(card).toContainText('Not approved as a bet')
  const details=card.locator('details')
  await expect(details).not.toHaveAttribute('open','')
  await details.locator('summary').click()
  await expect(details).toHaveAttribute('open','')
  await expect(card.getByText(/Model gate:/)).toBeVisible()
  if(route==='props')await expect(card).toContainText('Bookmaker reference -110')
  else await expect(card).toContainText('Entry payout and correlation must be checked separately')
 }
})

test('mobile player desk stays compact, original search and filtering work across both lanes',async({page})=>{
 for(const width of [320,390,430]){
  for(const route of ['props','prizepicks']){
   const {root,cover}=await open(page,route,width)
   const box=await cover.boundingBox()
   expect(box.height).toBeLessThan(235)
   const search=root.getByRole('textbox',{name:'Search props by player or market'})
   const searchBox=await search.boundingBox()
   expect(searchBox.y).toBeLessThan(1100)
   await search.fill('not a player')
   await expect(root.getByText(/No upcoming (PrizePicks|prop) lines match this filter/)).toBeVisible()
   await search.fill('Synthetic')
   await expect(root.locator('[data-premium-player-card]')).toHaveCount(2)
   await root.getByRole('button',{name:'NFL',exact:true}).click()
   await expect(cover.locator('[data-prop-cover-context]')).toContainText('NFL')
   expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
  }
 }
})
