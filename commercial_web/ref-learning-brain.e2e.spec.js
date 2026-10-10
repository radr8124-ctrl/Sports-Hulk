import {test,expect} from '@playwright/test'
const BASE='http://127.0.0.1:8510/'

test('iPhone has a movable animated Ref with flag, strikeout and whistle calls',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 const errors=[]
 page.on('pageerror',e=>errors.push(e.message))
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await expect(ref).toBeVisible()
 await expect(ref).toHaveAttribute('data-side','right')
 const mobileNav=page.getByRole('navigation',{name:'Mobile primary navigation'})
 const layout=await page.evaluate(()=>({
  ref:document.querySelector('[data-ref-companion] button[aria-expanded]')?.getBoundingClientRect().bottom,
  nav:document.querySelector('nav[aria-label="Mobile primary navigation"]')?.getBoundingClientRect().top,
  overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 }))
 expect(layout.ref).toBeLessThan(layout.nav+1)
 expect(layout.overflow).toBeLessThanOrEqual(1)
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await expect(ref.getByRole('group',{name:'The Ref quick calls'})).toBeVisible()
 await ref.getByRole('button',{name:'The Ref throws a flag'}).click()
 await expect(ref).toHaveAttribute('data-signal','flag')
 await expect(ref.getByText('FLAG ON THE PLAY!')).toBeVisible()
 await ref.getByRole('button',{name:'The Ref signals strike three'}).click()
 await expect(ref).toHaveAttribute('data-signal','strike')
 await expect(ref.getByText('STRIKE THREE!')).toBeVisible()
 await ref.getByRole('button',{name:'The Ref blows a whistle'}).click()
 await expect(ref).toHaveAttribute('data-signal','whistle')
 await expect(ref.getByText('FWEET! WHISTLE!')).toBeVisible()
 await ref.getByRole('button',{name:'Move Ref to the left'}).click()
 await expect(ref).toHaveAttribute('data-side','left')
 await expect(ref.getByRole('group',{name:'The Ref quick calls'})).toHaveCount(0)
 expect(errors).toEqual([])
})

test('Ref Ask and Brain buttons navigate to existing functional destinations',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await ref.getByRole('button',{name:'Brain Record'}).click()
 await expect(page).toHaveURL(/#brain-record/)
 await expect(page.getByRole('heading',{name:'How good is the brain?',exact:true})).toBeVisible()
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await ref.getByRole('button',{name:'Ask The Ref'}).click()
 await expect(ref).toHaveCount(0)
 await expect(page.getByRole('button',{name:/Close/}).first()).toBeVisible()
})

test('Learning Loop buttons reveal real steps and link into Brain Record',async({page})=>{
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const loop=page.getByRole('region',{name:'Home learning loop'})
 await expect(loop.getByRole('group',{name:'Choose a learning step'})).toBeVisible()
 await loop.getByRole('button',{name:/STEP 03.*Review/}).click()
 await expect(loop.getByText(/A possible cause is not called proven/)).toBeVisible()
 await loop.getByRole('button',{name:/STEP 04.*Test/}).click()
 await expect(loop.getByText(/shadow trial until new future games/)).toBeVisible()
 await loop.getByRole('button',{name:'See actual evidence and mistakes'}).click()
 await expect(page).toHaveURL(/#brain-record/)
 await expect(page.getByRole('heading',{name:'How good is the brain?',exact:true})).toBeVisible()
})

test('homepage Brain Record explains a frozen one-pick sample without inventing wins',async({page})=>{
 // Frozen original Oct 10 observations keep this regression stable after Week 5 settles.
 await page.route('**/performance_snapshot.json*',route=>route.fulfill({
  status:200,contentType:'application/json',
  body:JSON.stringify({
   generated_at:'2026-10-10T08:09:11Z',
   official:{published:3,settled:1,pending:2,wins:0,losses:1,pushes:0,units:-1,roi_pct:-100,status:'TRACKING'},
   official_recent:[
    {event_type:'PUBLISHED',official:true,pick_id:'pending-a',grade:'PENDING',selection:'Detroit Lions',market:'MONEYLINE',game_key:'DET@ARI',american_odds:-240},
    {event_type:'PUBLISHED',official:true,pick_id:'pending-b',grade:'PENDING',selection:'New England Patriots',market:'MONEYLINE',game_key:'LV@NE',american_odds:-182},
    {event_type:'SETTLED',official:true,pick_id:'settled-no',grade:'LOSS',selection:'New Orleans Saints',game_key:'ATL@NO',american_odds:-141,result:'ATL 45 - 24 NO',settled_at:'2026-10-06T04:05:14Z'},
   ],
   policy:{record_started_at:'2026-10-05T04:28:17Z',rules:[]},
   research_validation:[],
  }),
 }))
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const card=page.getByRole('region',{name:'Home Fantasy Survivor and Brain Record'}).getByRole('button',{name:/Brain Record/})
 await expect(card.getByText('1 pick graded')).toBeVisible()
 await expect(card.getByText(/0 wins · 1 loss · 2 pending/)).toBeVisible()
 await expect(card.getByText(/Last graded: New Orleans Saints to win/)).toBeVisible()
 await card.click()
 const details=page.getByRole('region',{name:'Recently graded official picks'})
 await expect(details).toBeVisible()
 await expect(details.getByText(/New Orleans Saints to win/)).toBeVisible()
 await expect(details.getByText(/ATL 45 - 24 NO/)).toBeVisible()
 expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})

test('reduced-motion users still get Ref buttons but no automatic hovering',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'})
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 const css=await ref.locator('.zenith-ref-idle').evaluate(el=>getComputedStyle(el).animationName)
 expect(css).toBe('none')
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await ref.getByRole('button',{name:'The Ref throws a flag'}).click()
 await expect(ref).toHaveAttribute('data-signal','flag')
 expect(await ref.locator('.zenith-ref-flag').evaluate(el=>getComputedStyle(el).opacity)).toBe('1')
})
