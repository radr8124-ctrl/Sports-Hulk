import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'

const BASE=process.env.ZENITH_BETS_PREMIUM_URL||'http://127.0.0.1:8510/'
const snapshot=JSON.parse(readFileSync(new URL('./public/betting_v2_all_markets_current.json',import.meta.url),'utf8'))

async function start(page,width=390){
 await page.setViewportSize({width,height:844})
 await page.route('**/betting_v2_all_markets_current.json*',route=>route.fulfill({
   status:200,contentType:'application/json',body:JSON.stringify(snapshot),
 }))
 await page.goto(BASE+'#best-bets',{waitUntil:'domcontentloaded'})
 const brief=page.getByRole('region',{name:'Best Bets premium evidence brief'})
 await expect(brief).toBeVisible()
 return brief
}

test('premium Best Bets price desk preserves actual frozen source-count and PASS/SHADOW distinctions',async({page})=>{
 const brief=await start(page)
 await expect(brief.getByRole('heading',{name:'Best Bets'})).toBeVisible()
 expect(await brief.evaluate(el=>getComputedStyle(el).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(brief.getByText('THE PRICE DESK')).toBeVisible()
 const stats=brief.locator('[data-bestbets-proof-stats]')
 await expect(stats.locator('[data-proof-metric="reviewed"]').getByText(String(snapshot.summary.candidates),{exact:true})).toBeVisible()
 await expect(stats.locator('[data-proof-metric="shadow"]').getByText(String(snapshot.summary.shadow_plays),{exact:true})).toBeVisible()
 await expect(stats.locator('[data-proof-metric="passed"]').getByText(String(snapshot.summary.passes),{exact:true})).toBeVisible()
 await expect(brief.getByText(/not an approved bet/i)).toBeVisible()
 await expect(brief.getByText(/saved model research/i)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth)).toBeLessThanOrEqual(1)
})

test('on iPhone, actual odds comparison stays within the first fold below the premium cover',async({page})=>{
 await start(page,390)
 const odds=page.getByRole('region',{name:'Sportsbook odds and Zenith price comparisons'})
 await expect(odds.getByText('Games, odds and better prices')).toBeVisible()
 const rect=await odds.getByText('Games, odds and better prices').boundingBox()
 expect(rect?.y??9999).toBeLessThan(844)
 const first=page.getByRole('region',{name:'Best Bets premium evidence brief'})
 const hero=await first.boundingBox()
 expect(hero?.height??999).toBeLessThan(265)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-window.innerWidth)).toBeLessThanOrEqual(1)
})

test('paper watchlist stays expandable, source-preserving and clearly not a betting action',async({page})=>{
 await start(page)
 const watchlist=page.locator('[data-premium-research-card]').first()
 await watchlist.scrollIntoViewIfNeeded()
 await expect(watchlist).toBeVisible()
 await expect(watchlist.getByText(/Paper research, not an approved bet/)).toBeVisible()
 await expect(watchlist.getByText('RESEARCH',{exact:true})).toBeVisible()
 await watchlist.getByText('View evidence').click()
 await expect(watchlist.locator('details')).toHaveAttribute('open','')
 await expect(watchlist.getByText(/Model gate:/)).toBeVisible()
 const raw=await page.locator('body').innerText()
 expect(raw).not.toContain('ANNIE G 01')
})

test('sport and market filters retain their exact original decision scope',async({page})=>{
 await start(page,1280)
 const hero=page.getByRole('region',{name:'Best Bets premium evidence brief'})
 const selected=hero.locator('[data-bestbets-filter-context]')
 await expect(selected).toContainText('All sports')
 await page.getByRole('button',{name:'NHL',exact:true}).first().click()
 await expect(selected).toContainText('NHL')
 await page.getByRole('group',{name:'Betting market filter'}).getByRole('button',{name:'Moneyline'}).click()
 await expect(selected).toContainText('Moneyline')
 await expect(hero.locator('[data-proof-metric="reviewed"]').getByText(String(snapshot.summary.candidates),{exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})
