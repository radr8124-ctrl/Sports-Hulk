import {test,expect} from '@playwright/test'

const BASE=process.env.ZENITH_MARKET_BOARD_URL||'http://127.0.0.1:8510/'

test('premium Market Board is a legible retro broadcast masthead, not generic grey tabs',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE+'#best-bets',{waitUntil:'domcontentloaded'})
 const board=page.locator('[data-premium-market-board]')
 const heading=board.locator('[data-market-board-heading]')
 await expect(board).toBeVisible()
 await expect(heading).toBeVisible()
 await expect(heading.getByText('THE MARKET BOARD',{exact:true})).toBeVisible()
 expect(await heading.evaluate(node=>getComputedStyle(node).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(board.getByText(/Proof before picks/)).toBeVisible()
 const rail=board.getByRole('group',{name:'Betting sections'})
 await expect(rail.getByRole('button')).toHaveCount(6)
 await expect(rail.getByRole('button',{name:'Best Bets'})).toHaveAttribute('aria-current','page')
 expect(await board.evaluate(node=>getComputedStyle(node).backgroundColor)).toBe('rgb(255, 245, 228)')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})

test('mobile market navigation swipes to real Props, PrizePicks and Parlays destinations',async({page})=>{
 await page.setViewportSize({width:320,height:844})
 await page.goto(BASE+'#best-bets',{waitUntil:'domcontentloaded'})
 const board=page.locator('[data-premium-market-board]')
 const rail=board.getByRole('group',{name:'Betting sections'})
 const width=await rail.evaluate(node=>({content:node.scrollWidth,visible:node.clientWidth}))
 expect(width.content).toBeGreaterThan(width.visible+110)
 await rail.getByRole('button',{name:'PrizePicks'}).click()
 await expect(page).toHaveURL(/#prizepicks/)
 await expect(rail.getByRole('button',{name:'PrizePicks'})).toHaveAttribute('aria-current','page')
 await rail.getByRole('button',{name:'Parlays'}).click()
 await expect(page).toHaveURL(/#parlays/)
 await expect(rail.getByRole('button',{name:'Parlays'})).toHaveAttribute('aria-current','page')
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1)
})

test('market navigation has all six functional destinations without changing their evidence panels',async({page})=>{
 await page.setViewportSize({width:1280,height:900})
 for(const [name,hash] of [
  ['Best Bets','best-bets'],['Props','props'],['PrizePicks','prizepicks'],
  ['Tools','tools'],['Parlays','parlays'],['Bet Lab','bet-lab'],
 ]){
  await page.goto(BASE+'#'+hash,{waitUntil:'domcontentloaded'})
  const board=page.locator('[data-premium-market-board]')
  await expect(board).toBeVisible()
  const button=board.getByRole('button',{name,exact:true})
  await expect(button).toHaveAttribute('aria-current','page')
  await expect(board.getByRole('group',{name:'Betting sections'}).getByRole('button')).toHaveCount(6)
  const root=await page.evaluate(()=>({
   overflow:document.documentElement.scrollWidth-innerWidth,
   privatePoolExposed:document.body.innerText.includes('ANNIE G 01'),
   hasIndependentContent:!!document.querySelector('main [class*=rounded]'),
  }))
  expect(root.overflow).toBeLessThanOrEqual(1)
  expect(root.privatePoolExposed).toBe(false)
  expect(root.hasIndependentContent).toBe(true)
 }
})
