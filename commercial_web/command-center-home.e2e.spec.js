import {test,expect} from '@playwright/test'
const BASE='http://127.0.0.1:8510/'
const TODAY=Date.now()
const score=(p)=>p.getByRole('region',{name:'Game Day scores and schedule'})
const choices=p=>p.getByRole('group',{name:'Choose Game Day sport'})
const gameCards=p=>score(p).locator('article')
const gameSource='**/nhl_scores.json*'
async function home(p,width=390,freeze=true){
  await p.setViewportSize({width,height:844})
  if(freeze)await p.addInitScript(now=>{Date.now=()=>now},TODAY)
  await p.goto(BASE,{waitUntil:'domcontentloaded'})
  await expect(score(p).getByRole('heading',{name:'Scores & matchups'})).toBeVisible()
}

test('retro sports-broadcast command center shows real scores in first viewport on iPhone',async({page})=>{
 await home(page)
 const hero=page.getByRole('region',{name:'Sports Zenith game-day command center'})
 await expect(hero.getByRole('heading',{name:/The game.*The smarter call/s})).toBeVisible()
 await expect(hero.getByRole('button',{name:/Explore Bets/})).toBeVisible()
 await expect(hero.getByRole('button',{name:/Ask The Ref/})).toBeVisible()
 await expect(gameCards(page).first()).toBeVisible()
 const measured=await page.evaluate(()=>({
   x:document.documentElement.scrollWidth-document.documentElement.clientWidth,
   headingTop:document.querySelector('section[aria-label="Game Day scores and schedule"] h2').getBoundingClientRect().top,
   cardTop:document.querySelector('section[aria-label="Game Day scores and schedule"] article')?.getBoundingClientRect().top,
 }))
 expect(measured.x).toBeLessThanOrEqual(1)
 expect(measured.headingTop).toBeLessThan(650)
 expect(measured.cardTop).toBeLessThan(800)
 await expect(page.getByRole('navigation',{name:'Mobile primary navigation'})).toBeVisible()
 await expect(page.getByRole('button',{name:'Open the Ref sports assistant'})).toHaveCount(0)
 await expect(score(page).getByText(/Never simulated game results/)).toBeVisible()
})

test('All sport cards represent multiple distinct leagues, not 5 repeat NHL games',async({page})=>{
 await home(page)
 await expect(gameCards(page)).toHaveCount(5)
 const sports=await gameCards(page).evaluateAll(cards=>cards.map(card=>card.getAttribute('data-sport')))
 expect(new Set(sports).size).toBe(5)
 for(const sport of ['NFL','NHL','NBA','MLB','CFB']){
   expect(sports).toContain(sport)
 }
})

test('Sport tabs filter true source-matched fixtures on mobile, keeping game dates',async({page})=>{
 await home(page)
 await choices(page).getByRole('button',{name:'NHL',exact:true}).click()
 await expect(gameCards(page).first().getByText('NHL',{exact:true})).toBeVisible()
 expect((await gameCards(page).allInnerTexts()).every(text=>text.includes('NHL'))).toBe(true)
 await choices(page).getByRole('button',{name:'MLB',exact:true}).click()
 await expect(gameCards(page).first().getByText('MLB',{exact:true})).toBeVisible()
 await expect(gameCards(page).first().getByText('MLB StatsAPI')).toBeVisible()
 await choices(page).getByRole('button',{name:'NFL',exact:true}).click()
 await expect(gameCards(page).first().getByText('NFL',{exact:true})).toBeVisible()
 await expect(gameCards(page).first().getByText('UPCOMING')).toBeVisible()
 await expect(score(page).getByText(/source freshness are separate from a validated sportsbook price/)).toBeVisible()
})

test('NHL source failure is explicitly DATA SOURCE FAILURE rather than quiet NO BET',async({page})=>{
 await page.route(gameSource,r=>r.fulfill({status:503,contentType:'application/json',body:'{}'}))
 await home(page)
 await choices(page).getByRole('button',{name:'NHL',exact:true}).click()
 await expect(score(page).getByText('DATA SOURCE FAILURE',{exact:true})).toBeVisible()
 await expect(score(page).getByText(/NOT a betting-model NO BET/)).toBeVisible()
 await expect(gameCards(page)).toHaveCount(0)
})

test('Valid empty NHL games are no games, not a data-source failure',async({page})=>{
 await page.route(gameSource,r=>r.fulfill({status:200,contentType:'application/json',
  body:JSON.stringify({generated_at:new Date(TODAY-60000).toISOString(),status:'NO_GAMES',games:[]}),
 }))
 await home(page)
 await choices(page).getByRole('button',{name:'NHL',exact:true}).click()
 await expect(score(page).getByText('No games in the display window')).toBeVisible()
 await expect(score(page).getByText(/valid schedule was checked/)).toBeVisible()
 await expect(score(page).getByText('DATA SOURCE FAILURE')).toHaveCount(0)
})

test('Stale feeds explicitly mark SOURCE STALE and cannot pretend games are live',async({page})=>{
 const payload={generated_at:new Date(TODAY-6*3600000).toISOString(),
  status:'READY',games:[{event_id:'oldGame',away:'Sharks',home:'Kings',
   start_time:new Date(TODAY-20*60000).toISOString(),
   away_score:3,home_score:4,live:true,final:false}]}
 await page.route(gameSource,r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify(payload)}))
 await home(page)
 await choices(page).getByRole('button',{name:'NHL',exact:true}).click()
 await expect(score(page).getByText('SOURCE STALE',{exact:true})).toBeVisible()
 await expect(score(page).getByText(/latest score feed is too old/)).toBeVisible()
 await expect(gameCards(page)).toHaveCount(0)
})

test('Bright sports-broadcast navigation and homepage links open original services',async({page})=>{
 await home(page,1280)
 await expect(page.getByRole('navigation',{name:'Primary navigation'})).toBeVisible()
 await page.getByRole('region',{name:'Sports Zenith game-day command center'}).getByRole('button',{name:/Explore Bets/}).click()
 await expect(page).toHaveURL(/#best-bets/)
 await expect(page.getByRole('heading',{name:'Best Bets',exact:true})).toBeVisible()
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await score(page).getByRole('button',{name:/All scores/}).click()
 await expect(page).toHaveURL(/#scores/)
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await page.getByRole('region',{name:'Sports Zenith game-day command center'}).getByRole('button',{name:/Ask The Ref/}).click()
 await expect(page).toHaveURL(/#ask/)
 await expect(page.getByRole('img',{name:'Zenith AI referee avatar'})).toBeVisible()
})
