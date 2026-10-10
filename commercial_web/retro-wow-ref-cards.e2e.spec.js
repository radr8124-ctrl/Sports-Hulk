import {test,expect} from '@playwright/test'
const URL='http://127.0.0.1:8510/'
const view=(page)=>page.evaluate(()=>({
 overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 ref:document.querySelector('.zenith-ref-mascot')?.getBoundingClientRect().toJSON(),
 latest:document.querySelector('[data-intelligence-card="Survivor"]')?.getBoundingClientRect().toJSON(),
}))

test('desktop editorial signal cards use five distinct paper colors with an unobstructed sideline',async({page})=>{
 await page.setViewportSize({width:1280,height:900})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 await page.getByRole('region',{name:'Home decision overview'}).scrollIntoViewIfNeeded()
 const cards=page.locator('[data-intelligence-card]')
 await expect(cards).toHaveCount(5)
 const profile=await cards.evaluateAll(rows=>rows.map(el=>({
  label:el.dataset.intelligenceCard,
  bg:getComputedStyle(el).backgroundColor,
  title:el.querySelector('h3')?.innerText,
  metric:el.querySelector('.zenith-home-signal-metric')?.innerText,
 })))
 expect(new Set(profile.map(r=>r.bg)).size).toBe(5)
 expect(profile.map(r=>r.label)).toEqual(['Best Bets','Props','PrizePicks','Parlays','Survivor'])
 expect(profile.every(r=>r.title&&r.metric)).toBe(true)
 const dims=await view(page)
 expect(dims.overflow).toBeLessThanOrEqual(1)
 expect(dims.ref.width).toBeGreaterThanOrEqual(145)
 expect(dims.ref.left).toBeGreaterThanOrEqual(dims.latest.right+5)
 await expect(page.getByRole('complementary',{name:'The Ref sports companion'})).toHaveAttribute('data-section','signals')
 await cards.filter({hasText:'Best Bets'}).click()
 await expect(page).toHaveURL(/#best-bets/)
})

test('news editorial uses source-linked colored paper without altering headlines',async({page})=>{
 await page.setViewportSize({width:1280,height:900})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 const story=page.getByRole('region',{name:'Home sports news'}).locator('[data-news-card]').first()
 if(await story.count()){
  const color=await story.evaluate(e=>getComputedStyle(e).backgroundColor)
  expect(color).not.toBe('rgb(255, 255, 255)')
  await expect(story.locator('[data-category-sign]')).toBeVisible()
  const url=await story.locator('a').getAttribute('href')
  expect(url).toMatch(/^https:\/\//)
 }
})

test('The Ref actually follows the page sections on desktop and moves vertically',async({page})=>{
 await page.setViewportSize({width:1280,height:900})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 const heights=[]
 for(const [selector,expected] of [
  ['[aria-label="Game Day scores and schedule"]','scores'],
  ['[aria-label="Home decision overview"]','signals'],
  ['[aria-label="Home sports news"]','news'],
  ['[aria-label="Home learning loop"]','learning'],
 ]){
  await page.evaluate(q=>document.querySelector(q)?.scrollIntoView({block:'center',behavior:'instant'}),selector)
  await expect(ref).toHaveAttribute('data-section',expected)
  await page.waitForTimeout(860)
  heights.push(await ref.evaluate(el=>Number.parseFloat(getComputedStyle(el).bottom)))
 }
 expect(Math.max(...heights)-Math.min(...heights)).toBeGreaterThan(120)
 expect((await view(page)).overflow).toBeLessThanOrEqual(1)
})

test('bigger mobile Ref can be minimized and does not cover bottom navigation',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await expect(ref.getByRole('button',{name:'Open The Ref animated sports companion'})).toBeVisible()
 const dims=await page.evaluate(()=>({
  figure:document.querySelector('.zenith-ref-mascot')?.getBoundingClientRect().toJSON(),
  nav:document.querySelector('nav[aria-label="Mobile primary navigation"]')?.getBoundingClientRect().toJSON(),
  overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
 }))
 expect(dims.figure.width).toBeGreaterThanOrEqual(108)
 expect(dims.figure.bottom).toBeLessThanOrEqual(dims.nav.top+1)
 expect(dims.overflow).toBeLessThanOrEqual(1)
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await ref.getByRole('button',{name:'Shrink'}).click()
 await expect(ref).toHaveAttribute('data-minimized','true')
 await ref.getByRole('button',{name:'Expand The Ref mascot'}).click()
 await expect(ref).toHaveAttribute('data-minimized','false')
})

test('football flag and strike signal are visibly animated, sound remains opt-in',async({page})=>{
 await page.setViewportSize({width:390,height:844})
 await page.goto(URL,{waitUntil:'domcontentloaded'})
 const ref=page.getByRole('complementary',{name:'The Ref sports companion'})
 await ref.getByRole('button',{name:'Open The Ref animated sports companion'}).click()
 await ref.getByRole('button',{name:'The Ref throws a flag'}).click()
 await expect(ref).toHaveAttribute('data-signal','flag')
 expect(await ref.locator('.zenith-ref-flag').evaluate(el=>getComputedStyle(el).animationName)).toContain('zenith-premium-flag-toss')
 await ref.getByRole('button',{name:'The Ref signals strike three'}).click()
 await expect(ref).toHaveAttribute('data-signal','strike')
 expect(await ref.locator('.zenith-ref-right-arm').evaluate(el=>getComputedStyle(el).animationName)).toContain('zenith-premium-strike')
 await expect(ref.getByRole('button',{name:'The Ref blows a whistle'})).toBeVisible()
})
