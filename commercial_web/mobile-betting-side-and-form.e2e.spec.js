import {test,expect} from '@playwright/test'

async function mobile(page,hash){
 await page.setViewportSize({width:390,height:844})
 await page.addInitScript(utc=>{Date.now=()=>utc},Date.parse('2026-10-09T23:41:00Z'))
 await page.goto('http://127.0.0.1:8510/#'+hash,{waitUntil:'domcontentloaded'})
}

test('Each quoted outcome is explicit: which team/side, bookmaker odds and settlement',async({page})=>{
 await mobile(page,'best-bets')
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 const board=page.getByRole('region',{name:'Sportsbook odds and Zenith price comparisons'})
 await expect(board.getByText(/13 priced games/)).toBeVisible()
 const first=board.locator('article').first()
 await expect(first.getByText('BET ON Philadelphia Eagles',{exact:true})).toBeVisible()
 await expect(first.getByText('BET ON Jacksonville Jaguars',{exact:true})).toBeVisible()
 await expect(first.getByText('Jacksonville Jaguars must win the game.')).toBeVisible()
 await expect(first.getByText(/BET ON Jacksonville Jaguars -7.5/)).toBeVisible()
 await expect(first.getByText(/Jacksonville Jaguars must win by 8 or more/)).toBeVisible()
 await expect(first.getByText(/BET OVER.*points/i)).toBeVisible()
 await expect(first.getByText(/Zenith NFL forecast/)).toBeVisible()
 await expect(first.getByText(/No proven betting edge/)).toBeVisible()
 const size=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}))
 expect(size.scroll).toBeLessThanOrEqual(size.viewport+1)
})

test('Props uses 4-game context to surface 15 real form watches, not fabricated PLAYs',async({page})=>{
 await mobile(page,'props')
 const views=page.getByRole('group',{name:'Player research views'})
 await expect(views.getByRole('button',{name:/Recent-form watch \(15\)/})).toBeVisible()
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await views.getByRole('button',{name:/Recent-form watch/}).click()
 await expect(page.getByText('15 lines',{exact:true})).toBeVisible()
 const first=page.locator('main article').first()
 await expect(first.getByText('FORM WATCH',{exact:true})).toBeVisible()
 await expect(first.getByText('4/4 prior games',{exact:true})).toBeVisible()
 await expect(first.getByText(/Market fair probability/)).toBeVisible()
 await expect(first.getByText(/Not validated/)).toBeVisible()
 await expect(first.getByText('PASS',{exact:true})).toHaveCount(0)
 await expect(first.getByText(/Not approved as a bet/)).toBeVisible()
})

test('PrizePicks has 10 player form watches with MORE or LESS but not fake entry odds',async({page})=>{
 await mobile(page,'prizepicks')
 const views=page.getByRole('group',{name:'Player research views'})
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await expect(views.getByRole('button',{name:/Recent-form watch \(10\)/})).toBeVisible()
 await views.getByRole('button',{name:/Recent-form watch/}).click()
 await expect(page.getByText('10 lines',{exact:true})).toBeVisible()
 const cards=page.getByRole('region',{name:'PrizePicks current line research'}).locator('article')
 await expect(cards).toHaveCount(6)
 await page.getByRole('button',{name:/Show 12 more PrizePicks lines/}).click()
 await expect(cards).toHaveCount(10)
 const first=cards.first()
 await expect(first.getByText('FORM WATCH',{exact:true})).toBeVisible()
 await expect(first.getByText(/MORE|LESS/).first()).toBeVisible()
 await expect(first.getByText(/entry payout and correlation must be checked/i)).toBeVisible()
 await expect(first.getByText('PASS',{exact:true})).toHaveCount(0)
 await expect(page.getByText(/Full pick-em payout and correlation are not yet validated/).first()).toBeVisible()
})

test('Weak recent form is clearly a caution, never a manufactured profitable recommendation',async({page})=>{
 await mobile(page,'prizepicks')
 await page.getByRole('button',{name:'NFL',exact:true}).first().click()
 await page.getByRole('textbox',{name:'Search props by player or market'}).fill('Jakobi Meyers')
 const card=page.locator('main article').first()
 await expect(card.getByText('Jakobi Meyers',{exact:true})).toBeVisible()
 await expect(card.getByText('Recent form cautions')).toBeVisible()
 await expect(card.getByText('1/4 prior games',{exact:true})).toBeVisible()
 await expect(card.getByText(/Not approved as a bet/)).toBeVisible()
})

test('Betting horizontal tabs do not call whole-page scrollIntoView on mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.addInitScript(()=>{
   const native=Element.prototype.scrollIntoView
   window.__betRailAncestorScrollCalls=0
   Element.prototype.scrollIntoView=function(...args){
     if(this.closest('[aria-label="Betting sections"]'))window.__betRailAncestorScrollCalls++
     return native.apply(this,args)
   }
 })
 await page.goto('http://127.0.0.1:8510/#props',{waitUntil:'domcontentloaded'})
 await page.getByRole('group',{name:'Player research views'}).waitFor()
 expect(await page.evaluate(()=>window.__betRailAncestorScrollCalls)).toBe(0)
 const nav=page.getByRole('button',{name:'PrizePicks',exact:true}).first()
 await nav.click()
 await page.getByRole('heading',{name:'PrizePicks',exact:true}).waitFor()
 await page.waitForTimeout(350)
 const y=await page.evaluate(()=>scrollY)
 expect(y).toBeLessThan(3)
 await page.waitForTimeout(750)
 expect(Math.abs((await page.evaluate(()=>scrollY))-y)).toBeLessThan(3)
 expect(await page.evaluate(()=>window.__betRailAncestorScrollCalls)).toBe(0)
 const dim=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
 expect(dim).toBeLessThanOrEqual(1)
})
