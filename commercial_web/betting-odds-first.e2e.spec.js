import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const read=f=>JSON.parse(readFileSync(new URL('./public/'+f,import.meta.url),'utf8'))
const all=read('betting_odds_board.json')
const frozen=read('nfl_frozen_game_intelligence.json')
const props=read('prop_v2_current.json')
const early=Date.parse('2026-10-09T22:44:00Z')
const originals=[
  all.games.find(g=>g.sport==='NFL'&&g.game_key==='PHI@JAX'),
  all.games.find(g=>g.sport==='NFL'&&g.game_key==='HOU@TEN'),
  all.games.find(g=>g.sport==='CFB'&&Date.parse(g.start)>early),
]
const small={...all,games:originals,game_count:3}
async function open(page,route,board=small){
  await page.setViewportSize({width:390,height:844})
  await page.addInitScript(time=>{Date.now=()=>time},early)
  await page.route('**/betting_odds_board.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(board)}))
  await page.route('**/nfl_frozen_game_intelligence.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(frozen)}))
  await page.route('**/prop_v2_current.json*',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(props)}))
  await page.goto('http://127.0.0.1:8510/#'+route,{waitUntil:'domcontentloaded'})
}
const region=page=>page.getByRole('region',{name:'Sportsbook odds and Zenith price comparisons'})

test('Bets immediately shows real sportsbook lines and price-quality judgment, not only 0-PLAY banners',async({page})=>{
 await open(page,'best-bets')
 const board=region(page)
 await expect(board.getByText('3 priced games')).toBeVisible()
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await expect(board.getByText('2 priced games')).toBeVisible()
 const card=board.locator('article').first()
 await expect(card.getByText('Moneyline',{exact:true})).toBeVisible()
 await expect(card.getByText('Spread',{exact:true})).toBeVisible()
 await expect(card.getByText(/Game total/)).toBeVisible()
 await expect(card.getByText('Typical', {exact:false}).first()).toBeVisible()
 await expect(card.getByText(/Zenith price read/)).toBeVisible()
 await expect(card.getByText(/No proven betting edge/)).toBeVisible()
 await card.getByText('Why Zenith rates these odds').click()
 await expect(card.getByText(/compares the best observed bookmaker odds/i)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
})

test('NFL filter shows real model winner and original market comparison, never approved pick',async({page})=>{
 await open(page,'best-bets')
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 const board=region(page)
 await expect(board.getByText('2 priced games')).toBeVisible()
 const card=board.locator('article').first()
 await expect(card.getByText(/Zenith NFL forecast · experimental/)).toBeVisible()
 await expect(card.getByText(/Jacksonville Jaguars to win/)).toBeVisible()
 await expect(card.getByText(/Original Pinnacle no-vig/)).toBeVisible()
 await expect(card.getByText(/Market-assisted prediction.*Not a proven bet/)).toBeVisible()
 await page.getByRole('group',{name:'Betting market filter'}).getByRole('button',{name:'Moneyline',exact:true}).click()
 await expect(board.locator('article').first().getByText('Point spread',{exact:true})).toHaveCount(0)
 await expect(board.locator('article').first().getByText('Moneyline',{exact:true})).toBeVisible()
})

test('Price shopping filter only highlights source-recent, meaningfully better same-line prices',async({page})=>{
 const copy=structuredClone(small)
 copy.games[0].markets.MONEYLINE.sides.AWAY.price_assessment='BETTER PRICE THAN PEERS'
 copy.games[0].markets.MONEYLINE.sides.AWAY.price_improvement_pct_points=2.5
 await open(page,'best-bets',copy)
 await region(page).getByRole('button',{name:/Better prices/}).click()
 const cards=region(page).locator('article')
 expect(await cards.count()).toBeGreaterThanOrEqual(1)
 await expect(cards.first().getByText(/Notably better than peers/).first()).toBeVisible()
 for (const card of await cards.all()) {
   await expect(card.getByText(/No proven betting edge/)).toBeVisible()
 }
})

test('Stale market snapshots cannot be highlighted as good current prices',async({page})=>{
 const copy=structuredClone(small)
 copy.games=copy.games.filter(g=>g.sport==='NFL')
 for(const g of copy.games) {
  g.source_capture_at='2026-10-05T00:00:00Z'
  g.capture_status='RECENT_CAPTURE'
  g.markets.MONEYLINE.sides.AWAY.price_assessment='BETTER PRICE THAN PEERS'
 }
 await open(page,'best-bets',copy)
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await expect(region(page).getByText('STALE').first()).toBeVisible()
 await region(page).getByRole('button',{name:/Better prices/}).click()
 await expect(region(page).locator('article')).toHaveCount(0)
})

test('Invalid proof cannot turn forged odds into a displayed market board',async({page})=>{
 await open(page,'best-bets',{...small,no_approved_pick_or_bet_created:false})
 await expect(region(page).getByText(/Source proof unavailable/)).toBeVisible()
 await expect(region(page).locator('article')).toHaveCount(0)
})

test('All game cards remain reachable through incremental Show more',async({page})=>{
 const games=Array.from({length:20},(_,i)=>({
  ...originals[i%3],
  provider_event_id:'browse-'+i,
  start:new Date(Date.parse(originals[i%3].start)+1000*i).toISOString(),
 }))
 await open(page,'best-bets',{...small,games,game_count:20})
 await expect(region(page).locator('article')).toHaveCount(4)
 await region(page).getByRole('button',{name:/Show 12 more/}).click()
 await expect(region(page).locator('article')).toHaveCount(16)
 await region(page).getByRole('button',{name:/Show 12 more/}).click()
 await expect(region(page).locator('article')).toHaveCount(20)
})

test('Props has reference odds, market probability, search and more lines',async({page})=>{
 await open(page,'props')
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 const search=page.getByRole('textbox',{name:'Search props by player or market'})
 await expect(search).toBeVisible()
 await search.fill('Jalen Hurts')
 await expect(page.getByText('Jalen Hurts',{exact:true}).first()).toBeVisible()
 await expect(page.getByText(/Market fair probability/).first()).toBeVisible()
 await expect(page.getByText(/Bookmaker reference/).first()).toBeVisible()
 await expect(page.getByText(/not a verified live or executable offer/i).first()).toBeVisible()
})

test('PrizePicks keeps line and market evidence separate from platform entry payout',async({page})=>{
 await open(page,'prizepicks')
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await expect(page.getByText(/PrizePicks is a pick-em line, not a sportsbook odds quote/i).first()).toBeVisible()
 await expect(page.getByText(/Market fair probability/).first()).toBeVisible()
 await expect(page.getByText(/Entry payout and correlation/).first()).toBeVisible()
})
