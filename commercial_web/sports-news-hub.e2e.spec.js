import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
import {gunzipSync} from 'node:zlib'
import {curateSportsNews,NEWS_SPORTS,selectHomeTopStories} from './news_curation.js'

const BASE=process.env.ZENITH_NEWS_DESK_URL||'http://127.0.0.1:8510/'
const source=JSON.parse(gunzipSync(readFileSync(new URL('../reports/SPORTS_ZENITH_NEWS_SOURCE_FIXTURE_20261010.json.gz',import.meta.url))).toString('utf8'))
const CLOCK=Date.parse(source.generated_at)+4*60_000
const expected=curateSportsNews(source,CLOCK)
const featured=selectHomeTopStories(expected.stories,CLOCK)

async function open(page,hash='',payload=source){
 await page.setViewportSize({width:390,height:844})
 await page.addInitScript(clock=>{Date.now=()=>clock},CLOCK)
 await page.route('**/ask_retrieval.json*',route=>route.fulfill({
  status:200,contentType:'application/json',body:JSON.stringify(payload),
 }))
 await page.goto(BASE+(hash?'#'+hash:''),{waitUntil:'domcontentloaded'})
}
const home=p=>p.getByRole('region',{name:'Home sports news'})
const hub=p=>p.locator('[aria-label="Sports Zenith full news hub"]')
const articles=p=>p.locator('[data-news-card]')
const leagueTabs=p=>p.getByRole('group',{name:'Filter news by sport'})
const typeTabs=p=>p.getByRole('group',{name:'Filter news by story type'})

test('Home keeps only four current, sourced, varied Top Stories with bold editorial icons',async({page})=>{
 await open(page)
 await expect(home(page).getByRole('heading',{name:'Top sports news'})).toBeVisible()
 await expect(home(page).getByRole('button',{name:/All sports news/})).toBeVisible()
 await expect(articles(home(page))).toHaveCount(4)
 const data=await articles(home(page)).evaluateAll(items=>items.map(item=>({
  category:item.dataset.newsCategory,sport:item.dataset.newsSport,
  link:item.querySelector('a')?.href,target:item.querySelector('a')?.target,
  icon:item.querySelector('[data-category-sign] svg')?.outerHTML?.slice(0,50),
 })))
 expect(new Set(data.map(r=>r.sport)).size).toBe(4)
 expect(data.some(x=>x.category==='INJURY')).toBe(true)
 expect(data.some(x=>x.category==='RECAP')).toBe(true)
 expect(data.every(x=>x.icon&&x.link?.startsWith('http')&&x.target==='_blank')).toBe(true)
 expect(data.map(x=>x.sport)).toEqual(featured.map(x=>x.sport))
 await home(page).getByRole('button',{name:/All sports news/}).click()
 await expect(page).toHaveURL(/#news/)
 await expect(hub(page).getByRole('heading',{name:/Sports news\./})).toBeVisible()
})

test('Newsroom shows six distinct league sections and ALL curated article count, not only 18',async({page})=>{
 await open(page,'news')
 await expect(hub(page).getByText(new RegExp(expected.stories.length+' source-linked stories'))).toBeVisible()
 await expect(hub(page).getByRole('heading',{name:'Top across sports'})).toBeVisible()
 await expect(page.locator('[data-sport-news-section]')).toHaveCount(6)
 const leagues=await page.locator('[data-sport-news-section]').evaluateAll(sections=>sections.map(s=>s.dataset.sportNewsSection))
 expect(leagues).toEqual(NEWS_SPORTS)
 await expect(page.locator('[aria-label="Newsroom top headlines"] [data-news-card]')).toHaveCount(3)
 const num=await articles(page).count()
 expect(num).toBeGreaterThan(15)
 expect(num).toBeLessThanOrEqual(21)
 await expect(page.getByText(/Videos and promotional items are excluded/)).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(1)
})

test('Sport filter unlocks all NFL articles through functional Show More, without hiding remaining stories',async({page})=>{
 await open(page,'news')
 await expect(leagueTabs(page).getByRole('button',{name:/^NFL\s/})).toBeVisible()
 await leagueTabs(page).getByRole('button',{name:/^NFL\s/}).click()
 await expect(page.locator('[data-sport-news-section="NFL"]')).toHaveCount(1)
 const section=page.locator('[data-sport-news-section="NFL"]')
 await expect(articles(section)).toHaveCount(12)
 await section.getByRole('button',{name:/Show more NFL stories/}).click()
 await expect(articles(section)).toHaveCount(24)
 await section.getByRole('button',{name:/Show more NFL stories/}).click()
 const nfl=expected.stories.filter(x=>x.sport==='NFL')
 await expect(articles(section)).toHaveCount(nfl.length)
 await expect(section.getByRole('button',{name:/Show more NFL stories/})).toHaveCount(0)
})

test('Recap, injury and Fantasy category icons really filter story articles',async({page})=>{
 await open(page,'news')
 await expect(typeTabs(page).getByRole('button',{name:/^recap$/i})).toBeVisible()
 await typeTabs(page).getByRole('button',{name:/^recap$/i}).click()
 const recap=page.locator('[data-news-card]')
 await expect(recap.first()).toBeVisible()
 const categories=await recap.evaluateAll(rows=>rows.map(x=>x.dataset.newsCategory))
 expect(new Set(categories)).toEqual(new Set(['RECAP']))
 await expect(page.getByText(/stories found/)).toBeVisible()
 await typeTabs(page).getByRole('button',{name:/^injury$/i}).click()
 await expect(recap.first()).toBeVisible()
 expect(new Set(await recap.evaluateAll(rows=>rows.map(x=>x.dataset.newsCategory)))).toEqual(new Set(['INJURY']))
 await typeTabs(page).getByRole('button',{name:/^fantasy$/i}).click()
 await expect(recap.first()).toBeVisible()
 expect(new Set(await recap.evaluateAll(rows=>rows.map(x=>x.dataset.newsCategory)))).toEqual(new Set(['FANTASY']))
})

test('Search filters by story, player and sport; newest ordering is separate from top rank',async({page})=>{
 await open(page,'news')
 const input=page.getByRole('searchbox',{name:'Search sports news'})
 await input.fill('Shesterkin')
 await expect(page.locator('[data-sport-news-section="NHL"]')).toBeVisible()
 const titles=await page.locator('[data-news-card] h3').allTextContents()
 expect(titles.length).toBeGreaterThanOrEqual(1)
 expect(titles.every(title=>title.toLowerCase().includes('shesterkin'))).toBe(true)
 await input.fill('unfindable unlikely phrase')
 await expect(page.getByText(/No articles match those filters/)).toBeVisible()
 await input.fill('')
 await page.getByRole('group',{name:'Sort sports articles'}).getByRole('button',{name:'Newest first'}).click()
 await expect(page.getByRole('group',{name:'Sort sports articles'}).getByRole('button',{name:'Newest first'})).toHaveAttribute('aria-pressed','true')
 await expect(page.getByText('Top across sports',{exact:true})).toHaveCount(0)
})

test('Articles link directly to the original ESPN story and never turn raw injury FACT into a headline',async({page})=>{
 await open(page,'news')
 await expect(articles(page).first()).toBeVisible()
 const sources=await articles(page).evaluateAll(nodes=>nodes.map(e=>({
  url:e.querySelector('a')?.href,
  target:e.querySelector('a')?.target,
  text:e.querySelector('h3')?.textContent,
 })))
 expect(sources.every(s=>s.url?.startsWith('http')&&s.target==='_blank')).toBe(true)
 expect(sources.every(s=>!s.text?.includes('Adem Bona is listed'))).toBe(true)
 expect(sources.every(s=>!s.text?.includes('Game Highlights'))).toBe(true)
 expect(sources.every(s=>!s.text?.includes('promo code'))).toBe(true)
})

test('Newsroom editor drafts remain accessible, but tucked away below real articles',async({page})=>{
 await open(page,'news')
 const editorial=page.locator('details[aria-label="Sports Zenith editorial research drafts"]')
 await expect(editorial).toBeVisible()
 await expect(editorial).not.toHaveAttribute('open','')
 await editorial.locator('summary').click()
 await expect(editorial).toHaveAttribute('open','')
 await expect(editorial.getByRole('heading',{name:'Future original publishing engine'})).toBeVisible()
 await expect(editorial.getByText('No auto-publish')).toBeVisible()
})

test('Bad feeds and verified-empty feeds have different statuses on Home and News',async({page})=>{
 await open(page,'news',{generated_at:new Date(CLOCK).toISOString(),news_events:null})
 await expect(hub(page).getByText('DATA SOURCE FAILURE',{exact:true})).toBeVisible()
 await page.unrouteAll({behavior:'ignoreErrors'})
 await page.route('**/ask_retrieval.json*',route=>route.fulfill({
  status:200,contentType:'application/json',
  body:JSON.stringify({generated_at:new Date(CLOCK).toISOString(),news_events:[]}),
 }))
 await page.reload({waitUntil:'domcontentloaded'})
 await expect(hub(page).getByText('NO QUALIFIED ARTICLES',{exact:true})).toBeVisible()
 await page.goto(BASE,{waitUntil:'domcontentloaded'})
 await expect(home(page).getByText(/No source-linked news articles qualified/)).toBeVisible()
})

test('Newsroom desktop layout stays readable, and no duplicate Ref bubble blocks articles',async({page})=>{
 await open(page,'news')
 await page.setViewportSize({width:1280,height:844})
 await expect(page.getByRole('heading',{name:/Sports news\./})).toBeVisible()
 await expect(page.locator('[data-sport-news-section]')).toHaveCount(6)
 await expect(page.getByRole('button',{name:'Open the Ref sports assistant'})).toHaveCount(0)
 const dims=await page.evaluate(()=>({
  overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
  featured:document.querySelector('[aria-label="Newsroom top headlines"] [data-news-card]')?.getBoundingClientRect().top,
 }))
 expect(dims.overflow).toBeLessThanOrEqual(1)
 expect(dims.featured).toBeLessThan(1000)
})
