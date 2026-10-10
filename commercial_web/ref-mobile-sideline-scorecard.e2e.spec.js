import {test,expect} from '@playwright/test'

const BASE=process.env.ZENITH_REF_SAFE_TEST_URL||'http://127.0.0.1:8510/'
const now=new Date()
const oneHourAgo=new Date(now.getTime()-3600_000).toISOString()
const source=(games=[])=>({generated_at:new Date().toISOString(),status:'READY',games})
const game=(n)=>({
  event_id:'SYN-VISUAL-NFL-'+n,
  away:'Synthetic Falcons of the Bay',home:'Synthetic Mariners of the North',
  away_abbr:'FAL',home_abbr:'MAR',
  start_time:oneHourAgo,live:true,final:false,
  away_score:21+n,home_score:17+n,
})

async function load(page,{count=3}={}){
 await page.emulateMedia({reducedMotion:'reduce'})
 for(const sport of ['nfl','nhl','cfb','nba','mlb']){
  await page.route('**/'+sport+'_scores.json*',route=>route.fulfill({
   status:200,contentType:'application/json',
   body:JSON.stringify(source(sport==='nfl'?Array.from({length:count},(_,i)=>game(i)):[])),
  }))
 }
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const deck=page.getByRole('region',{name:'Game Day scores and schedule'})
 await expect(deck.locator('[data-testid^="gameday-"]')).toHaveCount(count)
 await expect(page.getByRole('complementary',{name:'The Ref sports companion'})).toBeVisible()
 return deck
}

const metrics=page=>page.evaluate(()=>{
 const deck=document.querySelector('[aria-label="Game Day scores and schedule"]')
 const rail=deck?.querySelector('[data-scorecard-scroll]')
 const score=rail?.querySelector('[data-testid^="gameday-"]')
 const mascot=document.querySelector('.zenith-ref-mascot')
 const nav=document.querySelector('nav[aria-label="Mobile primary navigation"]')
 const ref=mascot?.getBoundingClientRect()
 const card=score?.getBoundingClientRect()
 const mask=rail?.getBoundingClientRect()
 const bottom=nav?.getBoundingClientRect()
 const collision=ref&&card?Math.max(0,Math.min(ref.right,card.right)-Math.max(ref.left,card.left))
   * Math.max(0,Math.min(ref.bottom,card.bottom)-Math.max(ref.top,card.top)):null
 const visibleCard=card&&mask ? {
  left:Math.max(card.left,mask.left),right:Math.min(card.right,mask.right),
  top:Math.max(card.top,mask.top),bottom:Math.min(card.bottom,mask.bottom)
 }:null
 const visibleCollision=ref&&visibleCard?Math.max(0,Math.min(ref.right,visibleCard.right)-Math.max(ref.left,visibleCard.left))
   * Math.max(0,Math.min(ref.bottom,visibleCard.bottom)-Math.max(ref.top,visibleCard.top)):null
 return {
  width:innerWidth,
  ref:ref?.toJSON(),
  score:card?.toJSON(),
  rail:mask?.toJSON(),
  avatarWidth:ref?.width,
  overlap:Math.round(collision??-1),
  visibleOverlap:Math.round(visibleCollision??-1),
  navClear:Boolean(ref&&bottom&&ref.bottom<=bottom.top+1),
  scoreWithinRail:Boolean(card&&mask&&card.left>=mask.left-1&&card.right<=mask.right+1),
  scoreLabels:score?.querySelectorAll('b')?.length||0,
  scrollWidth:rail?.scrollWidth||0,clientWidth:rail?.clientWidth||0,
  pageOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
  safeLaneVisible:Boolean(deck?.querySelector('[data-ref-mobile-sideline]')&&
   getComputedStyle(deck.querySelector('[data-ref-mobile-sideline]')).display!=='none'),
 }
})

test('mobile full-body Ref uses a dedicated no-overlap sideline beside live scores',async({page})=>{
 await load(page)
 for(const width of [320,360,390,430]){
  await page.setViewportSize({width,height:844})
  // Chrome can commit viewport dimensions a frame before recalculating vw widths.
  await expect.poll(()=>page.locator('[data-scorecard-scroll]').evaluate(el=>Math.round(el.getBoundingClientRect().width))).toBe(width-153)
  const state=await metrics(page)
  expect(state.pageOverflow,'Page overflow at '+width).toBeLessThanOrEqual(1)
  expect(state.safeLaneVisible,'Missing Ref sideline at '+width).toBe(true)
  expect(state.avatarWidth,'Full-size Ref not preserved at '+width).toBeGreaterThanOrEqual(108)
  expect(state.scoreWithinRail,'Scorecard clipped at '+width).toBe(true)
  expect(state.overlap,'Ref covers the verified scorecard at '+width).toBe(0)
  expect(state.visibleOverlap).toBe(0)
  expect(state.scoreLabels).toBe(2)
  expect(state.navClear).toBe(true)
 }
})

test('mobile scorecard rail still swipes through all three public sourced games',async({page})=>{
 const deck=await load(page)
 await page.setViewportSize({width:390,height:844})
 const rail=deck.locator('[data-scorecard-scroll]')
 await expect(rail).toBeVisible()
 const before=await rail.evaluate(el=>({left:el.scrollLeft,visible:el.clientWidth,total:el.scrollWidth}))
 expect(before.total).toBeGreaterThan(before.visible+150)
 await rail.evaluate(el=>{el.scrollLeft=el.scrollWidth})
 await expect.poll(()=>rail.evaluate(el=>el.scrollLeft)).toBeGreaterThan(100)
 await expect(deck.locator('[data-testid^="gameday-"]')).toHaveCount(3)
 await expect(page.getByRole('button',{name:'Open The Ref animated sports companion'})).toBeVisible()
})

test('desktop scorecards still use the full-width original grid beside the referee gutter',async({page})=>{
 const deck=await load(page)
 await page.setViewportSize({width:1280,height:900})
 const state=await metrics(page)
 expect(state.safeLaneVisible).toBe(false)
 expect(state.pageOverflow).toBeLessThanOrEqual(1)
 expect(state.scoreWithinRail).toBe(true)
 expect(state.avatarWidth).toBeGreaterThanOrEqual(145)
 expect(state.overlap).toBe(0)
 expect(state.clientWidth).toBeGreaterThan(500)
 await expect(deck.locator('[data-testid^="gameday-"]')).toHaveCount(3)
})

test('no new user data, sound, or fabricated outcomes enter the Ref score display',async({page})=>{
 const deck=await load(page)
 await page.setViewportSize({width:390,height:844})
 await expect(deck.locator('[data-testid^="gameday-"]')).toHaveCount(3)
 const state=await page.evaluate(()=>{
  const el=document.querySelector('[data-ref-mobile-sideline]')
  const buttons=el?[...el.querySelectorAll('button,a')]:[]
  const scoreboard=document.querySelector('[aria-label="Game Day scores and schedule"]')
  return {sidelineAriaHidden:el?.getAttribute('aria-hidden'),stageActionCount:buttons.length,
    originalSourceVisible:scoreboard?.textContent?.includes('ESPN'),
    scoreText:scoreboard?.textContent?.includes('21')&&scoreboard?.textContent?.includes('17'),
    hiddenAccountLeak:document.body.textContent.includes('ANNIE G 01')}
 })
 expect(state.sidelineAriaHidden).toBe('true')
 expect(state.stageActionCount).toBe(0)
 expect(state.originalSourceVisible).toBe(true)
 expect(state.scoreText).toBe(true)
 expect(state.hiddenAccountLeak).toBe(false)
})

test('verified no-games state also stays readable beside full-size Ref',async({page})=>{
 const deck=await load(page,{count:0})
 await page.setViewportSize({width:390,height:844})
 await expect(deck.getByText('No games in the display window')).toBeVisible()
 const el=deck.locator('[data-score-empty]')
 await expect(el).toBeVisible()
 await expect(deck.locator('[data-ref-mobile-sideline]')).toBeVisible()
 const d=await page.evaluate(()=>{
  const a=document.querySelector('.zenith-ref-mascot').getBoundingClientRect()
  const b=document.querySelector('[data-score-empty]').getBoundingClientRect()
  return {
   overlap:Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))
     *Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)),
   overflow:document.documentElement.scrollWidth-innerWidth,
   refWidth:a.width,
  }
 })
 expect(d.overlap).toBe(0)
 expect(d.overflow).toBeLessThanOrEqual(1)
 expect(d.refWidth).toBeGreaterThanOrEqual(108)
})
