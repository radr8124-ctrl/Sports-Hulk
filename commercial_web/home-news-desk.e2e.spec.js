import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
import {gunzipSync} from 'node:zlib'
import {curateSportsNews,selectHomeTopStories} from './news_curation.js'

const BASE=process.env.ZENITH_NEWS_DESK_URL||'http://127.0.0.1:8510/'
const fixture=JSON.parse(gunzipSync(readFileSync(new URL('../reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz',import.meta.url))).toString('utf8'))
const CLOCK=Date.parse(fixture.generated_at)+4*60_000
const expected=selectHomeTopStories(curateSportsNews(fixture,CLOCK).stories,CLOCK)
const region=page=>page.getByRole('region',{name:'Home sports news'})

async function load(page,width=1280,payload=fixture){
 await page.setViewportSize({width,height:900})
 await page.addInitScript(clock=>{Date.now=()=>clock},CLOCK)
 await page.route('**/ask_retrieval.json*',route=>route.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(payload),
 }))
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await expect(region(page).getByRole('heading',{name:'Top sports news'})).toBeVisible()
}

test('Zenith News Desk has a premium ink masthead and one true lead with three attributed briefs',async({page})=>{
 await load(page)
 const news=region(page)
 const masthead=news.locator('[data-news-desk-masthead]')
 await expect(masthead).toBeVisible()
 expect(await masthead.evaluate(node=>getComputedStyle(node).backgroundColor)).toBe('rgb(23, 62, 82)')
 await expect(masthead.getByText('ZENITH NEWS DESK',{exact:true})).toBeVisible()
 await expect(news.locator('[data-news-desk-lead] [data-news-card]')).toHaveCount(1)
 await expect(news.locator('[data-news-desk-supporting] [data-news-card]')).toHaveCount(3)
 await expect(news.locator('[data-news-card]')).toHaveCount(4)
 await expect(news.locator('[data-news-desk-lead] [data-news-card]')).toHaveAttribute('data-news-featured','true')
 await expect(news.locator('[data-news-desk-supporting] [data-news-card]').first()).toHaveAttribute('data-news-compact','true')
 const proof=await news.locator('[data-news-card]').evaluateAll(nodes=>nodes.map(n=>({
   title:n.querySelector('h3')?.textContent?.trim(),
   sport:n.dataset.newsSport,
   category:n.dataset.newsCategory,
   sign:Boolean(n.querySelector('[data-category-sign]')),
   link:n.querySelector('a')?.href,
   source:Boolean(n.querySelector('a > div:last-child')?.textContent?.trim()),
 })))
 expect(proof.map(x=>x.title)).toEqual(expected.map(x=>x.title))
 expect(proof.every(x=>x.sign&&x.source&&x.link?.startsWith('http'))).toBe(true)
 expect(new Set(proof.map(x=>x.sport)).size).toBe(4)
 await news.getByRole('button',{name:/All sports news/}).click()
 await expect(page).toHaveURL(/#news/)
})

test('lead story visually dominates desktop while brief stories remain fully readable',async({page})=>{
 await load(page,1280)
 const news=region(page)
 const lead=news.locator('[data-news-desk-lead] [data-news-card]')
 const side=news.locator('[data-news-desk-supporting] [data-news-card]').first()
 const boxes=await Promise.all([lead.boundingBox(),side.boundingBox()])
 expect(boxes[0].width).toBeGreaterThan(boxes[1].width)
 expect(boxes[0].height).toBeGreaterThan(boxes[1].height*2)
 expect(boxes[1].x).toBeGreaterThan(boxes[0].x+boxes[0].width-5)
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
 expect(overflow).toBeLessThanOrEqual(1)
})

test('phone News Desk keeps featured story first, then discoverable swipe briefs without body overflow',async({page})=>{
 for(const width of [320,390,430]){
  await load(page,width)
  const news=region(page)
  await expect(news.locator('[data-news-desk-lead]')).toBeVisible()
  const rail=news.locator('[data-news-desk-supporting]')
  await expect(rail.locator('[data-news-card]')).toHaveCount(3)
  const dimensions=await page.evaluate(()=>{
   const lead=document.querySelector('[data-news-desk-lead]').getBoundingClientRect()
   const rail=document.querySelector('[data-news-desk-supporting]')
   const rect=rail.getBoundingClientRect()
   return {
    overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
    scrollable:rail.scrollWidth>rail.clientWidth,
    leadTop:lead.top,railTop:rect.top,
    regionWidth:document.querySelector('[aria-label="Home sports news"]').getBoundingClientRect().width,
    navTop:document.querySelector('nav[aria-label="Mobile primary navigation"]')?.getBoundingClientRect().top,
   }
  })
  expect(dimensions.overflow).toBeLessThanOrEqual(1)
  expect(dimensions.scrollable).toBe(true)
  expect(dimensions.railTop).toBeGreaterThan(dimensions.leadTop)
  await page.reload({waitUntil:'domcontentloaded'})
 }
})

test('failure and empty news feeds retain source-honest statuses inside the news desk',async({page})=>{
 for(const [payload,expectedText] of [
  [{generated_at:new Date(CLOCK).toISOString(),news_events:null},'NEWS SOURCE FAILURE'],
  [{generated_at:new Date(CLOCK).toISOString(),news_events:[]},'No source-linked news articles qualified'],
 ]){
  await load(page,390,payload)
  await expect(region(page).locator('[data-news-desk-masthead]')).toBeVisible()
  await expect(region(page).getByText(/Lead headline \+ 3 quick reads/)).toHaveCount(0)
  await expect(region(page).getByText(new RegExp(expectedText))).toBeVisible()
  await expect(region(page).locator('[data-news-card]')).toHaveCount(0)
 }
})
