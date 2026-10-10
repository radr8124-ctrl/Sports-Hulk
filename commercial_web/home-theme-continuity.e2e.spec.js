import { test, expect } from '@playwright/test'

const URL = process.env.ZENITH_NEWS_DESK_URL || 'http://127.0.0.1:8510/'
const rgb = (r,g,b) => `rgb(${r}, ${g}, ${b})`

async function homepage(page,width=390) {
  await page.setViewportSize({width,height:844})
  await page.goto(URL,{waitUntil:'domcontentloaded'})
  const scores=page.getByRole('region',{name:'Game Day scores and schedule'})
  await expect(scores).toBeVisible()
  await expect(scores.locator('article').first()).toBeVisible()
  await expect(page.getByRole('region',{name:'Home decision overview'})).toBeVisible()
}

test('new 1980s sports-broadcast palette appears across the actual Home', async({page})=>{
  await homepage(page)
  const c = await page.evaluate(()=>{
    const find=selector=>{
      const node=document.querySelector(selector)
      if(!node)throw new Error('Missing Home part: '+selector)
      const style=getComputedStyle(node)
      return {background:style.backgroundColor,foreground:style.color}
    }
    return {
      page:find('#root > div'),
      html:find('html'),
      hero:find('section[aria-label="Sports Zenith game-day command center"]'),
      scores:find('section[aria-label="Game Day scores and schedule"]'),
      scoreCard:find('section[aria-label="Game Day scores and schedule"] article'),
      decisionCard:find('section[aria-label="Home decision overview"] button.min-w-\\[270px\\]'),
      heading:find('section[aria-label="Home decision overview"] h2'),
      newsHeading:find('section[aria-label="Home sports news"] h2'),
      fantasy:find('section[aria-label="Home Fantasy Survivor and Brain Record"] button:nth-child(2)'),
      footer:find('footer'),
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
    }
  })
  expect(c.page.background).toBe(rgb(255,248,237))
  expect(c.html.background).toBe(rgb(255,248,237))
  expect(c.hero.background).toBe(rgb(255,245,228))
  expect(c.scores.background).toBe(rgb(218,244,238))
  expect(c.scoreCard.background).toBe(rgb(255,255,255))
  expect(c.decisionCard.background).toBe(rgb(255,240,232))
  expect(c.heading.foreground).toBe(rgb(23,62,82))
  // News Desk now uses warm ivory lettering on a contrasting ink masthead.
  expect(c.newsHeading.foreground).toBe(rgb(255,245,228))
  expect(c.fantasy.background).toBe(rgb(217,244,238))
  expect(c.footer.background).toBe(rgb(255,241,219))
  expect(c.overflow).toBeLessThanOrEqual(1)
})

test('retro editorial layout keeps scores inside first phone screen and readable at 320px',async({page})=>{
  await homepage(page,320)
  const hero=page.getByRole('region',{name:'Sports Zenith game-day command center'})
  await expect(hero.getByRole('heading',{name:/The game.*The smarter call/s})).toBeVisible()
  await expect(hero.getByRole('button',{name:/Explore Bets/})).toBeVisible()
  await expect(hero.getByRole('button',{name:/Ask The Ref/})).toBeVisible()
  await expect(page.getByRole('navigation',{name:'Mobile primary navigation'})).toBeVisible()
  const dims=await page.evaluate(()=>({
    overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
    headingTop:document.querySelector('[aria-label="Game Day scores and schedule"] h2')?.getBoundingClientRect().top,
    cardTop:document.querySelector('[aria-label="Game Day scores and schedule"] article')?.getBoundingClientRect().top,
  }))
  expect(dims.overflow).toBeLessThanOrEqual(1)
  expect(dims.headingTop).toBeLessThan(660)
  expect(dims.cardTop).toBeLessThan(820)
})

test('home headline cards retain category signs and true attributed links',async({page})=>{
  await homepage(page,1280)
  const section=page.getByRole('region',{name:'Home sports news'})
  await expect(section.getByRole('heading',{name:'Top sports news'})).toBeVisible()
  const articles=section.locator('[data-news-card]')
  // Await finished source-linked article rendering, not the brief LOADING banner.
  const first=articles.first()
  await expect(first).toBeVisible({timeout:15000})
  const style=await first.evaluate(el=>({
    background:getComputedStyle(el).backgroundColor,
    title:getComputedStyle(el.querySelector('h3')).color,
  }))
  expect([rgb(255,244,238),rgb(255,248,223),rgb(234,248,245),rgb(237,249,241),rgb(243,239,250),rgb(234,244,254),rgb(255,249,239)]).toContain(style.background)
  expect(style.title).toBe(rgb(2,6,23))
  await expect(first.locator('[data-category-sign]')).toBeVisible()
  expect(await first.locator('a').getAttribute('href')).toMatch(/^https:\/\//)
  await section.getByRole('button',{name:/All sports news/}).click()
  await expect(page).toHaveURL(/#news/)
})

test('Survivor Fantasy Brain and private-state protection survive the visual redesign',async({page})=>{
  await homepage(page)
  const cards=page.getByRole('region',{name:'Home Fantasy Survivor and Brain Record'})
  await expect(cards.getByText('Survivor',{exact:true})).toBeVisible()
  await expect(cards.getByText('Fantasy + DFS')).toBeVisible()
  await expect(cards.getByText('Brain Record')).toBeVisible()
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
  await cards.getByRole('button',{name:/Open Survivor/}).click()
  await expect(page).toHaveURL(/#survivor/)
  await expect(page.getByRole('heading',{name:'Survivor',exact:true})).toBeVisible()
  expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#root > div')).backgroundColor))
    .toBe(rgb(241,245,250))
})

test('source-status and learning evidence stay available under retro styling',async({page})=>{
  await homepage(page)
  await expect(page.getByRole('region',{name:'Home learning loop'})).toBeVisible()
  const details=page.locator('details').filter({hasText:'Source connections and system status'}).first()
  await details.locator('summary').click()
  await expect(details).toHaveAttribute('open','')
  await expect(page.getByText(/A green collector is not proof/)).toBeVisible()
  expect((await page.locator('body').innerText()).includes('ANNIE G 01')).toBe(false)
})

test('all other routes retain readable light research pages',async({page})=>{
  await homepage(page,1280)
  for(const [hash,heading] of [['#best-bets','Best Bets'],['#fantasy',null],['#brain-record','How good is the brain?']]){
    await page.goto(URL+hash,{waitUntil:'domcontentloaded'})
    await expect(page.getByRole('main')).toBeVisible()
    if(heading)await expect(page.getByRole('heading',{name:heading,exact:true})).toBeVisible()
    expect(await page.evaluate(()=>getComputedStyle(document.querySelector('#root > div')).backgroundColor))
      .toBe(rgb(241,245,250))
  }
})
